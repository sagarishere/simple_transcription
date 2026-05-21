import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import transcription as t


class TranscriptionApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Audio Transcription")
        self.root.minsize(720, 520)

        self.event_queue: queue.Queue = queue.Queue()
        self.busy = False
        self.api_key_configured = False
        self.speaker_conversation: list[dict] | None = None

        self._build_api_key_panel()
        self._build_language_bar()
        self._build_notebook()
        self._try_load_api_key_from_env()
        self._update_app_state()
        self._poll_queue()

    def _try_load_api_key_from_env(self) -> None:
        if t.get_api_key():
            try:
                t.init_assemblyai()
                self.api_key_configured = True
            except ValueError:
                self.api_key_configured = False

    def _build_api_key_panel(self) -> None:
        self.api_key_frame = ttk.LabelFrame(
            self.root,
            text="API key is missing",
            padding=10,
        )

        ttk.Label(
            self.api_key_frame,
            text=(
                "No ASSEMBLYAI_API_KEY was found in your .env file or environment. "
                "Paste your AssemblyAI API key below, then click Save & continue."
            ),
            wraplength=680,
        ).pack(anchor="w", pady=(0, 8))

        self.api_key_text = tk.Text(self.api_key_frame, height=2, width=72, wrap="word")
        self.api_key_text.pack(fill="x", pady=(0, 8))

        options = ttk.Frame(self.api_key_frame)
        options.pack(fill="x")

        self.save_env_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options,
            text="Save to .env for next time",
            variable=self.save_env_var,
        ).pack(side="left")

        ttk.Button(
            options,
            text="Save & continue",
            command=self._submit_api_key,
        ).pack(side="right")

    def _submit_api_key(self) -> None:
        api_key = self.api_key_text.get("1.0", "end").strip()
        if not api_key:
            messagebox.showerror(
                "API key is missing",
                "Please enter your AssemblyAI API key in the text box.",
                parent=self.root,
            )
            self.api_key_text.focus_set()
            return

        try:
            t.configure_assemblyai(api_key)
            if self.save_env_var.get():
                t.save_api_key_to_env(api_key)
        except (ValueError, OSError) as exc:
            messagebox.showerror("API key is missing", str(exc), parent=self.root)
            return

        self.api_key_configured = True
        self.api_key_text.delete("1.0", "end")
        self.api_key_frame.pack_forget()
        self._update_app_state()
        messagebox.showinfo(
            "API key saved",
            "Your API key is set. You can start transcribing.",
            parent=self.root,
        )

    def _update_app_state(self) -> None:
        if self.api_key_configured:
            self.api_key_frame.pack_forget()
        elif not self.api_key_frame.winfo_ismapped():
            self.api_key_frame.pack(fill="x", padx=10, pady=(10, 0), before=self.language_frame)
            self.api_key_text.focus_set()

        enabled = self.api_key_configured and not self.busy
        readonly_state = "readonly" if enabled else "disabled"
        state = "normal" if enabled else "disabled"

        self.language_combo.configure(state=readonly_state)
        self.refresh_button.configure(state=state)
        self.transcribe_batch_button.configure(state=state)
        self.transcribe_speaker_button.configure(state=state)
        self.speaker_browse_button.configure(state=state)
        self.speaker_source_combo.configure(state=state)

        if not self.api_key_configured:
            self.save_speaker_button.configure(state="disabled")
        elif self.busy:
            self.save_speaker_button.configure(state="disabled")
        elif self.speaker_conversation:
            self.save_speaker_button.configure(state="normal")
        else:
            self.save_speaker_button.configure(state="disabled")

    def _require_api_key(self) -> bool:
        if self.api_key_configured:
            return True
        messagebox.showwarning(
            "API key is missing",
            "Enter your AssemblyAI API key in the box at the top of the window first.",
            parent=self.root,
        )
        self.api_key_text.focus_set()
        return False

    def _build_language_bar(self) -> None:
        self.language_frame = ttk.Frame(self.root, padding=(10, 10, 10, 0))
        self.language_frame.pack(fill="x")
        frame = self.language_frame

        ttk.Label(frame, text="Language:").pack(side="left")

        self.language_var = tk.StringVar(value=t.AUTO_LANGUAGE_LABEL)
        self.language_combo = ttk.Combobox(
            frame,
            textvariable=self.language_var,
            values=t.LANGUAGE_COMBO_VALUES,
            state="readonly",
            width=44,
        )
        self.language_combo.pack(side="left", padx=(6, 0))

        ttk.Label(
            frame,
            text="Auto detects language, or pick one of 103 supported codes.",
            foreground="gray",
        ).pack(side="left", padx=(8, 0))

    def _build_notebook(self) -> None:
        notebook = ttk.Notebook(self.root, padding=10)
        notebook.pack(fill="both", expand=True)

        batch_frame = ttk.Frame(notebook, padding=10)
        speaker_frame = ttk.Frame(notebook, padding=10)
        notebook.add(batch_frame, text="Batch")
        notebook.add(speaker_frame, text="Speaker-labeled")

        self._build_batch_tab(batch_frame)
        self._build_speaker_tab(speaker_frame)

    def _build_batch_tab(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", pady=(0, 8))

        self.refresh_button = ttk.Button(toolbar, text="Refresh", command=self.refresh_batch_list)
        self.refresh_button.pack(side="left")

        self.transcribe_batch_button = ttk.Button(
            toolbar,
            text="Transcribe pending",
            command=self.start_batch_transcription,
        )
        self.transcribe_batch_button.pack(side="left", padx=(8, 0))

        columns = ("file", "status")
        self.batch_tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        self.batch_tree.heading("file", text="File")
        self.batch_tree.heading("status", text="Status")
        self.batch_tree.column("file", width=420, anchor="w")
        self.batch_tree.column("status", width=100, anchor="center")
        self.batch_tree.pack(fill="both", expand=True)

        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill="x", pady=(8, 4))

        self.batch_progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.batch_progress.pack(fill="x")

        self.batch_status_label = ttk.Label(progress_frame, text="Ready")
        self.batch_status_label.pack(anchor="w", pady=(4, 0))

        self.batch_log = scrolledtext.ScrolledText(parent, height=8, state="disabled", wrap="word")
        self.batch_log.pack(fill="both", expand=True, pady=(8, 0))

        self.refresh_batch_list()

    def _build_speaker_tab(self, parent: ttk.Frame) -> None:
        source_frame = ttk.Frame(parent)
        source_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(source_frame, text="Source:").pack(side="left")

        self.speaker_source_var = tk.StringVar()
        self.speaker_source_combo = ttk.Combobox(
            source_frame,
            textvariable=self.speaker_source_var,
            width=50,
        )
        self.speaker_source_combo.pack(side="left", padx=(6, 6), fill="x", expand=True)

        self.speaker_browse_button = ttk.Button(
            source_frame,
            text="Browse…",
            command=self.browse_speaker_source,
        )
        self.speaker_browse_button.pack(side="left")

        action_frame = ttk.Frame(parent)
        action_frame.pack(fill="x", pady=(0, 8))

        self.transcribe_speaker_button = ttk.Button(
            action_frame,
            text="Transcribe",
            command=self.start_speaker_transcription,
        )
        self.transcribe_speaker_button.pack(side="left")

        self.save_speaker_button = ttk.Button(
            action_frame,
            text="Save conversation.json",
            command=self.save_speaker_output,
            state="disabled",
        )
        self.save_speaker_button.pack(side="left", padx=(8, 0))

        self.speaker_status_label = ttk.Label(action_frame, text="Ready")
        self.speaker_status_label.pack(side="left", padx=(12, 0))

        self.speaker_output = scrolledtext.ScrolledText(parent, height=20, state="disabled", wrap="word")
        self.speaker_output.pack(fill="both", expand=True)

        self._refresh_speaker_sources()

    def get_selected_language_code(self) -> str | None:
        label = self.language_var.get().strip()
        if label == t.AUTO_LANGUAGE_LABEL:
            return None
        code = t.LANGUAGE_LABEL_TO_CODE.get(label)
        if code is None:
            raise ValueError("Select a supported language from the list.")
        return code

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self._update_app_state()

    def _append_batch_log(self, message: str) -> None:
        self.batch_log.configure(state="normal")
        self.batch_log.insert("end", message + "\n")
        self.batch_log.see("end")
        self.batch_log.configure(state="disabled")

    def _set_speaker_output(self, text: str) -> None:
        self.speaker_output.configure(state="normal")
        self.speaker_output.delete("1.0", "end")
        self.speaker_output.insert("1.0", text)
        self.speaker_output.configure(state="disabled")

    def refresh_batch_list(self) -> None:
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)

        for audio_name in t.list_audio_files():
            status = t.get_file_status(audio_name)
            display_status = "Done" if status == "done" else "Pending"
            self.batch_tree.insert("", "end", values=(audio_name, display_status))

        pending_count = len(t.get_pending_files())
        self.batch_status_label.configure(
            text=f"{pending_count} pending file(s)" if pending_count else "All files transcribed"
        )

    def _refresh_speaker_sources(self) -> None:
        values = [f"{t.AUDIO_DIR}/{name}" for name in t.list_audio_files()]
        self.speaker_source_combo.configure(values=values)
        if values and not self.speaker_source_var.get():
            self.speaker_source_var.set(values[0])

    def browse_speaker_source(self) -> None:
        path = filedialog.askopenfilename(
            title="Select audio file",
            initialdir=os.path.abspath(t.AUDIO_DIR),
            filetypes=[
                ("Audio files", "*.mp3 *.m4a *.wav *.mp4 *.aac *.flac *.ogg *.webm"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.speaker_source_var.set(path)

    def start_batch_transcription(self) -> None:
        if self.busy or not self._require_api_key():
            return

        try:
            language_code = self.get_selected_language_code()
        except ValueError as exc:
            messagebox.showerror("Language", str(exc))
            return

        pending_files = t.get_pending_files()
        if not pending_files:
            messagebox.showinfo("Batch", "All audio files already have transcripts.")
            return

        self._set_busy(True)
        self.batch_progress.configure(maximum=len(pending_files), value=0)
        self._append_batch_log(f"Starting batch transcription ({len(pending_files)} file(s)).")

        def worker() -> None:
            try:
                def on_progress(current: int, total: int, name: str, status: str) -> None:
                    self.event_queue.put(("batch_progress", current, total, name, status))

                results = t.transcribe_batch(
                    language_code=language_code,
                    on_progress=on_progress,
                )
                self.event_queue.put(("batch_done", results))
            except Exception as exc:
                self.event_queue.put(("error", "Batch transcription", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def start_speaker_transcription(self) -> None:
        if self.busy or not self._require_api_key():
            return

        source = self.speaker_source_var.get().strip()
        if not source:
            messagebox.showerror("Speaker-labeled", "Select or enter an audio source.")
            return

        source = t.resolve_audio_path(source)
        if not source.startswith(("http://", "https://")) and not os.path.exists(source):
            messagebox.showerror(
                "Speaker-labeled",
                f"Audio file not found.\n"
                f"Put files in {t.AUDIO_DIR}/ or choose a valid path or http(s) URL.",
            )
            return

        try:
            language_code = self.get_selected_language_code()
        except ValueError as exc:
            messagebox.showerror("Language", str(exc))
            return

        self._set_busy(True)
        self.speaker_status_label.configure(text="Transcribing…")
        self._set_speaker_output("")

        def worker() -> None:
            try:
                result = t.transcribe_file(
                    source,
                    speaker_labels=True,
                    language_code=language_code,
                )
                self.event_queue.put(("speaker_done", result))
            except Exception as exc:
                self.event_queue.put(("error", "Speaker transcription", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def save_speaker_output(self) -> None:
        if not self._require_api_key():
            return

        if not self.speaker_conversation:
            messagebox.showinfo("Speaker-labeled", "Nothing to save. Transcribe a file first.")
            return

        path = t.save_speaker_conversation(self.speaker_conversation)
        self.speaker_status_label.configure(text=f"Saved {path}")
        messagebox.showinfo("Speaker-labeled", f"Saved to {path}")

    def _poll_queue(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]

        if kind == "batch_progress":
            _, current, total, name, status = event
            self.batch_progress.configure(maximum=total, value=current - 1 if status == "transcribing" else current)
            if status == "transcribing":
                self.batch_status_label.configure(text=f"Transcribing {current}/{total}: {name}")
                self._append_batch_log(f"Transcribing ({current}/{total}): {t.AUDIO_DIR}/{name}")
            elif status == "done":
                self.batch_progress.configure(value=current)
            elif status == "failed":
                self.batch_progress.configure(value=current)

        elif kind == "batch_done":
            _, results = event
            for audio_name, success, message in results:
                if success:
                    self._append_batch_log(message)
                else:
                    self._append_batch_log(f"Failed: {audio_name} -> {message}")
            self.batch_progress.configure(value=self.batch_progress["maximum"])
            self.batch_status_label.configure(text="Batch complete")
            self.refresh_batch_list()
            self._set_busy(False)

        elif kind == "speaker_done":
            _, result = event
            if not isinstance(result, list):
                messagebox.showerror("Speaker-labeled", "Unexpected transcription result.")
                self._set_busy(False)
                return

            self.speaker_conversation = result
            lines = [f"Speaker {entry['speaker']}: {entry['text']}" for entry in result]
            self._set_speaker_output("\n".join(lines))
            self.speaker_status_label.configure(text=f"Done ({len(result)} utterances)")
            self.save_speaker_button.configure(state="normal")
            path = t.save_speaker_conversation(result)
            self.speaker_status_label.configure(text=f"Done — auto-saved {path}")
            self._set_busy(False)

        elif kind == "error":
            _, title, message = event
            messagebox.showerror(title, message)
            self.batch_status_label.configure(text="Ready")
            self.speaker_status_label.configure(text="Ready")
            self._set_busy(False)


def main() -> None:
    root = tk.Tk()
    t.ensure_directories()
    TranscriptionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
