# Audio to Text

A batch transcription script that uses AssemblyAI.

How it works:
- Looks in `audio/` for audio files.
- Checks `transcripts/` for matching `<same-name>.json` files.
- Transcribes only files that do not yet have a matching transcript.
- Saves transcripts to `transcripts/` with the same base filename and `.json` extension.

Usage:
```bash
python3 audio2txt.py
```
