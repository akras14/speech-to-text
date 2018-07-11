import os
import speech_recognition as sr
import traceback
import subprocess
import shlex
import argparse
from multiprocessing.dummy import Pool
pool = Pool(8) # Number of concurrent threads

def do_work(input_file):

    # get metadata
    index = input_file.rfind('/')
    file_dir = input_file[0:index]
    file_name = input_file[index+1:len(input_file)]

    # convert input file from .mp3 to .wav
    # can't do this with ffmpeg because it compresses it in a way that's not suported by wave.py
    # need to use audacity to convert to wav instead

    file_path = input_file
    # split .wav file into parts
    print("START: Splitting {0} into parts.".format(file_path))
    cmd_in = "ffmpeg -loglevel quiet -i {0} -f segment -segment_time 30 -c copy source/parts/{1}%09d.wav".format(file_path, file_name[:-3])
    args = shlex.split(cmd_in)
    p = subprocess.Popen(args)
    print("Waiting for input file to be split")
    p.wait() #necessary in order to avoid starting subsequent work before splitting finishes
    print("DONE: Split file with ffmpeg.")

    #open api key to google cloud
    with open("api-key.json") as f:
        GOOGLE_CLOUD_SPEECH_CREDENTIALS = f.read()

    # find the relevant files
    r = sr.Recognizer()
    file_dir = 'source/parts/'
    all_files = sorted(os.listdir(file_dir))
    files = []
    for i in range(len(all_files)):
        elem = all_files[i]
        if elem.startswith(file_name[:-4]):
            files.append(elem)

    # transcribe file parts
    print("START: Transcribing file parts.")

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

    # print file transcripts
    with open("transcripts/{0}_transcript.txt".format(file_name[:-4]), "w") as f:
        f.write(transcript)
    print("DONE: Wrote full text to transcript.txt.")

    with open("transcripts/{0}_transcript.csv".format(file_name[:-4]), "w") as f:
        f.write(transcript_csv)
    print("DONE: Wrote to transcript.csv with 30s timestamps.")
    print("DONE: Transcript files are located in {0}/transcripts.".format(os.getcwd()))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'path', help='Full file path to input .wav file.')
    args = parser.parse_args()
    do_work(args.path)
