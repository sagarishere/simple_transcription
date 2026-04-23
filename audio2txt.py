import json
import assemblyai as aai
import os

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ASSEMBLYAI_API_KEY")
if not api_key:
    raise ValueError("Missing ASSEMBLYAI_API_KEY in environment variables.")

aai.settings.api_key = api_key

AUDIO_DIR = "audio"
TRANSCRIPTS_DIR = "transcripts"
SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".mp4", ".aac", ".flac", ".ogg", ".webm", ".mpeg", ".mpga"}

if not os.path.isdir(AUDIO_DIR):
    raise FileNotFoundError(f"Audio directory not found: {AUDIO_DIR}")

os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

config = aai.TranscriptionConfig(
    speech_models=["universal-3-pro", "universal-2"],
    language_detection=True,
)

transcriber = aai.Transcriber(config=config)

audio_files = []
for name in sorted(os.listdir(AUDIO_DIR)):
    file_path = os.path.join(AUDIO_DIR, name)
    extension = os.path.splitext(name)[1].lower()
    if os.path.isfile(file_path) and extension in SUPPORTED_EXTENSIONS:
        audio_files.append(name)

if not audio_files:
    print(f"No supported audio files found in '{AUDIO_DIR}'.")
    raise SystemExit(0)

pending_files = []
for audio_name in audio_files:
    base_name, _ = os.path.splitext(audio_name)
    transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}.json")
    if not os.path.exists(transcript_path):
        pending_files.append(audio_name)

if not pending_files:
    print("All audio files already have transcripts.")
    raise SystemExit(0)

print(f"Found {len(pending_files)} file(s) to transcribe.")

for audio_name in pending_files:
    audio_path = os.path.join(AUDIO_DIR, audio_name)
    base_name, _ = os.path.splitext(audio_name)
    transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}.json")

    print(f"Transcribing: {audio_path}")
    transcript = transcriber.transcribe(audio_path)

    if transcript.status == aai.TranscriptStatus.error:
        print(f"Failed: {audio_name} -> {transcript.error}")
        continue

    payload = {
        "file_name": audio_name,
        "transcript": transcript.text or "",
    }
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Saved: {transcript_path}")
