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

# Global flags
bot_speaking = False

# Warming up the voice
voice = "en_UK/apope_low" # "en_US/vctk_low"
subprocess.run(["mimic3", "--voice", voice, " "], stdout=subprocess.DEVNULL)

# Load offline Vosk model (download first from Vosk's website)
MODEL_PATH = "/Users/mickey/vosk_model/vosk-model-small-en-us-0.15"
if not os.path.exists(MODEL_PATH):
    print("Please download the Vosk model and place it in the 'model' folder.")
    exit(1)

# Initialize Vosk speech recognizer
model = Model(MODEL_PATH) # Loads the vosk model
rec = KaldiRecognizer(model, 16000) # Sample rate as 16kHz (standard for voice)
rec.SetWords(True) # Words level processing

# Audio recording parameters
samplerate = 16000 # How often sound is processed per second
q = queue.Queue() # Creates a queue to store the audio data -> avoid lag

# Callback function for live audio processing
def callback(indata, frames, time, status):
    """
    Listens for audio input with microphone. Converts raw sound data to bytes that Vosk understands.
    """
    #if status:
    if not bot_speaking: # Only listen if bot not speaking
        print(status)
        #q.put(np.frombuffer(indata, dtype=np.int16))
        q.put(bytes(indata)) # Convert to bytes that Vosk likes

# def speak(text):
#     """
    
#     """
#     #subprocess.run(["piper", "--wave", "output.wav", "--text", text])
#     # subprocess.run(["afplay", "output.wav"])


# #text = "Hello from a script!"
    
#     #voice = "en_US/vctk_low"
#     output = "output.wav"

#     subprocess.run([
#         "mimic3",
#         "--voice", voice,
#         text
#     ], stdout=open(output, "wb"))

#     subprocess.run(["afplay", output])

def server_speak(text):
    global bot_speaking
    bot_speaking = True
    
    # text = "Hello from the server!"
    # voice = "en_US/cmu-arctic_low"
    url = "http://localhost:59125/api/tts"

    response = requests.post(url, data=text, params={"voice": voice})
    with open("output.wav", "wb") as f:
        f.write(response.content)
    
    subprocess.run(["afplay", "output.wav"])

    # Let echo fade
    time.sleep(0.3)

    # Resetting flag
    bot_speaking = False


# Start listening
print("Say something (Ctrl+C to exit)...")

# Starts listening w. sounddevice
stream = sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16', # Blocksize in small chunks -> efficient
                       channels=1, callback=callback) # Callback to store audio

try:
    with stream:
        while True:
            data = q.get() # Grabs audio
            if rec.AcceptWaveform(data): # Is speech detected?
                result = json.loads(rec.Result()) # Decodes the speech
                command = result.get("text", "").lower() # Responds to what was said
                print(f"You said: {command.strip()}", flush=True)

                # # Basic command execution
                if ("shut down" in command) or ("goodbye" in command):
                    server_speak("Goodbye, powering down.")
                    break
                # if "hello" in command:
                #     print("Jarvis: Hello, how can I assist?")
                #     server_speak("Hello, how may I assist?")
                # elif "exit" in command:
                #     print("Jarvis: Goodbye!")
                #     server_speak("Goodbye!")
                #     break
                # elif "how are you" in command:
                #     server_speak("I think I'm fine, thank you. Not quite sure cause this is you testing my voice. Not sure what I think about that.")
                # elif "how's the weather today" in command:
                #     server_speak("it's gorgeous! Go outside you momma bear!")
                # elif "would you like a pork chop" in command:
                #     server_speak("I got one in my belly button, thank you very much.")
                # else:
                #     print("Jarvis: Command not recognized.")

                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3.2:latest", 
                        "prompt": command,
                        # "messages": [
                        #     {"role": "system", "content": "Your name is Tovia. You are a helpful and witty assistant that helps develop software and robotics applications."},
                        #     {"role": "user", "content": command}
                        # ]
                    },
                    stream=True # Because llama3.2 is responding in a stream format
                )

                # buffer = "" # Make a buffer to make speech sound more natural
                # for line in response.iter_lines(): # Each line of ollama stream
                #     if line: # Skipping empty lines
                #         data = json.loads(line) # JSON to Python dict
                #         token = data.get("response", "") # Gets response from chunk
                #         buffer += token

                #         # Speak when we've collected enough words to a sentence
                #         if token in {".", "?", "!"} or len(buffer.split()) >= 5:
                #             server_speak(buffer)
                #             buffer = ""
                        
                #         # If stream ended, speak leftovers and exit
                #         if data.get("done", False):
                #             if buffer.strip():
                #                 server_speak(buffer)
                #             break

                # Showing that Tovia is thinking
                print("\nTovia: Thinking...", end="\r", flush=True)

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
                                server_speak(buffer.strip())
                                buffer = ""
                                word_count = 0
                        
                        if data.get("done", False):
                            break
                
                # Finish up leftover text
                if buffer.strip():
                    server_speak(buffer.strip())
                
                print()
                # llama_response = str(response.text) # ["response"]
                # print(f"Tovia: {final_response}")
                # server_speak(final_response)
except KeyboardInterrupt:
    print("\nTovia: Goodbye! Shutting down gracefully.")
    stream.close()
    sys.exit(0)



# mimic3-server
# New terminal
# source mimic3_env/bin/activate
# python3 basic_tts_assist.py

# ollama list
