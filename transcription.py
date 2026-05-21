import json
import os
from typing import Callable

import assemblyai as aai
from dotenv import load_dotenv

AUDIO_DIR = "./audio"
TRANSCRIPTS_DIR = "./transcripts"
SUPPORTED_EXTENSIONS = {
    ".mp3", ".m4a", ".wav", ".mp4", ".aac", ".flac", ".ogg", ".webm", ".mpeg", ".mpga",
}

from supported_languages import MANUAL_LANGUAGE_CHOICES

AUTO_LANGUAGE_LABEL = "Auto (detect language)"

LANGUAGE_CHOICES: list[tuple[str, str | None]] = [
    (AUTO_LANGUAGE_LABEL, None),
    *MANUAL_LANGUAGE_CHOICES,
]

LANGUAGE_COMBO_VALUES = [label for label, _ in LANGUAGE_CHOICES]
LANGUAGE_LABEL_TO_CODE = {label: code for label, code in LANGUAGE_CHOICES}


def get_api_key() -> str | None:
    load_dotenv()
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if api_key:
        return api_key.strip()
    return None


def configure_assemblyai(api_key: str) -> None:
    key = api_key.strip()
    if not key:
        raise ValueError("API key cannot be empty.")
    aai.settings.api_key = key
    os.environ["ASSEMBLYAI_API_KEY"] = key


def save_api_key_to_env(api_key: str, env_path: str = ".env") -> None:
    key = api_key.strip()
    if not key:
        raise ValueError("API key cannot be empty.")

    lines: list[str] = []
    key_written = False
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            lines = f.read().splitlines()

    updated: list[str] = []
    for line in lines:
        if line.startswith("ASSEMBLYAI_API_KEY="):
            updated.append(f"ASSEMBLYAI_API_KEY={key}")
            key_written = True
        else:
            updated.append(line)

    if not key_written:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append(f"ASSEMBLYAI_API_KEY={key}")

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(updated) + "\n")


def init_assemblyai(api_key: str | None = None) -> None:
    load_dotenv()
    key = (api_key or os.getenv("ASSEMBLYAI_API_KEY") or "").strip()
    if not key:
        raise ValueError("Missing ASSEMBLYAI_API_KEY in environment variables.")
    configure_assemblyai(key)


def ensure_directories() -> None:
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def resolve_audio_path(path_or_name: str) -> str:
    """Resolve a path or filename to an existing local file, defaulting to AUDIO_DIR."""
    value = path_or_name.strip()
    if value.startswith(("http://", "https://")):
        return value
    if os.path.exists(value):
        return value

    in_audio_dir = os.path.join(AUDIO_DIR, value)
    if os.path.exists(in_audio_dir):
        return in_audio_dir

    basename = os.path.basename(value)
    in_audio_dir = os.path.join(AUDIO_DIR, basename)
    if os.path.exists(in_audio_dir):
        return in_audio_dir

    return value


def build_transcription_config(
    *,
    speaker_labels: bool = False,
    language_code: str | None = None,
) -> aai.TranscriptionConfig:
    kwargs: dict = {
        "speech_models": ["universal-3-pro", "universal-2"],
    }
    if speaker_labels:
        kwargs["speaker_labels"] = True
    if language_code:
        kwargs["language_code"] = language_code.strip().lower()
    else:
        kwargs["language_detection"] = True
    return aai.TranscriptionConfig(**kwargs)


def list_audio_files() -> list[str]:
    if not os.path.isdir(AUDIO_DIR):
        return []
    audio_files = []
    for name in sorted(os.listdir(AUDIO_DIR)):
        file_path = os.path.join(AUDIO_DIR, name)
        extension = os.path.splitext(name)[1].lower()
        if os.path.isfile(file_path) and extension in SUPPORTED_EXTENSIONS:
            audio_files.append(name)
    return audio_files


def transcript_path_for(audio_name: str) -> str:
    base_name, _ = os.path.splitext(audio_name)
    return os.path.join(TRANSCRIPTS_DIR, f"{base_name}.json")


def get_file_status(audio_name: str) -> str:
    if os.path.exists(transcript_path_for(audio_name)):
        return "done"
    return "pending"


def get_pending_files() -> list[str]:
    return [name for name in list_audio_files() if get_file_status(name) == "pending"]


def save_batch_transcript(audio_name: str, text: str) -> str:
    transcript_path = transcript_path_for(audio_name)
    payload = {
        "file_name": audio_name,
        "transcript": text,
    }
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return transcript_path


def save_speaker_conversation(
    conversation: list[dict],
    path: str = "conversation.json",
) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    return path


def transcribe_file(
    audio_path: str,
    *,
    speaker_labels: bool = False,
    language_code: str | None = None,
) -> str | list[dict]:
    config = build_transcription_config(
        speaker_labels=speaker_labels,
        language_code=language_code,
    )
    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(audio_path)

    if transcript.status == aai.TranscriptStatus.error:
        raise RuntimeError(transcript.error or "Transcription failed.")

    if speaker_labels:
        conversation = []
        for utterance in transcript.utterances or []:
            conversation.append({
                "speaker": utterance.speaker,
                "text": utterance.text,
            })
        return conversation

    return transcript.text or ""


def transcribe_batch(
    *,
    language_code: str | None = None,
    on_progress: Callable[[int, int, str, str], None] | None = None,
) -> list[tuple[str, bool, str]]:
    pending_files = get_pending_files()
    results: list[tuple[str, bool, str]] = []
    total = len(pending_files)

    for index, audio_name in enumerate(pending_files, start=1):
        audio_path = os.path.join(AUDIO_DIR, audio_name)
        if on_progress:
            on_progress(index, total, audio_name, "transcribing")

        try:
            text = transcribe_file(audio_path, language_code=language_code)
            if not isinstance(text, str):
                raise RuntimeError("Expected plain text transcript.")
            transcript_path = save_batch_transcript(audio_name, text)
            message = f"Saved: {transcript_path}"
            results.append((audio_name, True, message))
            if on_progress:
                on_progress(index, total, audio_name, "done")
        except Exception as exc:
            message = str(exc)
            results.append((audio_name, False, message))
            if on_progress:
                on_progress(index, total, audio_name, "failed")

    return results
