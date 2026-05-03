import librosa
import noisereduce as nr
import soundfile as sf

# Load audio
audio, sr = librosa.load("input.wav", sr=None)

# Reduce noise
reduced_noise = nr.reduce_noise(y=audio, sr=sr)

# Save output
sf.write("cleaned.wav", reduced_noise, sr)