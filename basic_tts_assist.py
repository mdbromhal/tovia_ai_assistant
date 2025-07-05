'''
Basic voice assist script that makes sure the vosk model is working.
- Offline, completely local

Process:
    1. Microphone input: captures real-time sound
    2. Callback function: converts raw input into bytes
    3. Queue (q): holds the audio until processed
    4. Vosk processes queue: converts speech into text
    5. Queue discards processed data: no long-term storage.

Resources:
https://alphacephei.com/vosk/models
'''

# Importing necessary modules
import os # For accessing files (vosk model files)
import json # To structure vosk's responses
import queue # Handles streaming audio input
import sounddevice as sd # Captures microphone input
from vosk import Model, KaldiRecognizer # Speech to text (model is speech recognition, Kaldi processes to text w. model)
import numpy as np
import subprocess
import requests
import time
import sys
import select
from thefuzz import process, fuzz
import threading
from pydub import AudioSegment
from pydub.playback import play
import termios
import tty
from pynput import keyboard


class SpeechInterface:
    def __init__(self, model_path):
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)

        self.queue = queue.Queue()
        self.stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype='int16',
            channels=1,
            callback=self._callback
        )
    

    def _callback(self, indata, frames, time_info, status):
        if not bot_speaking:
            self.queue.put(bytes(indata))

    
    def start(self):
        self.stream.start()

    
    def stop(self):
        self.stream.stop()



# Global flags
bot_speaking = False
stop_requested = False # Interrupt speech generation


def is_fuzzy_trigger(trigger, string):
    """Uses fuzz to see if a word loosely matches a trigger word."""
    if fuzz.ratio(trigger, string) > 85:
        return True
    else:
        return False


def is_trigger_word(list_words, string):
    """Returns True or False depending on if the trigger word for the action is in the string."""
    if any(word in string for word in list_words):
        return True
    else:
        return False


# Callback function for live audio processing
def make_callback(q):
    def callback(indata, frames, time, status):
        """
        Listens for audio input with microphone. Converts raw sound data to bytes that Vosk understands.
        """
        #if status:
        if not bot_speaking: # Only listen if bot not speaking
            # print(status)
            #q.put(np.frombuffer(indata, dtype=np.int16))
            q.put(bytes(indata)) # Convert to bytes that Vosk likes
    
    return callback


def start_keyboard_listener():
    def on_press(key):
        global stop_requested
        try:
            if key.char == 'q':
                stop_requested = True
                print("[Keyboard] 'q' pressed. Interripting...")
                return False # Stop listener
        except AttributeError:
            pass # Special keys ~ Shift/Ctrl/ect.
    
    listener = keyboard.Listener(on_press=on_press)
    listener.start()


def server_speak(text, voice, speech: SpeechInterface):
    global bot_speaking, stop_requested
    bot_speaking = True
    stop_requested = False

    # def keyboard_listener():
    #     global stop_requested
    #     print("[Press 'q' to stop speaking]")

    #     fd = sys.stdin.fileno()
    #     old_settings = termios.tcgetattr(fd)

    #     try:
    #         tty.setcbreak(fd) # Non-blocking mode
    #         while not stop_requested:
    #             if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
    #                 # key = sys.stdin.readline().strip().lower()
    #                 key = sys.stdin.read(1)
    #                 if key.lower() == 'q':
    #                     stop_requested = True
    #                     print("\n[Keyboard] 'q' pressed. Stopping speech.")
    #                     break
    #             time.sleep(0.05)
    #     finally:
    #         termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    start_keyboard_listener()

    # Listens for "stop" in background while speaking
    # def listen_for_stop():
    #     global stop_requested

    #     while not stop_requested:
    #         if not speech.queue.empty():
    #             data = speech.queue.get()
    #             if speech.recognizer.AcceptWaveform(data):
    #                 result = json.loads(speech.recognizer.Result())
    #                 command = result.get("text", "").lower()
    #                 if "stop" in command:
    #                     print("\n[Voice Command] Interruption Requested.")
    #                     nonlocal process
    #                     stop_requested = True
    #                     process.terminate()
    #                     break

    # listener_thread = threading.Thread(target=listen_for_stop)
    # listener_thread.start()

    # keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
    # keyboard_thread.start()


    # Call TTS & play audio
    url = "http://localhost:59125/api/tts"

    response = requests.post(url, data=text, params={"voice": voice})
    with open("output.wav", "wb") as f:
        f.write(response.content)

    # process = subprocess.Popen(["afplay", "output.wav"])
    sound = AudioSegment.from_file("output.wav")
    play_thread = threading.Thread(target=play, args=(sound,))
    play_thread.start()

    # Monitor playback
    #while process.poll() is None:
    while play_thread.is_alive():
        if stop_requested:
            # process.terminate()
            # print("[System] Audio playback stopped.")
            break
        time.sleep(0.1)

    # listener_thread.join()
    # keyboard_thread.join()
    bot_speaking = False
    with speech.queue.mutex:
        speech.queue.queue.clear()

    # stop_thread.join()

    # subprocess.run(["afplay", "output.wav"])

    # # Let echo fade
    # #time.sleep(0.3)

    # # Resetting flag
    # bot_speaking = False
    # # stop_requested = False

    # # Clearing any leftover audio
    # with q.mutex:
    #     q.queue.clear()


