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
from thefuzz import process, fuzz


# Global flags
bot_speaking = False


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


def server_speak(text, voice, q):
    global bot_speaking
    bot_speaking = True
    
    url = "http://localhost:59125/api/tts"

    response = requests.post(url, data=text, params={"voice": voice})
    with open("output.wav", "wb") as f:
        f.write(response.content)
    
    subprocess.run(["afplay", "output.wav"])

    # Let echo fade
    time.sleep(0.3)

    # Resetting flag
    bot_speaking = False

    # Clearing any leftover audio
    with q.mutex:
        q.queue.clear()


def start_listening(STT_MODEL_PATH):
    """Starts vosk's model listening to the user with the system's microphone."""
    # Load offline Vosk model (download first from Vosk's website)
    if not os.path.exists(STT_MODEL_PATH):
        print("Please download the Vosk model and place it in the 'model' folder.")
        exit(1)

    # Initialize Vosk speech recognizer
    model = Model(STT_MODEL_PATH) # Loads the vosk model


    rec = KaldiRecognizer(model, 16000) # Sample rate as 16kHz (standard for voice)
    rec.SetWords(True) # Words level processing

    # Audio recording parameters
    samplerate = 16000 # How often sound is processed per second
    q = queue.Queue() # Creates a queue to store the audio data -> avoid lag

    # Start listening
    print("Say something starting with 'philip' (Ctrl+C to exit)...")

    return q, rec, samplerate


def warm_up_voice(voice):
    """Warms up voice with mimic3 so assistant can talk quicker."""
    subprocess.run(["mimic3", "--voice", voice, " "], stdout=subprocess.DEVNULL)


def main():

    # Variables
    voice = "en_UK/apope_low" # "en_US/vctk_low"
    STT_MODEL_PATH = "/Users/mickey/vosk_model/vosk-model-small-en-us-0.15"
    wake_words = ['tovia', 'to via', 'toby']
    sleep_words = ['goodnight', 'good bye', 'goodbye', 'shut down', 'later gater', 'see you later']
    ai_model = "codellama:latest"


    # Functions
    warm_up_voice(voice)
    q, rec, samplerate = start_listening(STT_MODEL_PATH)

    # Starts listening w. sounddevice
    stream = sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16', # Blocksize in small chunks -> efficient
                        channels=1, callback=make_callback(q)) # Callback to store audio
    
    try:
        with stream:
            while True:
                data = q.get() # Grabs audio
                # print("Listening...", end="", flush=True)
                print("\rListening...", end="", flush=True)

                if rec.AcceptWaveform(data): # Is speech detected?
                    result = json.loads(rec.Result()) # Decodes the speech
                    
                    # Else, listen and get command
                    command = result.get("text", "").lower() # Responds to what was said

                    if command != "":
                        print(f"\nYou said: {command}", flush=True)

                    # # Basic command execution
                    if is_trigger_word(sleep_words, command):
                        server_speak("Goodbye, powering down.", voice, q)
                        break


                    if "philip" in command:
                    # if is_fuzzy_trigger("philip", command):
                        print("\a", end='', flush=True)
                        
                        actual_request = command.replace("philip", "")

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
                            if line:
                                data = json.loads(line)
                                token = data.get("response", "")

                                if not token:
                                    continue

                                # Print first token with the label
                                if first_token:
                                    print("Tovia: ", end="", flush=True)
                                    first_token = False

                                # print each token without a newline
                                print(token, end="", flush=True)
                                buffer += token
                                word_count += token.count(" ")

                                # Speak every 5-7 words or with punctuation
                                if token in {".", "!", "?"}:
                                    if buffer.strip():
                                        server_speak(buffer.strip(), voice, q)
                                        buffer = ""
                                        word_count = 0
                                
                                if data.get("done", False):
                                    break
                        
                        # Finish up leftover text
                        if buffer.strip():
                            server_speak(buffer.strip(), voice, q)
                    
                    # else:
                    #     print(f"You said: {command.strip()}", flush=True)

    except KeyboardInterrupt:
        print("\nTovia: Goodbye! Shutting down gracefully.")
        stream.close()
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




