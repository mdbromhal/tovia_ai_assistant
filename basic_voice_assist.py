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
    if status:
        print(status)
    #q.put(np.frombuffer(indata, dtype=np.int16))
    q.put(bytes(indata)) # Convert to bytes that Vosk likes

# Start listening
print("Say something (Ctrl+C to exit)...")

# Starts listening w. sounddevice
with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16', # Blocksize in small chunks -> efficient
                       channels=1, callback=callback): # Callback to store audio
    while True:
        data = q.get() # Grabs audio
        if rec.AcceptWaveform(data): # Is speech detected?
            result = json.loads(rec.Result()) # Decodes the speech
            command = result.get("text", "").lower() # Responds to what was said
            print(f"You said: {command}")

            # Basic command execution
            if "hello" in command:
                print("Jarvis: Hello, how can I assist?")
            elif "exit" in command:
                print("Jarvis: Goodbye!")
                break
            else:
                print("Jarvis: Command not recognized.")