# def start_listening(STT_MODEL_PATH, assistant_name):
#     """Starts vosk's model listening to the user with the system's microphone."""
#     # Load offline Vosk model (download first from Vosk's website)
#     if not os.path.exists(STT_MODEL_PATH):
#         print("Please download the Vosk model and place it in the 'model' folder.")
#         exit(1)

#     # Initialize Vosk speech recognizer
#     model = Model(STT_MODEL_PATH) # Loads the vosk model


#     rec = KaldiRecognizer(model, 16000) # Sample rate as 16kHz (standard for voice)
#     rec.SetWords(True) # Words level processing

#     # Audio recording parameters
#     samplerate = 16000 # How often sound is processed per second
#     q = queue.Queue() # Creates a queue to store the audio data -> avoid lag

#     # Start listening
#     print(f"Say something starting with '{assistant_name}' (Ctrl+C to exit)...")

#     return q, rec, samplerate


def warm_up_voice(voice):
    """Warms up voice with mimic3 so assistant can talk quicker."""
    subprocess.run(["mimic3", "--voice", voice, " "], stdout=subprocess.DEVNULL)


def main():

    # Variables
    voice = "en_UK/apope_low" # "en_US/vctk_low"
    STT_MODEL_PATH = "/Users/mickey/vosk_model/vosk-model-small-en-us-0.15"
    # wake_words = ['tovia', 'to via', 'toby']
    sleep_words = ['goodnight', 'good bye', 'goodbye', 'shut down', 'later gater', 'see you later']
    ai_model = "codellama:latest"
    # device_id = 0 # Headphones w. microphone
    assistant_name = "jarvis"

    speech = SpeechInterface(STT_MODEL_PATH)
    speech.start()

    # Functions
    warm_up_voice(voice)
    # q, rec, samplerate = start_listening(STT_MODEL_PATH, assistant_name)

    # Starts listening w. sounddevice
    # stream = sd.RawInputStream(# device=device_id, 
    #                            samplerate=samplerate, 
    #                            blocksize=8000, # Blocksize in small chunks -> efficient
    #                            dtype='int16', 
    #                            channels=1, 
    #                            callback=make_callback(q)) # Callback to store audio
    
    try:
        while True:
            data = speech.queue.get()

            print("\rListening...", end="", flush=True)

            if speech.recognizer.AcceptWaveform(data):
                result = json.loads(speech.recognizer.Result())
                command = result.get("text", "").lower()

                if command:
                    print(f"\nYou said: {command}")

                if is_trigger_word(['shut down', 'goodbye', 'good bye'], command):
                    server_speak("Powering down.", voice, speech)
                    break

                elif command == assistant_name:
                    server_speak("Yes Boss?", voice, speech)
                    print(f"{assistant_name}: ", "Yes, Boss?")
                    
                elif assistant_name in command:
                    print("\a", end='', flush=True)
                    actual_request = command.replace(assistant_name, "")

                    response = requests.post(
                        "http://localhost:11434/api/generate",
                        json={"model": ai_model, 
                            "prompt": actual_request,
                            # "messages": [
                            #     {"role": "system", "content": "Your name is Tovia. You are a helpful and witty assistant that helps develop software and robotics applications."},
                            #     {"role": "user", "content": command}
                            # ]
                        },
                        stream=True # Because llama3.2 is responding in a stream format
                    )

                    buffer = ""
                    word_count = 0
                    first_token = True
                    for line in response.iter_lines():

                        # Check for stop requested
                        if stop_requested:
                            break

                        if line:
                            data = json.loads(line)
                            token = data.get("response", "")

                            if not token:
                                continue

                            # Print first token with the label
                            if first_token:
                                print(f"{assistant_name}: ", end="", flush=True)
                                first_token = False

                            # print each token without a newline
                            print(token, end="", flush=True)
                            buffer += token
                            word_count += token.count(" ")

                            # Speak every 5-7 words or with punctuation
                            if token in {".", "!", "?", ","} or (word_count > 5):
                                if buffer.strip():
                                    server_speak(buffer.strip(), voice, speech)
                                    buffer = ""
                                    word_count = 0
                            
                            if data.get("done", False):
                                break
                    
                    # Finish up leftover text
                    if buffer.strip():
                        server_speak(buffer.strip(), voice, speech)
                    
        # with stream:
        #     while True:
        #         data = q.get() # Grabs audio
        #         # print("Listening...", end="", flush=True)
        #         print("\rListening...", end="", flush=True)

        #         if rec.AcceptWaveform(data): # Is speech detected?
        #             result = json.loads(rec.Result()) # Decodes the speech
                    
        #             # Else, listen and get command
        #             command = result.get("text", "").lower() # Responds to what was said

        #             if command != "":
        #                 print(f"\nYou said: {command}", flush=True)

        #             # # Basic command execution
        #             if is_trigger_word(sleep_words, command):
        #                 server_speak("Goodbye, powering down.", voice, q, STT_MODEL_PATH)
        #                 break


        #             if assistant_name in command:
                    # if is_fuzzy_trigger("philip", command):
                        #print("\a", end='', flush=True)
                        
                        #actual_request = command.replace(assistant_name, "")

                        # response = requests.post(
                        #     "http://localhost:11434/api/generate",
                        #     json={"model": ai_model, 
                        #         "prompt": actual_request,
                        #         # "messages": [
                        #         #     {"role": "system", "content": "Your name is Tovia. You are a helpful and witty assistant that helps develop software and robotics applications."},
                        #         #     {"role": "user", "content": command}
                        #         # ]
                        #     },
                        #     stream=True # Because llama3.2 is responding in a stream format
                        # )

                        # buffer = ""
                        # word_count = 0
                        # first_token = True
                        # for line in response.iter_lines():
                        #     if line:
                        #         data = json.loads(line)
                        #         token = data.get("response", "")

                        #         if not token:
                        #             continue

                        #         # Print first token with the label
                        #         if first_token:
                        #             print(f"{assistant_name}: ", end="", flush=True)
                        #             first_token = False

                        #         # print each token without a newline
                        #         print(token, end="", flush=True)
                        #         buffer += token
                        #         word_count += token.count(" ")

                        #         # Speak every 5-7 words or with punctuation
                        #         if token in {".", "!", "?"}:
                        #             if buffer.strip():
                        #                 server_speak(buffer.strip(), voice, q, STT_MODEL_PATH)
                        #                 buffer = ""
                        #                 word_count = 0
                                
                        #         if data.get("done", False):
                        #             break
                        
                        # # Finish up leftover text
                        # if buffer.strip():
                        #     server_speak(buffer.strip(), voice, q, STT_MODEL_PATH)
                    
                    # else:
                    #     print(f"You said: {command.strip()}", flush=True)

    except KeyboardInterrupt:
        print("\nShutting down.")
        speech.stop()
        # stream.close()
        sys.exit(0)


if __name__ == "__main__":
    main()



# mimic3-server
# New terminal
# source mimic3_env/bin/activate
# python3 basic_tts_assist.py

# ollama list

# python3 -m venv tovia_env
# source tovia_env/bin/activate

# pip install mycroft-mimic3-tts

# pip freeze > requirements.txt

# ollama rm llama2

# ollama pull mistral

# sudo tcpdump -i any


# TAURI
# npm run tauri dev in interruptor


