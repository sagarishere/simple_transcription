import json
import assemblyai as aai
import os
import sys

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ASSEMBLYAI_API_KEY")
if not api_key:
    raise ValueError("Missing ASSEMBLYAI_API_KEY in environment variables.")

aai.settings.api_key = api_key

# URL or filepath of the file to transcribe.
# You can override the default by passing a first CLI argument:
# python3 audio2txtSpeakerLabeled.py ./audio/example.m4a
FILE_URL = sys.argv[1] if len(sys.argv) > 1 else "./audio/police_and_border_call_estonia.m4a"

if not FILE_URL.startswith(("http://", "https://")) and not os.path.exists(FILE_URL):
    raise FileNotFoundError(
        f"Audio file not found: {FILE_URL}\n"
        "Use an absolute path, a correct relative path, or a public URL."
    )

config = aai.TranscriptionConfig(
    speech_models=["universal-3-pro", "universal-2"],
    language_detection=True,
    speaker_labels=True,
)

transcriber = aai.Transcriber()
transcript = transcriber.transcribe(
    FILE_URL,
    config=config
)

if transcript.status == aai.TranscriptStatus.error:
    raise RuntimeError(f"Transcription failed: {transcript.error}")

conversation = []

for utterance in transcript.utterances:
    # add it to a list of dictionaries
    conversation.append({
        "speaker": utterance.speaker,
        "text": utterance.text
    })

    print(f"Speaker {utterance.speaker}: {utterance.text}")
    
# save the conversation to a file
with open("conversation.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(conversation, ensure_ascii=False, indent=2))
