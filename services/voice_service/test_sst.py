import whisper

print("Loading Whisper model...")
model = whisper.load_model("small")

print("Transcribing audio...")
result = model.transcribe("output.wav", language="fr")

print("✅ Transcription result:")
print(result["text"])