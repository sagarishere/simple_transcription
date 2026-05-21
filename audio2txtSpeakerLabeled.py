import os
import sys

import transcription as t


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python3 audio2txtSpeakerLabeled.py <path_or_url>",
            file=sys.stderr,
        )
        raise SystemExit(1)

    file_url = sys.argv[1]

    if not file_url.startswith(("http://", "https://")) and not os.path.exists(file_url):
        raise FileNotFoundError(
            f"Audio file not found: {file_url}\n"
            "Use an absolute path, a correct relative path, or a public URL."
        )

    t.init_assemblyai()
    conversation = t.transcribe_file(file_url, speaker_labels=True)

    if not isinstance(conversation, list):
        raise RuntimeError("Expected speaker-labeled conversation.")

    for entry in conversation:
        print(f"Speaker {entry['speaker']}: {entry['text']}")

    output_path = t.save_speaker_conversation(conversation)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
