import sounddevice as sd

def callback(indata, frames, time, status):
    print("Got data:", indata.shape)

sd.RawInputStream(
    samplerate=16000,
    blocksize=8000,
    dtype='int16',
    channels=1,
    callback=callback,
    device=0  # AirPods mic
).start()
