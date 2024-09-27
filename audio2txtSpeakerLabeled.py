import json
import assemblyai as aai
import os

from dotenv import load_dotenv
load_dotenv()
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

# URL or filepath of the file to transcribe
FILE_URL = "./Mirka Feedback 2024 09 26 13 02 36.mp3"

config = aai.TranscriptionConfig(speaker_labels=True)

transcriber = aai.Transcriber()
transcript = transcriber.transcribe(
    FILE_URL,
    config=config
)

conversation = []

for utterance in transcript.utterances:
    # add it to a list of dictionaries
    conversation.append({
        "speaker": utterance.speaker,
        "text": utterance.text
    })

    print(f"Speaker {utterance.speaker}: {utterance.text}")
    
# save the conversation to a file
with open("conversation.json", "w") as f:
    f.write(json.dumps(conversation))
