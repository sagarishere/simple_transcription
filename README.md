# Audio to Text

Batch and speaker-labeled transcription using [AssemblyAI](https://www.assemblyai.com/).

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set your API key in a `.env` file (recommended):

```
ASSEMBLYAI_API_KEY=your_key_here
```

   If the key is missing when you launch the GUI, a box at the top of the main window asks for it (with a text area to paste the key). You can optionally save it to `.env` from there.

3. Place audio files in the `audio/` directory (created automatically if missing when using the GUI).

## Desktop UI (Tkinter)

```bash
python3 gui.py
```

The app has two tabs:

- **Batch** — Scans `audio/` for supported files, shows Pending/Done status, and transcribes files that do not yet have a matching `transcripts/<name>.json`.
- **Speaker-labeled** — Transcribes one file (from `audio/` or via Browse) with speaker diarization and saves `conversation.json`.

### Language

At the top of the window, choose how AssemblyAI should handle language:

- **Auto (detect language)** (default) — Uses `language_detection=True` (same as the CLI scripts).
- **A specific language** — Sets `language_code` manually. The dropdown lists all **103** languages from [AssemblyAI supported languages](https://www.assemblyai.com/docs/pre-recorded-audio/supported-languages) (e.g. `en`, `es`, `et`, `en_us`).

With a manual language code, some features (such as speaker labels) may not be available for every language; the API returns an error in that case.

## CLI

### Batch transcription

```bash
python3 audio2txt.py
```

- Looks in `audio/` for audio files.
- Checks `transcripts/` for matching `<same-name>.json` files.
- Transcribes only files that do not yet have a matching transcript.
- Saves transcripts to `transcripts/` with the same base filename and `.json` extension.
- Uses automatic language detection by default.

### Speaker-labeled (single file)

```bash
python3 audio2txtSpeakerLabeled.py [path_or_url]
```

Transcribes one file with speaker labels and writes `conversation.json`. Requires a path or URL argument.
