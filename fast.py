import os
import speech_recognition as sr
import traceback
import subprocess
import shlex
import argparse
import datetime
from os.path import isfile, join
from multiprocessing.dummy import Pool

def do_work(input_file):

    pool = Pool(8)  # Number of concurrent threads
    index = input_file.rfind('/')
    file_name = input_file[index+1:len(input_file)]
    print("\nTRANSCRIPTION STARTING FOR {0}.".format(file_name.upper()))

    # convert input file from .mp3 to .wav
    # can't do this with ffmpeg because it compresses it in a way that's not supported by wave.py
    # need to use audacity to convert to wav instead

    #region split .wav file into parts
    file_path = input_file
    print("Splitting {0} into parts.".format(file_name))
    cmd_in = "ffmpeg -loglevel quiet -i {0} -f segment -segment_time 30 " \
             "-c copy source/parts/{1}%09d.wav".format(file_path, file_name[:-3])
    args = shlex.split(cmd_in)
    p = subprocess.Popen(args)
    p.wait() #necessary in order to avoid starting subsequent work before splitting finishes
    #endregion

    #open api key to google cloud
    with open("api-key.json") as f:
        GOOGLE_CLOUD_SPEECH_CREDENTIALS = f.read()

    #find only the relevant files
    r = sr.Recognizer()
    file_dir = 'source/parts/'
    all_files = sorted(os.listdir(file_dir))
    files = []
    for i in range(len(all_files)):
        elem = all_files[i]
        if elem.startswith(file_name[:-4]) and file_name[:-4] in elem:
            files.append(elem)
    print("Split file with ffmpeg into {0} parts.".format(len(files)))
    #endregion

    #region transcribe file parts
    print("Transcribing file parts.")

    def transcribe(data):
        idx, file = data
        name = file_dir + file
        text = ""
        try:
            with sr.AudioFile(name) as source:
                audio = r.record(source)
            text = r.recognize_google_cloud(audio, credentials_json=GOOGLE_CLOUD_SPEECH_CREDENTIALS)
            print(name + ": done")
        except ValueError as err:
            tb = traceback.format_exc()
            print("Unexpected error with:" + name)
            print(err.args)
            print(tb)
            raise
        return {
            "idx": idx,
            "text": text
        }

    all_text = pool.map(transcribe, enumerate(sorted(files)))
    pool.close()
    pool.join()

    transcript = ""
    transcript_csv = ""
    for t in sorted(all_text, key=lambda x: x['idx']):
        total_seconds = t['idx'] * 30
        # Cool shortcut from:
        # https://stackoverflow.com/questions/775049/python-time-seconds-to-hms
        # to get hours, minutes and seconds
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)

        # Format time as h:m:s - 30 seconds of text
        transcript = transcript + "{} ".format(t['text'])
        transcript_csv = transcript_csv + "{:0>2d}:{:0>2d}:{:0>2d}, {}\n".format(h, m, s, t['text'])
    #endregion

    #region print file transcripts
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    out1 = "{0}_transcript_{1}.txt".format(file_name[:-4], timestamp)
    with open("transcripts/" + out1, "w") as f:
        f.write(transcript)
    print("Wrote full text to {0}.".format(out1))

    out2 = "{0}_transcript_{1}.csv".format(file_name[:-4], timestamp)
    with open("transcripts/" + out2, "w") as f:
        f.write(transcript_csv)
    print("Wrote full text to {0} with 30s timestamps.".format(out2))

    print("Transcript files are located in {0}/transcripts.".format(os.getcwd()))
    #endregion

    #region clean up
    # delete file parts
    for file in files:
        os.remove(file_dir + file)
    print("Deleted all file parts.")

    #change source wav file name
    newname = input_file[:index] + '/' + file_name[:-4] + "_Processed_" + timestamp + ".wav"
    os.rename(input_file, newname)
    print("Renamed input file to {0}.".format(newname))
    #endregion

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'path', help='Full file path to input .wav file.')
    args = parser.parse_args()
    if ".wav" in args.path:
        do_work(args.path)
    else:
        onlyfiles = []
        for f in os.listdir(args.path):
            if isfile(join(args.path, f)) and ".wav" in f:
                onlyfiles.append(os.path.abspath(os.path.join(args.path,f)))
        for f in onlyfiles:
            do_work(f)