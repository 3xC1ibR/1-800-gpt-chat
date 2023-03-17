"""
listener.py
example usage:
    python listener.py --model_size=small

this script executes two processes.
(1) will listen to a microphone and save the audio to a file in 1 second increments.
it will periodically check the unprocessed directory for files and if it finds any, it will
combine them into a single file.
(2) will then run whisper on the file chunk and print the result.

"""
import argparse
import pyaudio
import wave
import signal
import sys
import whisper
import os
from os import walk
import subprocess
import time
from pathlib import Path
from datetime import datetime
from multiprocessing import Process

# DIRS
UNPROCESSED = os.path.join(Path(__file__).parent.absolute(), 'audio/unprocessed')
STAGE = os.path.join(Path(__file__).parent.absolute(), 'audio/stage')
ARCHIVE = os.path.join(Path(__file__).parent.absolute(), 'audio/archive')

STAGE_FILE = os.path.join(STAGE, "sounds.wav")
TRIGGER = 'robot jones'
QUIT = 'go away'

def print_writer(*args) -> None:
    """helper fucntion to see which process is printing"""
    text= " ".join([str(arg) for arg in args])
    print(f"WRITER: {text}")

def print_reader(*args) -> None:
    """helper fucntion to see which process is printing"""
    text= " ".join([str(arg) for arg in args])
    print(f"READER: {text}")

class TranscriptionNameRequired(BaseException):
    pass


def signal_handler(sig, frame):
    os.system('cls' if os.name == 'nt' else 'clear')
    _clean_up()
    print('bye')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def _clean_up():
    _archive_stage()
    files = next(walk(UNPROCESSED), (None, None, []))[2]  # [] if no file
    _archive_unprocessed(files)


def _archive_stage():
    # clear STAGE, UNPROCESSED directories on startup
    print('...archiving chunk')
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not os.path.isfile(STAGE_FILE):
        return
    old_chunk = STAGE_FILE

    archive_chunk = os.path.join(ARCHIVE, f"archive_{now}.wav")
    os.rename(old_chunk, archive_chunk)


def _archive_unprocessed(file_list):
    # clear STAGE, UNPROCESSED directories on startup
    print('...archiving unprocessed files')
    for f in file_list:
        old = os.path.join(UNPROCESSED, f)
        new = os.path.join(ARCHIVE, f)
        os.rename(old, new)


def _startup():
    # helper function to clear STAGE, UNPROCESSED directories on startup
    # and wait for the stream reader buffer to fill up
    _clean_up()
    print_reader('...waiting for stream reader to warm up')
    COLD_START = False
    time.sleep(3.5)



def stream_reader(name=None, model_size="small"):
    print('#' * 40)
    print_reader('...starting stream_reader')
    print_reader("...loading model")
    # model = whisper.load_model("tiny")
    model = whisper.load_model("base")
    # model = whisper.load_model("small")
    # model = whisper.load_model("large")
    # model = whisper.load_model(model_size)
    print_reader(model_size, "model loaded...")

    now = datetime.now().strftime("%y%m%d_%H%M")
    transcription_name = (name+now if name else now) + '.txt'
    _startup()

    while True:
        infiles = next(walk(UNPROCESSED), (None, None, []))[2]  # [] if no file
        if not infiles:
            print_reader('NO FILES IN', UNPROCESSED)
            print_reader('WAITING FOR FILES...')
            time.sleep(1)
            # os.system('cls' if os.name == 'nt' else 'clear')
            continue
        infiles.sort()
        oldest_ts = infiles[0]
        latest_ts = infiles[-1]

        print_reader('generating file chunk')
        data = []
        for infile in infiles:
            infile = os.path.join(UNPROCESSED, infile)
            w = wave.open(infile, 'rb')
            data.append([w.getparams(), w.readframes(w.getnframes())])
            w.close()

        output = wave.open(STAGE_FILE, 'wb')
        output.setparams(data[0][0])
        for i in range(len(data)):
            output.writeframes(data[i][1])
        output.close()
        # ARCHIVE FILE CHUNK
        # todo: truncate silence
        _archive_unprocessed(infiles)

        print_reader('running transcription')
        print_reader('for timestamps')
        # todo: calculate lag
        # infile[0] - infile[-1] = processing chuck size
        # infile[0] - now() = lag
        print_reader(f"{oldest_ts} '-->' {latest_ts}")
        tic = time.process_time()
        result = model.transcribe(STAGE_FILE)

        text = result["text"]
        print(text)
        if TRIGGER in text.lower():
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('TRIGGER WORD ACTIVATED')
            print('TRIGGER WORD ACTIVATED')
            print('TRIGGER WORD ACTIVATED')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        if QUIT in text.lower():
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('QUIT WORD ACTIVATED')
            print('QUIT WORD ACTIVATED')
            print('QUIT WORD ACTIVATED')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            _clean_up()
            sys.exit(0)
        with open(transcription_name, 'a') as f:
            f.write(text)
            f.write('\n')

        toc = time.process_time()
        print_reader("executed in ", toc - tic)
        print('~' * 30)


def stream_writer():
    print('#' * 40)
    print_writer('...starting stream_writer')
    # AUDIO INPUT
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024
    RECORD_SECONDS = 3

    audio = pyaudio.PyAudio()

    # start Recording
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)

    iters = 0
    while True:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")

        print_writer(f"[{now} | {iters} ] recording...")
        frames = []
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)
        file_name = 'audio/unprocessed/' + now + '.wav'
        wave_file = wave.open(file_name, 'wb')
        wave_file.setnchannels(CHANNELS)
        wave_file.setsampwidth(audio.get_sample_size(FORMAT))
        wave_file.setframerate(RATE)
        wave_file.writeframes(b''.join(frames))
        wave_file.close()
        iters += 1


if __name__ == '__main__':
    # todo: add option to rename transcription file
    # todo: add option to rename archive files
    # todo: add transcription mode
    # todo: add listener mode

    parser = argparse.ArgumentParser(description='whisper wrapper')
    parser.add_argument('-t', action='store_true', description='')  # default = false
    parser.add_argument('-n', type=str)
    args = parser.parse_args()

    transcribe = args.t
    transcribe_name = args.n
    if transcribe:
        if not transcribe_name:
            raise TranscriptionNameRequired("name is required for transcribe mode\n try: listener -t -n NAME")
        model = "large"

    # print(args)

    Process(target=stream_writer).start()
    Process(target=stream_reader, args=('transcribe', 'large')).start()
