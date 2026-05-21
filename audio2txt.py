import sys

import transcription as t


def main() -> None:
    t.init_assemblyai()
    t.ensure_directories()

    audio_files = t.list_audio_files()
    if not audio_files:
        print(f"No supported audio files found in '{t.AUDIO_DIR}'.")
        raise SystemExit(0)

    pending_files = t.get_pending_files()
    if not pending_files:
        print("All audio files already have transcripts.")
        raise SystemExit(0)

    print(f"Found {len(pending_files)} file(s) to transcribe.")

    def on_progress(current: int, total: int, name: str, status: str) -> None:
        if status == "transcribing":
            audio_path = f"{t.AUDIO_DIR}/{name}"
            print(f"Transcribing ({current}/{total}): {audio_path}")

    results = t.transcribe_batch(on_progress=on_progress)
    for audio_name, success, message in results:
        if success:
            print(message)
        else:
            print(f"Failed: {audio_name} -> {message}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
