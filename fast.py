import os
import speech_recognition as sr
from tqdm import tqdm
from multiprocessing.dummy import Pool
pool = Pool(8) # Number of concurrent threads

with open("api-key.json") as f:
    GOOGLE_CLOUD_SPEECH_CREDENTIALS = f.read()

r = sr.Recognizer()
files = sorted(os.listdir('parts/'))

def transcribe(data):
    idx, file = data
    name = "parts/" + file
    print(name + " started")
    # Load audio file
    with sr.AudioFile(name) as source:
        audio = r.record(source)
    # Transcribe audio file
    text = r.recognize_google_cloud(audio, credentials_json=GOOGLE_CLOUD_SPEECH_CREDENTIALS)
    print(name + " done")
    return {
        "idx": idx,
        "text": text
    }

all_text = pool.map(transcribe, enumerate(files))
pool.close()
pool.join()

transcript = ""
for t in sorted(all_text, key=lambda x: x['idx']):
    total_seconds = t['idx'] * 30
    # Cool shortcut from:
    # https://stackoverflow.com/questions/775049/python-time-seconds-to-hms
    # to get hours, minutes and seconds
    m, s = divmod(total_seconds, 60)
    h, m = divmod(m, 60)

    # Format time as h:m:s - 30 seconds of text
    transcript = transcript + "{:0>2d}:{:0>2d}:{:0>2d} {}\n".format(h, m, s, t['text'])

print(transcript)

with open("transcript.txt", "w") as f:
    f.write(transcript)
