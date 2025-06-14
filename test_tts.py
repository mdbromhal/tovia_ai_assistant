import pyttsx3

engine = pyttsx3.init()

# Get available voices
voices = engine.getProperty('voices')

# for idx, voice in enumerate(voices):
#     print(f"Voice {idx}: {voice.name}")

#     # Choose a specific voice (replace the index with one from the list)
    # engine.setProperty('voice', voices[idx].id)  # Example: Switch to a different voice

# Change volume (range 0.0 to 1.0)
# engine.setProperty('volume', 0.8)  # Example: 80% volume

engine.setProperty('voice', voices[45].id)
# engine.say("I am using a different voice now.")
# engine.runAndWait()

engine.say("Здраствоисте! Я твои друг!")
engine.runAndWait()
