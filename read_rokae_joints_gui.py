#!/usr/bin/env python3
"""Small GUI wrapper for reading ROKAE joint angles."""

from __future__ import annotations

import subprocess
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk


ROOT = Path(__file__).resolve().parent
PYTHON = "/home/mars/miniforge3/envs/lerobot/bin/python"
READER = ROOT / "read_rokae_joints.py"


class JointReaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ROKAE Joint Reader")
        self.geometry("880x700")
        self.minsize(760, 520)

        style = ttk.Style(self)
        style.theme_use("clam")
        self.default_font = tkfont.Font(family="DejaVu Sans", size=10)
        self.mono_font = tkfont.Font(family="DejaVu Sans Mono", size=11)
        self.option_add("*Font", self.default_font)
        style.configure("TFrame", background="#f4f6f8")
        style.configure("TLabel", background="#f4f6f8", foreground="#1f2933")
        style.configure("TButton", padding=(10, 5))
        style.configure("TCombobox", padding=(4, 3))

        self.target = tk.StringVar(value="all")
        self.status = tk.StringVar(value="Ready")
        self.interval_s = tk.StringVar(value="1.0")
        self.live_enabled = False
        self.live_after_id: str | None = None
        self.reading = False
        self.last_output = ""

        toolbar = ttk.Frame(self, padding=(12, 10))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="Target").pack(side=tk.LEFT)
        target_box = ttk.Combobox(
            toolbar,
            textvariable=self.target,
            values=("all", "right_arm", "left_arm", "taihu"),
            width=14,
            state="readonly",
        )
        target_box.pack(side=tk.LEFT, padx=(8, 14))

        self.read_button = ttk.Button(toolbar, text="Read Joints", command=self.read_joints)
        self.read_button.pack(side=tk.LEFT)

        self.live_button = ttk.Button(toolbar, text="Start Live", command=self.toggle_live)
        self.live_button.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(toolbar, text="Interval").pack(side=tk.LEFT, padx=(14, 4))
        interval_box = ttk.Combobox(
            toolbar,
            textvariable=self.interval_s,
            values=("0.5", "1.0", "2.0", "5.0"),
            width=6,
            state="readonly",
        )
        interval_box.pack(side=tk.LEFT)
        ttk.Label(toolbar, text="s").pack(side=tk.LEFT, padx=(3, 0))

        ttk.Button(toolbar, text="Clear", command=self.clear_output).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(toolbar, textvariable=self.status).pack(side=tk.RIGHT)

        text_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.output = tk.Text(
            text_frame,
            wrap=tk.NONE,
            font=self.mono_font,
            background="#ffffff",
            foreground="#111827",
            insertbackground="#111827",
            relief=tk.FLAT,
            borderwidth=0,
            padx=12,
            pady=10,
        )
        yscroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.output.yview)
        xscroll = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.output.xview)
        self.output.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.output.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

    def clear_output(self) -> None:
        self.output.delete("1.0", tk.END)
        self.last_output = ""
        self.status.set("Ready")

    def replace_output(self, text: str) -> None:
        if text == self.last_output:
            return

        yview = self.output.yview()
        xview = self.output.xview()
        self.output.configure(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.insert("1.0", text)
        self.output.configure(state=tk.DISABLED)

        if yview:
            self.output.yview_moveto(yview[0])
        if xview:
            self.output.xview_moveto(xview[0])
        self.last_output = text

    def read_joints(self) -> None:
        if self.reading:
            return
        self.reading = True
        self.read_button.configure(state=tk.DISABLED)
        self.live_button.configure(state=tk.DISABLED)
        self.status.set("Reading...")
        if not self.live_enabled:
            self.clear_output()

        thread = threading.Thread(target=self._read_worker, daemon=True)
        thread.start()

    def toggle_live(self) -> None:
        if self.live_enabled:
            self.stop_live()
        else:
            self.start_live()

    def start_live(self) -> None:
        self.live_enabled = True
        self.live_button.configure(text="Stop Live")
        self.read_joints()

    def stop_live(self) -> None:
        self.live_enabled = False
        self.live_button.configure(text="Start Live")
        if self.live_after_id is not None:
            self.after_cancel(self.live_after_id)
            self.live_after_id = None
        self.status.set("Stopped")

    def schedule_live_read(self) -> None:
        if not self.live_enabled:
            return
        try:
            interval_ms = max(250, int(float(self.interval_s.get()) * 1000))
        except ValueError:
            interval_ms = 1000
        self.live_after_id = self.after(interval_ms, self.read_joints)

    def _read_worker(self) -> None:
        cmd = [PYTHON, str(READER), "--target", self.target.get()]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=15,
                check=False,
            )
            output = proc.stdout or ""
            if proc.returncode != 0:
                output += f"\nExit code: {proc.returncode}\n"
            self.after(0, self.replace_output, output)
            self.after(0, self.status.set, "Done" if proc.returncode == 0 else "Finished with errors")
        except subprocess.TimeoutExpired:
            self.after(0, self.replace_output, "Timed out after 15 seconds.\n")
            self.after(0, self.status.set, "Timed out")
        except Exception as exc:
            self.after(0, self.replace_output, f"ERROR: {exc}\n")
            self.after(0, self.status.set, "Error")
        finally:
            self.reading = False
            self.after(0, self.read_button.configure, {"state": tk.NORMAL})
            self.after(0, self.live_button.configure, {"state": tk.NORMAL})
            self.after(0, self.schedule_live_read)


if __name__ == "__main__":
    JointReaderApp().mainloop()
