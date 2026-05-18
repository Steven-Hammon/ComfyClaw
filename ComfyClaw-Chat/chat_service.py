import json
import os
import shutil
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = APP_DIR / "chat_settings.json"
POLL_INTERVAL = 1000
USER_KEY_PREFIX = "<USER>"
AGENT_KEY_PREFIX = "<AGENT>"

DEFAULT_SETTINGS = {
    "download_dir": str(APP_DIR / "downloads"),
    "chat_to_agent_file": str(APP_DIR / "FromChat.txt"),
    "agent_to_chat_file": str(APP_DIR / "ToChat.txt"),
    "user_name": "You",
    "agent_name": "Agent",
}


def load_settings() -> dict[str, str]:
    settings = DEFAULT_SETTINGS.copy()
    if not SETTINGS_PATH.exists():
        return settings

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings

    for key in settings:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            settings[key] = value.strip()
    return settings


def save_settings(settings: dict[str, str]) -> None:
    SETTINGS_PATH.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def backup_file(path: Path) -> Path:
    timestamp = int(time.time())
    backup = path.with_name(f"{path.name}.backup-{timestamp}")
    counter = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.backup-{timestamp}-{counter}")
        counter += 1
    shutil.copy2(path, backup)
    return backup


def read_json_object(path: Path) -> tuple[dict, str | None]:
    if not path.exists():
        return {}, None

    raw = path.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return {}, None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        backup = backup_file(path)
        return {}, f"Outgoing file was not JSON. Backed it up to {backup.name}."

    if not isinstance(data, dict):
        backup = backup_file(path)
        return {}, f"Outgoing file was not a JSON object. Backed it up to {backup.name}."

    return data, None


def append_user_message(path_value: str, message: str) -> tuple[str, str | None]:
    path = Path(path_value).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    data, notice = read_json_object(path)
    timestamp = int(time.time())
    key = f"{USER_KEY_PREFIX}{timestamp}"
    while key in data:
        timestamp += 1
        key = f"{USER_KEY_PREFIX}{timestamp}"

    data[key] = message
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, path)
    return key, notice


def unique_download_path(download_dir_value: str, source_name: str) -> Path:
    download_dir = Path(download_dir_value).expanduser()
    download_dir.mkdir(parents=True, exist_ok=True)

    source_path = Path(source_name)
    stem = source_path.stem or "attachment"
    suffix = source_path.suffix
    target = download_dir / source_path.name
    counter = 1

    while target.exists():
        target = download_dir / f"{stem} ({counter}){suffix}"
        counter += 1

    return target


def copy_attachment_to_downloads(source_value: str, download_dir_value: str) -> Path:
    source = Path(source_value).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Attachment not found: {source}")

    target = unique_download_path(download_dir_value, source.name)
    shutil.copy2(source, target)
    return target


class ChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("File Chat")
        self.root.geometry("860x640")
        self.root.minsize(560, 420)

        settings = load_settings()
        self.download_dir = tk.StringVar(value=settings["download_dir"])
        self.chat_to_agent_file = tk.StringVar(value=settings["chat_to_agent_file"])
        self.agent_to_chat_file = tk.StringVar(value=settings["agent_to_chat_file"])
        self.user_name = tk.StringVar(value=settings["user_name"])
        self.agent_name = tk.StringVar(value=settings["agent_name"])
        self.status_var = tk.StringVar(value="Ready.")
        self.incoming_path_var = tk.StringVar()

        self._incoming_stamp = None
        self._attached_files: list[Path] = []
        self._message_history: list[tuple[str, str]] = []

        self._configure_style()
        self._build_ui()
        self._ensure_configured_paths()
        self._update_path_labels()
        self._schedule_poll()

    def _configure_style(self) -> None:
        self.root.configure(bg="#f3f4f6")
        self.root.option_add("*Font", "{Segoe UI} 10")

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background="#f3f4f6")
        style.configure("Top.TFrame", background="#111827")
        style.configure("Composer.TFrame", background="#f3f4f6")
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Title.TLabel", background="#111827", foreground="#f9fafb", font=("Segoe UI", 12, "bold"))
        style.configure("TopStatus.TLabel", background="#111827", foreground="#d1d5db")
        style.configure("Muted.TLabel", background="#f3f4f6", foreground="#6b7280")
        style.configure("Path.TLabel", background="#f3f4f6", foreground="#374151")
        style.configure("TButton", padding=(12, 7), font=("Segoe UI", 10))
        style.configure("Accent.TButton", background="#2563eb", foreground="#ffffff")
        style.map(
            "Accent.TButton",
            background=[("active", "#1d4ed8"), ("disabled", "#9ca3af")],
            foreground=[("disabled", "#f9fafb")],
        )
        style.configure("Menu.TMenubutton", padding=(12, 7), font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self._build_top_bar()
        self._build_chat_area()
        self._build_composer()

    def _build_top_bar(self) -> None:
        top_bar = ttk.Frame(self.root, style="Top.TFrame", padding=(12, 10))
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.grid_columnconfigure(2, weight=1)

        menu_button = ttk.Menubutton(top_bar, text="Menu", style="Menu.TMenubutton")
        menu = tk.Menu(menu_button, tearoff=False)
        menu.add_command(label="Settings...", command=self._open_settings)
        menu_button["menu"] = menu
        menu_button.grid(row=0, column=0, sticky="w")

        ttk.Label(top_bar, text="File Chat", style="Title.TLabel").grid(
            row=0, column=1, padx=(12, 16), sticky="w"
        )
        ttk.Label(top_bar, textvariable=self.status_var, style="TopStatus.TLabel").grid(
            row=0, column=2, sticky="ew"
        )

    def _build_chat_area(self) -> None:
        main = ttk.Frame(self.root, style="App.TFrame", padding=(12, 12, 12, 6))
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(main, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.grid_columnconfigure(1, weight=1)

        ttk.Label(header, text="Agent_To_Chat", style="Muted.TLabel", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, textvariable=self.incoming_path_var, style="Path.TLabel").grid(
            row=0, column=1, padx=(10, 0), sticky="ew"
        )

        display_frame = tk.Frame(main, bg="#d1d5db", bd=1, relief=tk.SOLID)
        display_frame.grid(row=1, column=0, sticky="nsew")
        display_frame.grid_columnconfigure(0, weight=1)
        display_frame.grid_rowconfigure(0, weight=1)

        self.display_text = tk.Text(
            display_frame,
            state=tk.DISABLED,
            bg="#ffffff",
            fg="#111827",
            bd=0,
            padx=14,
            pady=12,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
        )
        self.display_text.grid(row=0, column=0, sticky="nsew")

        display_scroll = ttk.Scrollbar(display_frame, orient=tk.VERTICAL, command=self.display_text.yview)
        display_scroll.grid(row=0, column=1, sticky="ns")
        self.display_text.configure(yscrollcommand=display_scroll.set)

        self.display_text.tag_configure("placeholder", foreground="#6b7280", font=("Segoe UI", 10, "italic"))
        self.display_text.tag_configure("role_user", foreground="#2563eb", font=("Segoe UI", 10, "bold"))
        self.display_text.tag_configure("role_agent", foreground="#047857", font=("Segoe UI", 10, "bold"))
        self.display_text.tag_configure("role_other", foreground="#4b5563", font=("Segoe UI", 10, "bold"))
        self.display_text.tag_configure("message", lmargin1=12, lmargin2=12, spacing3=12)
        self.display_text.tag_configure("raw", lmargin1=0, lmargin2=0, spacing3=6)

    def _build_composer(self) -> None:
        composer = ttk.Frame(self.root, style="Composer.TFrame", padding=(12, 6, 12, 12))
        composer.grid(row=2, column=0, sticky="ew")
        composer.grid_columnconfigure(0, weight=1)

        input_frame = tk.Frame(composer, bg="#d1d5db", bd=1, relief=tk.SOLID)
        input_frame.grid(row=0, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_text = tk.Text(
            input_frame,
            height=4,
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            bd=0,
            padx=12,
            pady=10,
            wrap=tk.WORD,
            undo=True,
            font=("Segoe UI", 10),
        )
        self.input_text.grid(row=0, column=0, sticky="ew")

        input_scroll = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        input_scroll.grid(row=0, column=1, sticky="ns")
        self.input_text.configure(yscrollcommand=input_scroll.set)
        self.input_text.bind("<Control-Return>", lambda event: self._send_message())

        actions = ttk.Frame(composer, style="Composer.TFrame")
        actions.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        actions.grid_columnconfigure(0, weight=1)

        self.attach_button = ttk.Button(actions, text="Attach File", command=self._attach_file)
        self.attach_button.grid(row=0, column=1, padx=(0, 8), sticky="e")

        self.send_button = ttk.Button(actions, text="Send", style="Accent.TButton", command=self._send_message)
        self.send_button.grid(row=0, column=2, sticky="e")

    def _open_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg="#f3f4f6")

        fields = ttk.Frame(dialog, style="App.TFrame", padding=16)
        fields.grid(row=0, column=0, sticky="nsew")
        fields.grid_columnconfigure(1, weight=1)

        download_var = tk.StringVar(value=self.download_dir.get())
        outgoing_var = tk.StringVar(value=self.chat_to_agent_file.get())
        incoming_var = tk.StringVar(value=self.agent_to_chat_file.get())
        user_name_var = tk.StringVar(value=self.user_name.get())
        agent_name_var = tk.StringVar(value=self.agent_name.get())

        self._add_path_row(
            fields,
            0,
            "Download directory",
            download_var,
            lambda: self._browse_directory(download_var),
        )
        self._add_path_row(
            fields,
            1,
            "Chat_To_Agent file path (outgoing)",
            outgoing_var,
            lambda: self._browse_file(outgoing_var, "Select Chat_To_Agent file"),
        )
        self._add_path_row(
            fields,
            2,
            "Agent_To_Chat file path (incoming)",
            incoming_var,
            lambda: self._browse_file(incoming_var, "Select Agent_To_Chat file"),
        )
        self._add_text_row(fields, 3, "User display name", user_name_var)
        self._add_text_row(fields, 4, "Agent display name", agent_name_var)

        buttons = ttk.Frame(fields, style="App.TFrame")
        buttons.grid(row=5, column=0, columnspan=3, sticky="e", pady=(16, 0))

        ttk.Button(buttons, text="Cancel", command=dialog.destroy).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            buttons,
            text="Save",
            style="Accent.TButton",
            command=lambda: self._save_settings_dialog(
                dialog,
                download_var,
                outgoing_var,
                incoming_var,
                user_name_var,
                agent_name_var,
            ),
        ).grid(row=0, column=1)

        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dialog.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")

    def _add_path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        browse_command,
    ) -> None:
        ttk.Label(parent, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=6)
        entry = ttk.Entry(parent, textvariable=variable, width=58)
        entry.grid(row=row, column=1, sticky="ew", padx=(10, 8), pady=6)
        ttk.Button(parent, text="Browse", command=browse_command).grid(row=row, column=2, sticky="e", pady=6)

    def _add_text_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=6)
        entry = ttk.Entry(parent, textvariable=variable, width=32)
        entry.grid(row=row, column=1, sticky="w", padx=(10, 8), pady=6)

    def _browse_directory(self, variable: tk.StringVar) -> None:
        initial = variable.get() if Path(variable.get()).exists() else str(APP_DIR)
        path = filedialog.askdirectory(title="Select download directory", initialdir=initial)
        if path:
            variable.set(path)

    def _browse_file(self, variable: tk.StringVar, title: str) -> None:
        current = Path(variable.get()).expanduser()
        initial_dir = str(current.parent if current.parent.exists() else APP_DIR)
        path = filedialog.askopenfilename(
            title=title,
            initialdir=initial_dir,
            initialfile=current.name,
            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            variable.set(path)

    def _save_settings_dialog(
        self,
        dialog: tk.Toplevel,
        download_var: tk.StringVar,
        outgoing_var: tk.StringVar,
        incoming_var: tk.StringVar,
        user_name_var: tk.StringVar,
        agent_name_var: tk.StringVar,
    ) -> None:
        settings = {
            "download_dir": download_var.get().strip(),
            "chat_to_agent_file": outgoing_var.get().strip(),
            "agent_to_chat_file": incoming_var.get().strip(),
            "user_name": user_name_var.get().strip(),
            "agent_name": agent_name_var.get().strip(),
        }

        missing = [name for name, value in settings.items() if not value]
        if missing:
            messagebox.showerror("Missing setting", "All settings need a value.")
            return

        self.download_dir.set(settings["download_dir"])
        self.chat_to_agent_file.set(settings["chat_to_agent_file"])
        self.agent_to_chat_file.set(settings["agent_to_chat_file"])
        self.user_name.set(settings["user_name"])
        self.agent_name.set(settings["agent_name"])

        try:
            self._ensure_configured_paths()
            save_settings(settings)
        except OSError as exc:
            messagebox.showerror("Settings error", f"Could not save settings:\n\n{exc}")
            return

        self._incoming_stamp = None
        self._update_path_labels()
        self._render_display()
        self._poll_incoming_file()
        self._flash_status("Settings saved.")
        dialog.destroy()

    def _ensure_configured_paths(self) -> None:
        Path(self.download_dir.get()).expanduser().mkdir(parents=True, exist_ok=True)

        for path_value in (self.chat_to_agent_file.get(), self.agent_to_chat_file.get()):
            path = Path(path_value).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)

    def _update_path_labels(self) -> None:
        incoming = Path(self.agent_to_chat_file.get()).expanduser()
        outgoing = Path(self.chat_to_agent_file.get()).expanduser()
        self.incoming_path_var.set(str(incoming))
        self.status_var.set(f"Outgoing: {outgoing.name}  |  Incoming: {incoming.name}")

    def _attach_file(self) -> None:
        path = filedialog.askopenfilename(title="Attach file")
        if not path:
            return

        attached_path = Path(path)
        self._attached_files.append(attached_path)
        current = self.input_text.get("1.0", "end-1c")
        prefix = "\n" if current.strip() else ""
        self.input_text.insert(tk.END, f"{prefix}Attached file: {attached_path}")
        self.input_text.focus_set()
        self._flash_status(f"Attached {attached_path.name}.")

    def _send_message(self) -> None:
        message = self.input_text.get("1.0", "end-1c").strip()
        if not message:
            self.input_text.focus_set()
            return

        try:
            copied_files = self._copy_attached_files()
            key, notice = append_user_message(self.chat_to_agent_file.get(), message)
        except (OSError, FileNotFoundError) as exc:
            messagebox.showerror("Send failed", f"Could not send message:\n\n{exc}")
            self._flash_status("Send failed.")
            return

        self.input_text.delete("1.0", tk.END)
        self._attached_files.clear()
        self._message_history.append((key, message))
        self._render_display()

        attachment_note = self._attachment_status(copied_files)
        if notice:
            self._flash_status(f"Sent as {key}. {attachment_note}{notice}", duration=7000)
        else:
            self._flash_status(f"Sent as {key}. {attachment_note}".strip())

    def _copy_attached_files(self) -> list[Path]:
        copied_files = []
        for attached_file in self._attached_files:
            copied_files.append(copy_attachment_to_downloads(str(attached_file), self.download_dir.get()))
        return copied_files

    def _attachment_status(self, copied_files: list[Path]) -> str:
        if not copied_files:
            return ""
        if len(copied_files) == 1:
            return f"Copied attachment to {copied_files[0].name}. "
        return f"Copied {len(copied_files)} attachments. "

    def _schedule_poll(self) -> None:
        self._poll_incoming_file()
        self.root.after(POLL_INTERVAL, self._schedule_poll)

    def _poll_incoming_file(self) -> None:
        path = Path(self.agent_to_chat_file.get()).expanduser()
        if not path.exists():
            self._incoming_stamp = None
            return

        try:
            stat = path.stat()
            stamp = (stat.st_mtime_ns, stat.st_size)
            if stamp == self._incoming_stamp:
                return

            self._incoming_stamp = stamp
            content = path.read_text(encoding="utf-8-sig").strip()
            if not content:
                return

            messages = self._messages_from_incoming(content)
            path.write_text("", encoding="utf-8")
            clear_stat = path.stat()
            self._incoming_stamp = (clear_stat.st_mtime_ns, clear_stat.st_size)

            if not messages:
                return

            self._message_history.extend(messages)

            self._render_display()
            count = len(messages)
            suffix = "" if count == 1 else "s"
            self._flash_status(f"Received {count} agent message{suffix}.")
        except OSError as exc:
            self._flash_status(f"Read error: {exc}")

    def _messages_from_incoming(self, content: str) -> list[tuple[str, str]]:
        parsed = self._parse_json_object(content)
        if parsed is None:
            return [(self._unique_history_key(AGENT_KEY_PREFIX), content)]

        messages = []
        used_keys = {key for key, _message in self._message_history}
        for raw_key, value in parsed.items():
            key = str(raw_key)
            if not key.startswith((USER_KEY_PREFIX, AGENT_KEY_PREFIX)):
                key = self._unique_history_key(AGENT_KEY_PREFIX, used_keys)
            else:
                key = self._avoid_history_key_collision(key, used_keys)
            used_keys.add(key)
            messages.append((key, self._stringify_message(value)))
        return messages

    def _unique_history_key(self, prefix: str, used_keys: set[str] | None = None) -> str:
        timestamp = int(time.time())
        existing_keys = used_keys if used_keys is not None else {key for key, _message in self._message_history}
        key = f"{prefix}{timestamp}"
        while key in existing_keys:
            timestamp += 1
            key = f"{prefix}{timestamp}"
        return key

    def _avoid_history_key_collision(self, key: str, used_keys: set[str] | None = None) -> str:
        existing_keys = used_keys if used_keys is not None else {existing for existing, _message in self._message_history}
        if key not in existing_keys:
            return key

        prefix = AGENT_KEY_PREFIX
        if key.startswith(USER_KEY_PREFIX):
            prefix = USER_KEY_PREFIX
        return self._unique_history_key(prefix, existing_keys)

    def _stringify_message(self, value) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, indent=2, ensure_ascii=False)

    def _render_display(self) -> None:
        self.display_text.config(state=tk.NORMAL)
        self.display_text.delete("1.0", tk.END)

        has_content = bool(self._message_history)
        for key, message in self._message_history:
            self._insert_message(key, message)

        if not has_content:
            self.display_text.insert(tk.END, "Waiting for agent messages.", "placeholder")

        self.display_text.config(state=tk.DISABLED)
        self.display_text.see(tk.END)

    def _parse_json_object(self, content: str) -> dict | None:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _insert_message(self, key: str, value) -> None:
        key = str(key)
        role, tag = self._role_for_key(key)
        timestamp = self._timestamp_for_key(key)
        header = f"{role}  {timestamp}" if timestamp else role
        body = self._stringify_message(value)

        self.display_text.insert(tk.END, header + "\n", tag)
        self.display_text.insert(tk.END, body.rstrip() + "\n\n", "message")

    def _role_for_key(self, key: str) -> tuple[str, str]:
        if key.startswith(USER_KEY_PREFIX):
            return self.user_name.get().strip() or "You", "role_user"
        if key.startswith(AGENT_KEY_PREFIX):
            return self.agent_name.get().strip() or "Agent", "role_agent"
        return key, "role_other"

    def _timestamp_for_key(self, key: str) -> str:
        for prefix in (USER_KEY_PREFIX, AGENT_KEY_PREFIX):
            if key.startswith(prefix):
                raw = key[len(prefix):]
                if raw.isdigit():
                    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(raw)))
        return ""

    def _flash_status(self, message: str, duration: int = 3000) -> None:
        self.status_var.set(message)
        self.root.after(duration, self._update_path_labels)


if __name__ == "__main__":
    root = tk.Tk()

    try:
        import ctypes

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            20,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        pass

    app = ChatApp(root)
    root.mainloop()
