import assemblyai as aai
import os

# import the API key from the .env file
from dotenv import load_dotenv
load_dotenv()

# Replace with your API key
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

# URL or file path of the file to transcribe
FILE_URL = "./Mirka Feedback 2024 09 26 13 02 36.mp3"

transcriber = aai.Transcriber()
transcript = transcriber.transcribe(FILE_URL)

if transcript.status == aai.TranscriptStatus.error:
    print(transcript.error)
else:
    # save the transcript to a file
    with open("transcript.txt", "w") as f:
        f.write(transcript.text)
    print(transcript.text)
