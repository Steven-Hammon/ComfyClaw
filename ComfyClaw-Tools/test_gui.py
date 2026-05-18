from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext


ROOT = Path(__file__).resolve().parent
RUN_TOOL = ROOT / "run_tool.py"


class ToolTestGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Tools1 Interactive Test GUI")
        self.root.geometry("900x650")

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()

        self.input_label = tk.Label(root, text="JSON tool call")
        self.input_label.pack(anchor="w", padx=10, pady=(10, 2))

        self.input_text = scrolledtext.ScrolledText(root, height=12, wrap=tk.WORD)
        self.input_text.pack(fill=tk.BOTH, expand=False, padx=10)
        self.input_text.insert(
            "1.0",
            '{"tool":"FILE_WRITE-APPEND","args":{"path":"C:\\\\Claw\\\\Workspace\\\\ToDo_List.md","content":"\\n## Tool & Environment Audit\\n- Objective: etc"}}',
        )

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, padx=10, pady=8)

        self.send_button = tk.Button(self.button_frame, text="Send", command=self.send_tool_call)
        self.send_button.pack(side=tk.LEFT)

        self.restart_button = tk.Button(self.button_frame, text="Restart Process", command=self.restart_process)
        self.restart_button.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="Starting run_tool.py --interactive...")
        self.status_label = tk.Label(self.button_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=(12, 0))

        self.output_label = tk.Label(root, text="Tool output")
        self.output_label.pack(anchor="w", padx=10, pady=(6, 2))

        self.output_text = scrolledtext.ScrolledText(root, height=18, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.start_process()
        self.root.after(100, self.drain_output_queue)

    def start_process(self) -> None:
        if self.process and self.process.poll() is None:
            return

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(RUN_TOOL), "--interactive"],
                cwd=str(ROOT),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except Exception as exc:
            self.status_var.set("Failed to start process")
            messagebox.showerror("Start failed", str(exc))
            return

        threading.Thread(target=self.read_stdout, daemon=True).start()
        threading.Thread(target=self.read_stderr, daemon=True).start()
        self.status_var.set("Ready")

    def restart_process(self) -> None:
        self.stop_process()
        self.start_process()
        self.append_output("\n[GUI] Restarted run_tool.py --interactive\n")

    def stop_process(self) -> None:
        if not self.process:
            return

        if self.process.poll() is None:
            try:
                if self.process.stdin:
                    self.process.stdin.close()
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                self.process.kill()

        self.process = None

    def read_stdout(self) -> None:
        if not self.process or not self.process.stdout:
            return

        while True:
            chunk = self.process.stdout.read(1)
            if chunk == "":
                break
            self.output_queue.put(chunk)

    def read_stderr(self) -> None:
        if not self.process or not self.process.stderr:
            return

        for line in self.process.stderr:
            self.output_queue.put(f"\n[stderr] {line}")

    def drain_output_queue(self) -> None:
        parts: list[str] = []
        while True:
            try:
                parts.append(self.output_queue.get_nowait())
            except queue.Empty:
                break

        if parts:
            self.append_output("".join(parts))

        if self.process and self.process.poll() is not None:
            self.status_var.set(f"Process exited: {self.process.returncode}")

        self.root.after(100, self.drain_output_queue)

    def append_output(self, text: str) -> None:
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

    def send_tool_call(self) -> None:
        self.start_process()
        if not self.process or not self.process.stdin or self.process.poll() is not None:
            messagebox.showerror("Not running", "run_tool.py --interactive is not running.")
            return

        payload = self.input_text.get("1.0", tk.END).strip()
        if not payload:
            messagebox.showwarning("Empty input", "Paste a JSON tool call first.")
            return

        try:
            self.process.stdin.write(payload + "\n")
            self.process.stdin.flush()
        except Exception as exc:
            self.status_var.set("Send failed")
            messagebox.showerror("Send failed", str(exc))
            return

        self.append_output("\n[GUI] Sent JSON tool call\n")

    def close(self) -> None:
        self.stop_process()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ToolTestGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
