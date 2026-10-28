# My app module for this compiler project.
"""MY C COMPILER - a desktop workspace for the C-written custom frontend."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, font, messagebox, simpledialog, ttk

from backend import BuildError, CompilerBackend


ROOT = Path(__file__).resolve().parents[1]
BG = "#10141f"
PANEL = "#181f2e"
EDITOR = "#111824"
EDGE = "#2a3447"
TEXT = "#e4eaf5"
MUTED = "#95a4bd"
ACCENT = "#76e0be"
BLUE = "#88b8ff"
AMBER = "#ffce80"
RED = "#ff8d9b"
DEFAULT_PAIRS = [
    ("printf", "output"), ("scanf", "input"), ("for", "each"),
    ("if", "when"), ("else", "given"), ("while", "until"),
    ("do", "execute"), ("switch", "choose"), ("case", "match"),
    ("default", "otherwise"), ("break", "snap"), ("continue", "so_on"),
    ("return", "provide"),
]


def settings_path():
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".config"))
    return base / "MY_C_COMPILER" / "settings.json"


class CodePane(tk.Frame):
    def __init__(self, parent, mono, on_change=None, readonly=False):
        super().__init__(parent, bg=EDITOR)
        self.on_change = on_change
        self.readonly = readonly
        self.pending = None
        self.aliases = {alias for _, alias in DEFAULT_PAIRS}
        self.gutter = tk.Canvas(self, width=52, bg=EDITOR, highlightthickness=0)
        self.gutter.grid(row=0, column=0, sticky="ns")
        self.text = tk.Text(
            self, bg=EDITOR, fg=TEXT, insertbackground=ACCENT,
            selectbackground="#334763", relief="flat", borderwidth=0,
            font=mono, padx=12, pady=14, undo=True, wrap="none",
            tabs=("4c",), spacing1=2, spacing3=2,
        )
        self.text.grid(row=0, column=1, sticky="nsew")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self._scroll)
        scroll.grid(row=0, column=2, sticky="ns")
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        horizontal.grid(row=1, column=1, sticky="ew")
        self.text.configure(
            yscrollcommand=lambda first, last: (scroll.set(first, last), self.redraw()),
            xscrollcommand=horizontal.set,
        )
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.text.bind("<<Modified>>", self._modified)
        self.text.bind("<Configure>", lambda event: self.redraw())
        self.text.bind("<Tab>", self._tab)
        self.text.tag_configure("comment", foreground="#71859c")
        self.text.tag_configure("string", foreground="#e9c48c")
        self.text.tag_configure("number", foreground="#c9adff")
        self.text.tag_configure("keyword", foreground=BLUE)
        self.text.tag_configure("function", foreground=ACCENT)
        self.text.tag_configure("error_line", background="#492a35")
        self.text.tag_configure("error_token", background="#8e3548", underline=True)
        if readonly:
            self.text.configure(state="disabled")

    def _scroll(self, *args):
        self.text.yview(*args)
        self.redraw()

    def _tab(self, event):
        if not self.readonly:
            self.text.insert("insert", "    ")
        return "break"

    def _modified(self, event=None):
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.text.tag_remove("error_line", "1.0", "end")
        self.text.tag_remove("error_token", "1.0", "end")
        if self.on_change:
            self.on_change()
        if self.pending:
            self.after_cancel(self.pending)
        self.pending = self.after(160, self.highlight)
        self.redraw()

    def get(self):
        return self.text.get("1.0", "end-1c")

    def set(self, content):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.edit_modified(False)
        if self.readonly:
            self.text.configure(state="disabled")
        self.highlight()
        self.after_idle(self.redraw)

    def highlight(self):
        self.pending = None
        source = self.get()
        for tag in ("comment", "string", "number", "keyword", "function"):
            self.text.tag_remove(tag, "1.0", "end")
        if len(source) > 200_000:
            return
        keywords = {"int", "void", "char", "float", "double", "long", "short",
                    "const", "unsigned", "signed", "return", "break", "continue",
                    "if", "else", "for", "while", "do", "switch", "case", "default",
                    "struct", "enum", "typedef", "sizeof"} | self.aliases
        pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\b[A-Za-z_]\w*\b|\b\d+(?:\.\d+)?\b'
        for match in re.finditer(pattern, source):
            token = match.group()
            if token.startswith(("//", "/*")):
                tag = "comment"
            elif token.startswith(('"', "'")):
                tag = "string"
            elif token[0].isdigit():
                tag = "number"
            elif token in ("output", "input", "printf", "scanf"):
                tag = "function"
            elif token in keywords:
                tag = "keyword"
            else:
                continue
            self.text.tag_add(tag, f"1.0+{match.start()}c", f"1.0+{match.end()}c")

    def redraw(self):
        self.gutter.delete("all")
        index = self.text.index("@0,0")
        while True:
            info = self.text.dlineinfo(index)
            if info is None:
                break
            line = index.split(".")[0]
            self.gutter.create_text(40, info[1] + 2, anchor="ne", text=line,
                                    font=self.text.cget("font"), fill="#5f718d")
            index = self.text.index(f"{index}+1line")


class CompilerApp:
    def __init__(self, root: tk.Tk, project=ROOT):
        self.root = root
        self.project = Path(project).resolve()
        self.events = queue.Queue()
        gcc = ""
        try:
            saved = json.loads(settings_path().read_text(encoding="utf-8"))
            gcc = saved.get("gcc", "") if isinstance(saved, dict) else ""
            if not isinstance(gcc, str):
                gcc = ""
            if not Path(gcc).is_file():
                gcc = ""
        except (OSError, ValueError, TypeError):
            pass
        self.backend = CompilerBackend(
            self.project, lambda kind, value: self.events.put((kind, value)), gcc)
        self.worker = None
        self.last_build = None
        self.built_signature = ""
        self.current_file = None
        self.include_folder = self.project
        self.document_name = "hello.myc"
        self.dirty = False
        self.config_dirty = False
        self.running = False
        self.closing = False
        self._close_started = 0
        self.root.title("MY C COMPILER")
        self.root.geometry("1240x900")
        self.root.minsize(990, 720)
        self.root.configure(bg=BG)
        self._style()
        self._layout()
        self.config.set((self.project / "custom-keywords" / "keywords.cfg").read_text("utf-8"))
        self._load_example("Hello world", confirm=False)
        self._refresh_vocabulary()
        self._compiler_label()
        self._set_busy(False)
        self._append(self.console, "Ready. Write your code, then click Run.\n", "hint")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Control-s>", lambda event: self.save_source())
        self.root.bind("<Control-o>", lambda event: self.open_source())
        self.root.bind("<Control-n>", lambda event: self.new_source())
        self.root.bind("<Control-g>", lambda event: self.go_to_line())
        self.root.bind("<F5>", lambda event: self.start_job("run"))
        self.root.after(40, self._poll)

    def _style(self):
        families = set(font.families(self.root))
        self.sans = next((x for x in ("Segoe UI", "DejaVu Sans") if x in families), "Arial")
        self.mono = next((x for x in ("Cascadia Code", "Consolas", "DejaVu Sans Mono")
                          if x in families), "Courier")
        self.root.option_add("*Font", (self.sans, 10))
        self.root.option_add("*Listbox.background", PANEL)
        self.root.option_add("*Listbox.foreground", TEXT)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                        padding=(17, 10), font=(self.sans, 10))
        style.map("TNotebook.Tab", background=[("selected", EDITOR)],
                  foreground=[("selected", TEXT)])
        style.configure("Vertical.TScrollbar", background=EDGE, troughcolor=EDITOR,
                        borderwidth=0, arrowcolor=MUTED)
        style.configure("Horizontal.TScrollbar", background=EDGE, troughcolor=EDITOR,
                        borderwidth=0, arrowcolor=MUTED)
        style.configure("TCombobox", fieldbackground=EDITOR, background=EDGE,
                        foreground=TEXT, arrowcolor=TEXT, borderwidth=0, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", EDITOR)],
                  foreground=[("readonly", TEXT)])
        style.configure("Treeview", background=EDITOR, fieldbackground=EDITOR,
                        foreground=TEXT, borderwidth=0, rowheight=23)
        style.configure("Treeview.Heading", background=PANEL, foreground=MUTED,
                        relief="flat", font=(self.sans, 9, "bold"))

    def label(self, parent, text, color=TEXT, size=10, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=(self.sans, size, "bold" if bold else "normal"), **kwargs)

    def button(self, parent, title, command, primary=False):
        return tk.Button(
            parent, text=title, command=command, bg=ACCENT if primary else EDGE,
            fg="#10251e" if primary else TEXT, activebackground="#a2efd6" if primary else "#35445e",
            activeforeground="#10251e" if primary else TEXT, disabledforeground="#67758c",
            relief="flat", borderwidth=0, padx=15, pady=8, cursor="hand2",
            font=(self.sans, 10, "bold" if primary else "normal"),
        )

    def _layout(self):
        header = tk.Frame(self.root, bg=BG, padx=24, pady=17)
        header.grid(row=0, column=0, sticky="ew")
        self.label(header, "{ C }", ACCENT, 20, True).pack(side="left", padx=(0, 15))
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left")
        self.label(titles, "MY C COMPILER", size=16, bold=True).pack(anchor="w")
        self.label(titles, "Custom keyword workspace", MUTED, 10).pack(anchor="w", pady=(3, 0))
        self.gcc_label = self.label(header, "", ACCENT, 10)
        self.gcc_label.pack(side="right")
        self.button(header, "Language help", self.language_help).pack(side="right", padx=4)
        self.button(header, "Choose GCC", self.choose_gcc).pack(side="right", padx=14)

        toolbar = tk.Frame(self.root, bg=PANEL, padx=18, pady=9)
        toolbar.grid(row=1, column=0, sticky="ew", padx=16)
        for title, action in (("New", self.new_source), ("Open", self.open_source),
                              ("Save", self.save_source)):
            self.button(toolbar, title, action).pack(side="left", padx=(0, 6))
        self.button(toolbar, "Save keywords", self.save_config).pack(side="left", padx=(3, 6))
        self.export_button = self.button(toolbar, "Export program", self.export_program)
        self.export_button.pack(side="left", padx=3)
        self.stop_button = self.button(toolbar, "Stop", self.stop)
        self.stop_button.pack(side="right", padx=(7, 0))
        self.run_button = self.button(toolbar, "Run  F5", lambda: self.start_job("run"), True)
        self.run_button.pack(side="right", padx=(7, 0))
        self.compile_button = self.button(toolbar, "Compile", lambda: self.start_job("compile"))
        self.compile_button.pack(side="right", padx=(7, 0))
        self.translate_button = self.button(toolbar, "Translate", lambda: self.start_job("translate"))
        self.translate_button.pack(side="right")

        vertical = tk.PanedWindow(self.root, orient="vertical", bg=BG, sashwidth=9,
                                  borderwidth=0, showhandle=False)
        vertical.grid(row=2, column=0, sticky="nsew", padx=16, pady=(10, 0))
        middle = tk.PanedWindow(vertical, orient="horizontal", bg=BG, sashwidth=12,
                               borderwidth=0, showhandle=False)
        vertical.add(middle, minsize=350, stretch="always")
        self.editor_tabs = ttk.Notebook(middle)
        self.source = CodePane(self.editor_tabs, (self.mono, 11), self._source_changed)
        self.generated = CodePane(self.editor_tabs, (self.mono, 11), readonly=True)
        self.config = CodePane(self.editor_tabs, (self.mono, 10), self._config_changed)
        self.editor_tabs.add(self.source, text="Source")
        self.editor_tabs.add(self.generated, text="Generated C")
        self.editor_tabs.add(self.config, text="Keywords")
        middle.add(self.editor_tabs, minsize=580, stretch="always")

        sidebar = tk.Frame(middle, bg=PANEL, padx=16, pady=14)
        middle.add(sidebar, minsize=280, width=290, stretch="never")
        self.label(sidebar, "EXAMPLES", MUTED, 9, True).pack(anchor="w")
        self.example_choice = ttk.Combobox(
            sidebar, state="readonly",
            values=("Hello world", "All keywords", "Number guessing", "Star pattern"),
        )
        self.example_choice.set("Hello world")
        self.example_choice.pack(fill="x", pady=(8, 16))
        self.example_choice.bind("<<ComboboxSelected>>",
                                 lambda event: self._load_example(self.example_choice.get()))
        self.tools_tabs = ttk.Notebook(sidebar)
        self.tools_tabs.pack(fill="both", expand=True)
        input_tools = tk.Frame(self.tools_tabs, bg=PANEL, padx=2, pady=12)
        language_tools = tk.Frame(self.tools_tabs, bg=PANEL, padx=2, pady=12)
        self.tools_tabs.add(input_tools, text="Program input")
        self.tools_tabs.add(language_tools, text="Language")
        self.label(input_tools, "PRELOAD INPUT", MUTED, 9, True).pack(anchor="w")
        self.input_text = tk.Text(
            input_tools, height=6, bg=EDITOR, fg=TEXT, insertbackground=ACCENT,
            font=(self.mono, 10), relief="flat", padx=10, pady=8, wrap="word",
        )
        self.input_text.pack(fill="x", pady=(8, 5))
        self.label(input_tools, "Optional: sent when Run starts.\nYou can also type below the console.",
                   MUTED, 9, justify="left").pack(anchor="w")
        limit_row = tk.Frame(input_tools, bg=PANEL)
        limit_row.pack(fill="x", pady=(12, 14))
        self.label(limit_row, "Run limit", MUTED, 9).pack(side="left")
        self.time_limit = ttk.Combobox(limit_row, width=5, state="readonly",
                                       values=("10", "30", "60", "120", "300"))
        self.time_limit.set("30")
        self.time_limit.pack(side="left", padx=8)
        self.label(limit_row, "seconds", MUTED, 9).pack(side="left")
        self.label(input_tools, "LIVE INPUT", MUTED, 9, True).pack(anchor="w", pady=(6, 6))
        self.label(input_tools,
                   "Run your program, type a value in the\nstdin box, then press Enter or Send.\n\n"
                   "Send EOF closes input.\nStop ends a running program.",
                   MUTED, 9, justify="left").pack(anchor="w")
        self.label(language_tools, "until repeats while its condition is true.",
                   MUTED, 8, wraplength=250, justify="left").pack(
                       side="bottom", anchor="w", pady=(9, 0))
        table = tk.Frame(language_tools, bg=PANEL)
        table.pack(fill="both", expand=True)
        self.vocabulary = ttk.Treeview(table, columns=("standard", "custom"),
                                       show="headings", height=10, selectmode="none")
        self.vocabulary.heading("standard", text="STANDARD C")
        self.vocabulary.heading("custom", text="YOUR NAME")
        self.vocabulary.column("standard", width=105, minwidth=75)
        self.vocabulary.column("custom", width=115, minwidth=80)
        self.vocabulary.pack(side="left", fill="both", expand=True)
        vocabulary_scroll = ttk.Scrollbar(table, orient="vertical",
                                         command=self.vocabulary.yview)
        vocabulary_scroll.pack(side="right", fill="y")
        self.vocabulary.configure(yscrollcommand=vocabulary_scroll.set)

        bottom = tk.Frame(vertical, bg=PANEL, padx=12, pady=10)
        vertical.add(bottom, minsize=190, height=245, stretch="never")
        bottom.rowconfigure(0, weight=1)
        bottom.columnconfigure(0, weight=1)
        self.output_tabs = ttk.Notebook(bottom)
        self.output_tabs.grid(row=0, column=0, sticky="nsew")
        self.console = self._output_box("Console")
        self.log = self._output_box("Build log")
        problems_frame = tk.Frame(self.output_tabs, bg=EDITOR)
        self.problems = ttk.Treeview(problems_frame, columns=("level", "line", "column", "message"),
                                    show="headings", selectmode="browse")
        for name, width in (("level", 75), ("line", 50), ("column", 60), ("message", 750)):
            self.problems.heading(name, text=name.title())
            self.problems.column(name, width=width, stretch=name == "message")
        self.problems.pack(fill="both", expand=True, side="left")
        problem_scroll = ttk.Scrollbar(problems_frame, command=self.problems.yview)
        problem_scroll.pack(side="right", fill="y")
        self.problems.configure(yscrollcommand=problem_scroll.set)
        self.problem_records = {}
        self.problems.bind("<Double-1>", self.go_to_problem)
        self.problems.bind("<Return>", self.go_to_problem)
        self.output_tabs.add(problems_frame, text="Problems (double-click to jump)")
        input_row = tk.Frame(bottom, bg=PANEL)
        input_row.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.label(input_row, "stdin", ACCENT, 10, True).pack(side="left", padx=(0, 12))
        self.live_input = tk.Entry(input_row, bg=EDITOR, fg=TEXT, insertbackground=ACCENT,
                                   disabledbackground=EDITOR, disabledforeground=MUTED,
                                   relief="flat", font=(self.mono, 11))
        self.live_input.pack(side="left", fill="x", expand=True, ipady=8)
        self.live_input.bind("<Return>", lambda event: self.send_input())
        self.send_button = self.button(input_row, "Send", self.send_input)
        self.send_button.pack(side="left", padx=8)
        self.eof_button = self.button(input_row, "Send EOF", self.send_eof)
        self.eof_button.pack(side="left")
        footer = tk.Frame(self.root, bg=BG, padx=20, pady=9)
        footer.grid(row=3, column=0, sticky="ew")
        self.status = self.label(footer, "Ready", ACCENT, 10)
        self.status.pack(side="left")
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=110)
        self.progress.pack(side="left", padx=12)
        self.button(footer, "Go to line", self.go_to_line).pack(side="left", padx=5)
        self.file_status = self.label(footer, "UTF-8  |  Custom C", MUTED, 9)
        self.file_status.pack(side="right")
        self.root.rowconfigure(2, weight=1)
        self.root.columnconfigure(0, weight=1)

    def _output_box(self, title):
        frame = tk.Frame(self.output_tabs, bg=EDITOR)
        text = tk.Text(frame, bg=EDITOR, fg=TEXT, font=(self.mono, 10),
                       relief="flat", borderwidth=0, padx=12, pady=10, wrap="word",
                       state="disabled", height=7, selectbackground="#334763")
        text.pack(side="left", expand=True, fill="both")
        scroll = ttk.Scrollbar(frame, command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)
        for tag, color in (("hint", MUTED), ("success", ACCENT), ("error", RED), ("input", BLUE)):
            text.tag_configure(tag, foreground=color)
        self.output_tabs.add(frame, text=title)
        return text

    @staticmethod
    def _append(widget, text, tag=None):
        widget.configure(state="normal")
        widget.insert("end", str(text), tag or ())
        widget.see("end")
        widget.configure(state="disabled")

    @staticmethod
    def _clear(widget):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")

    def _signature(self):
        return hashlib.sha256((self.source.get() + "\x00" + self.config.get()).encode()).hexdigest()

    def _source_changed(self):
        self.dirty = True
        self._title()
        self.export_button.configure(state="disabled")

    def _config_changed(self):
        self.config_dirty = True
        self.editor_tabs.tab(2, text="Keywords *")
        self._refresh_vocabulary()
        self.export_button.configure(state="disabled")

    def _refresh_vocabulary(self):
        pairs = []
        for line in self.config.get().splitlines():
            match = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)", line)
            if match:
                pairs.append(match.groups())
        self.source.aliases = {custom for _, custom in pairs}
        self.source.highlight()
        for row in self.vocabulary.get_children():
            self.vocabulary.delete(row)
        for standard, alias in pairs:
            self.vocabulary.insert("", "end", values=(standard, alias))

    def _title(self):
        marker = " *" if self.dirty else ""
        self.root.title(f"{self.document_name}{marker} - MY C COMPILER")
        self.editor_tabs.tab(0, text=self.document_name + marker)
        lines = self.source.get().count("\n") + 1
        self.file_status.configure(text=f"{lines} lines  |  UTF-8  |  Custom C")

    def _confirm_source(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel("Save source?", "Save your source changes first?",
                                           parent=self.root)
        if answer is None:
            return False
        return self.save_source() if answer else True

    def _load_example(self, name, confirm=True):
        if confirm and not self._confirm_source():
            return
        files = {"Hello world": "hello.myc", "All keywords": "all_features.myc",
                 "Number guessing": "number_guessing.myc", "Star pattern": "star_pattern.myc"}
        path = self.project / "custom-keywords" / "examples" / files[name]
        self.source.set(path.read_text(encoding="utf-8"))
        self.example_choice.set(name)
        self.document_name = path.name
        self.current_file = None
        self.include_folder = path.parent
        self.dirty = False
        self._title()
        self.editor_tabs.select(0)
        self.last_build = None
        if hasattr(self, "input_text"):
            self.input_text.delete("1.0", "end")
            if name in ("All keywords", "Star pattern"):
                self.input_text.insert("1.0", "1" if name == "All keywords" else "5")
        self.export_button.configure(state="disabled")

    def new_source(self):
        if not self._confirm_source():
            return
        self.source.set('#include <stdio.h>\n\nint main(void) {\n    output("Hello!\\n");\n    provide 0;\n}\n')
        self.document_name = "untitled.myc"
        self.current_file = None
        self.include_folder = self.project
        self.dirty = True
        self._title()
        self.editor_tabs.select(0)
        self.export_button.configure(state="disabled")

    def open_source(self):
        if not self._confirm_source():
            return
        filename = filedialog.askopenfilename(parent=self.root, title="Open source",
                                              filetypes=[("C-like source", "*.myc *.c"),
                                                         ("All files", "*.*")])
        if filename:
            try:
                path = Path(filename)
                source = path.read_text(encoding="utf-8-sig")
                if len(source.encode("utf-8")) > 1024 * 1024:
                    raise ValueError("Source is larger than the 1 MiB input limit.")
                self.source.set(source)
                self.current_file = path
                self.include_folder = path.parent
                self.document_name = path.name
                self.dirty = False
                self._title()
                self.editor_tabs.select(0)
                self.export_button.configure(state="disabled")
            except (OSError, UnicodeError, ValueError) as error:
                messagebox.showerror("Could not open source", str(error), parent=self.root)

    def save_source(self):
        filename = self.current_file
        if filename is None:
            selected = filedialog.asksaveasfilename(
                parent=self.root, title="Save source", initialfile=self.document_name,
                defaultextension=".myc", filetypes=[("Custom C source", "*.myc"),
                                                   ("C source", "*.c")])
            if not selected:
                return False
            filename = Path(selected)
        try:
            filename.write_text(self.source.get(), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Could not save", str(error), parent=self.root)
            return False
        self.current_file = filename
        self.include_folder = filename.parent
        self.document_name = filename.name
        self.dirty = False
        self._title()
        self.status.configure(text="Source saved", fg=ACCENT)
        return True

    def save_config(self):
        try:
            path = self.project / "custom-keywords" / "keywords.cfg"
            path.write_text(self.config.get(), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Could not save keywords", str(error), parent=self.root)
            return False
        self.config_dirty = False
        self.editor_tabs.tab(2, text="Keywords")
        self.status.configure(text="Keywords saved; next build uses these names", fg=ACCENT)
        return True

    def _compiler_label(self):
        self.gcc_label.configure(text="GCC ready" if self.backend.gcc else "GCC not selected",
                                 fg=ACCENT if self.backend.gcc else AMBER)

    def choose_gcc(self):
        if self.worker and self.worker.is_alive():
            return
        filename = filedialog.askopenfilename(parent=self.root, title="Select GCC executable",
                                              filetypes=[("GCC", "gcc.exe gcc *gcc*"),
                                                         ("All files", "*.*")])
        if filename:
            self.backend.gcc = filename
            self._compiler_label()
            try:
                path = settings_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"gcc": filename}), encoding="utf-8")
            except OSError:
                pass

    def _set_busy(self, busy):
        self.progress.start(12) if busy else self.progress.stop()
        for button in (self.run_button, self.compile_button, self.translate_button):
            button.configure(state="disabled" if busy else "normal")
        self.stop_button.configure(state="normal" if busy else "disabled")
        for widget in (self.live_input, self.send_button, self.eof_button):
            widget.configure(state="normal" if self.running else "disabled")
        usable = bool(not busy and self.last_build and self.last_build.executable
                      and self.built_signature == self._signature())
        self.export_button.configure(state="normal" if usable else "disabled")

    def start_job(self, action):
        if self.worker and self.worker.is_alive():
            return
        source, config = self.source.get(), self.config.get()
        initial = self.input_text.get("1.0", "end-1c")
        if len(initial.encode()) > 65536:
            messagebox.showerror("Input is too large", "Use at most 64 KiB of preloaded input.",
                                 parent=self.root)
            return
        signature = self._signature()
        source_folder = self.include_folder
        timeout = int(self.time_limit.get())
        self.backend.reset()
        self.backend.cleanup()
        self.last_build = None
        self.running = False
        self._clear(self.console)
        self._clear(self.log)
        self.problems.delete(*self.problems.get_children())
        self.problem_records.clear()
        self.source.text.tag_remove("error_line", "1.0", "end")
        self.source.text.tag_remove("error_token", "1.0", "end")
        self.config.text.tag_remove("error_line", "1.0", "end")
        self.config.text.tag_remove("error_token", "1.0", "end")
        self.generated.set("")
        self.status.configure(text="Starting...", fg=BLUE)
        self._set_busy(True)
        self.output_tabs.select(1 if action != "run" else 0)

        def work():
            try:
                result = self.backend.build(source, config, source_folder,
                                            translate_only=action == "translate")
                self.events.put(("built", (result, signature)))
                if action == "run":
                    outcome = self.backend.run(result, initial, timeout)
                    self.events.put(("finished", outcome))
                else:
                    self.events.put(("complete", action))
            except (BuildError, OSError, ValueError) as error:
                self.events.put(("error", str(error)))
            finally:
                self.events.put(("idle", None))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _poll(self):
        if self.closing:
            return
        for _ in range(256):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "diagnostic":
                item = self.problems.insert("", "end", values=(value["severity"], value["line"],
                                                             value["column"], value["message"]))
                self.problem_records[item] = value
                pane = self.config if value.get("target") == "config" else self.source
                if value["source"] == pane.get() and "error" in value["severity"]:
                    row, col = value["line"], value["column"]
                    pane.text.tag_add("error_line", f"{row}.0", f"{row}.end")
                    pane.text.tag_add("error_token", f"{row}.{col-1}", f"{row}.{col}")
            elif kind == "log":
                self._append(self.log, value)
            elif kind == "output":
                self._append(self.console, value)
            elif kind == "status":
                self.status.configure(text=value, fg=BLUE)
            elif kind == "generated":
                self.generated.set(value)
            elif kind == "built":
                self.last_build, self.built_signature = value
            elif kind == "running":
                self.running = True
                self.status.configure(text="Running | input is open", fg=ACCENT)
                self._set_busy(True)
                self.live_input.focus_set()
            elif kind == "finished":
                note = (f"\n\nProcess exited with code {value.returncode}"
                        f"  |  {value.elapsed:.2f}s")
                if value.reason != "completed":
                    note += "  |  " + value.reason
                note += "\n"
                tag = "success" if value.returncode == 0 else "error"
                self._append(self.console, note, tag)
                self.status.configure(
                    text="Finished" if value.reason == "completed" else "Stopped: " + value.reason,
                    fg=ACCENT if value.returncode == 0 else AMBER)
            elif kind == "complete":
                text = "Translation complete - see Generated C" if value == "translate" else "Build successful"
                self.status.configure(text=text, fg=ACCENT)
                if value == "translate":
                    self.editor_tabs.select(1)
            elif kind == "error":
                self._append(self.log, "\n" + value + "\n", "error")
                self._append(self.console, value + "\n", "error")
                self.output_tabs.select(1)
                self.status.configure(text="Stopped" if self.backend.cancelled.is_set()
                                      else "Build failed - see Build log", fg=RED)
            elif kind == "idle":
                self.running = False
                self._set_busy(False)
            elif kind == "input_closed":
                self._append(self.console, "\n[stdin closed]\n", "hint")
            elif kind == "input_error":
                self._append(self.console, "\nInput could not be sent: process ended or stdin is closed.\n",
                             "hint")
        self.root.after(40, self._poll)

    def send_input(self):
        if not self.running:
            return
        text = self.live_input.get()
        self.live_input.delete(0, "end")
        self._append(self.console, "> " + text + "\n", "input")
        def send():
            if not self.backend.send_input(text + "\n"):
                self.events.put(("input_error", None))
        threading.Thread(target=send, daemon=True).start()

    def send_eof(self):
        if self.running:
            def close_input():
                self.backend.close_input()
                self.events.put(("input_closed", None))
            threading.Thread(target=close_input, daemon=True).start()

    def stop(self):
        self.backend.cancel()
        self.status.configure(text="Stopping...", fg=AMBER)

    def go_to_line(self):
        count = self.source.get().count("\n") + 1
        line = simpledialog.askinteger("Go to line", f"Line number (1–{count})",
                                       parent=self.root, minvalue=1, maxvalue=count)
        if line:
            self.editor_tabs.select(0)
            self.source.text.mark_set("insert", f"{line}.0")
            self.source.text.see(f"{line}.0")
            self.source.text.focus_set()

    def go_to_problem(self, event=None):
        selected = self.problems.selection()
        if not selected:
            return
        problem = self.problem_records[selected[0]]
        pane = self.config if problem.get("target") == "config" else self.source
        if problem["source"] != pane.get():
            messagebox.showinfo("Source changed", "Compile again to refresh error locations.", parent=self.root)
            return
        index = f'{problem["line"]}.{problem["column"]-1}'
        self.editor_tabs.select(2 if problem.get("target") == "config" else 0)
        pane.text.mark_set("insert", index)
        pane.text.see(index)
        pane.text.focus_set()

    def language_help(self):
        pairs = "\n".join(f"{standard} → {custom}" for standard, custom in DEFAULT_PAIRS)
        messagebox.showinfo("My custom language", pairs +
            "\n\nUse my custom spellings in program code. Standard spellings are rejected."
            "\nTypes such as int remain valid. Use provide, snap and so_on for control flow."
            "\nuntil repeats while its condition is TRUE."
            "\nCompile/Run checks syntax and types; Translate only scans and converts words."
            "\nOpen Problems and double-click an error to jump to it. Ctrl+G goes to a line.",
            parent=self.root)

    def export_program(self):
        if not self.last_build or not self.last_build.executable:
            return
        if self.built_signature != self._signature():
            messagebox.showinfo("Compile first", "The source or keywords changed. Compile again.",
                                parent=self.root)
            return
        suffix = ".exe" if os.name == "nt" else ""
        destination = filedialog.asksaveasfilename(
            parent=self.root, title="Export compiled program", initialfile="my_program" + suffix,
            defaultextension=suffix, filetypes=[("Executable", "*.exe" if suffix else "*")])
        if destination:
            try:
                shutil.copy2(self.last_build.executable, destination)
                self.status.configure(text="Compiled program exported", fg=ACCENT)
            except OSError as error:
                messagebox.showerror("Export failed", str(error), parent=self.root)

    def close(self):
        if not self._confirm_source():
            return
        if self.config_dirty:
            answer = messagebox.askyesnocancel("Save keywords?", "Save your keyword changes?",
                                               parent=self.root)
            if answer is None or (answer and not self.save_config()):
                return
        self.closing = True
        self._close_started = time.monotonic()
        self.backend.cancel()
        self._finish_close()

    def _finish_close(self):
        if self.worker and self.worker.is_alive() and time.monotonic() - self._close_started < 7:
            self.root.after(80, self._finish_close)
            return
        self.backend.cleanup()
        self.root.destroy()


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (OSError, AttributeError):
            pass
    window = tk.Tk()
    CompilerApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
