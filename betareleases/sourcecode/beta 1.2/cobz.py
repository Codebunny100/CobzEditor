from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from syntax_config import SYNTAX_MENU_OPTIONS, SYNTAX_SCHEMES

APP_NAME = "Cobz"
APP_VERSION = "0.1.0-beta1"


@dataclass
class DocumentTab:
    frame: tk.Frame
    line_numbers: tk.Text
    text_area: tk.Text
    scroll_x: tk.Scrollbar
    current_file: Path | None = None
    is_dirty: bool = False
    syntax_name: str = "Plain Text"


class TextEditor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1100x720")
        self.root.minsize(720, 480)
        self.root.resizable(True, True)

        self.wrap_enabled = True
        self.status_var = tk.StringVar()
        self.wrap_var = tk.BooleanVar(value=True)
        self.syntax_var = tk.StringVar(value="Plain Text")
        self.documents: list[DocumentTab] = []
        self._tab_counter = 1
        self.find_dialog: tk.Toplevel | None = None
        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.match_case_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._bind_events()
        self.new_file()

    def _build_ui(self) -> None:
        self.root.option_add("*tearOff", False)
        self.root.configure(bg="#0f1722")

        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Cobz.TNotebook", background="#0f1722", borderwidth=0, tabmargins=[0, 0, 0, 0])
        self.style.configure(
            "Cobz.TNotebook.Tab",
            background="#2d3a52",
            foreground="#eceff4",
            padding=(14, 8),
            borderwidth=0,
        )
        self.style.map(
            "Cobz.TNotebook.Tab",
            background=[("selected", "#5e81ac"), ("active", "#4c6688")],
            foreground=[("selected", "#ffffff"), ("active", "#ffffff")],
        )

        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        file_menu = tk.Menu(self.menu_bar)
        edit_menu = tk.Menu(self.menu_bar)
        view_menu = tk.Menu(self.menu_bar)
        syntax_menu = tk.Menu(self.menu_bar)
        help_menu = tk.Menu(self.menu_bar)

        self.menu_bar.add_cascade(label="File", menu=file_menu)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        self.menu_bar.add_cascade(label="Syntax", menu=syntax_menu)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)

        file_menu.add_command(label="New Tab", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Close Tab", accelerator="Ctrl+W", command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.on_close)

        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self._event_generate_on_current("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self._event_generate_on_current("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self._event_generate_on_current("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self._event_generate_on_current("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self._event_generate_on_current("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Find / Replace...", accelerator="Ctrl+F", command=self.show_find_replace)
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self.select_all)

        view_menu.add_checkbutton(label="Word Wrap", variable=self.wrap_var, command=self.toggle_wrap)

        for label, extension in SYNTAX_MENU_OPTIONS:
            syntax_menu.add_radiobutton(
                label=label,
                value=label,
                variable=self.syntax_var,
                command=lambda ext=extension: self.set_syntax_mode(ext),
            )

        help_menu.add_command(label="About", command=self.show_about)

        toolbar = tk.Frame(self.root, bg="#0f1722")
        toolbar.pack(fill="x", padx=14, pady=(12, 0))

        new_tab_button = tk.Button(
            toolbar,
            text="+ New Tab",
            command=self.new_file,
            bg="#5e81ac",
            fg="#ffffff",
            activebackground="#4c6688",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=5,
        )
        new_tab_button.pack(side="left")

        close_tab_button = tk.Button(
            toolbar,
            text="Close Tab",
            command=self.close_current_tab,
            bg="#3b4252",
            fg="#eceff4",
            activebackground="#4c566a",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=5,
        )
        close_tab_button.pack(side="left", padx=(8, 0))

        self.notebook = ttk.Notebook(self.root, style="Cobz.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(10, 8))

        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padx=10,
            pady=6,
            background="#2d3a52",
            foreground="#eceff4",
        )
        self.status_bar.pack(fill="x")

    def _bind_events(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Control-n>", lambda event: self.new_file())
        self.root.bind("<Control-o>", lambda event: self.open_file())
        self.root.bind("<Control-s>", lambda event: self.save_file())
        self.root.bind("<Control-S>", lambda event: self.save_file_as())
        self.root.bind("<Control-q>", lambda event: self.on_close())
        self.root.bind("<Control-f>", lambda event: self.show_find_replace())
        self.root.bind("<Control-a>", lambda event: self.select_all())
        self.root.bind("<Control-w>", lambda event: self.close_current_tab())
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _bind_document_events(self, document: DocumentTab) -> None:
        text_area = document.text_area
        text_area.bind("<<Modified>>", lambda event, doc=document: self._on_modified(doc))
        text_area.bind("<KeyRelease>", lambda event, doc=document: self._refresh_editor_state(doc))
        text_area.bind("<ButtonRelease-1>", lambda event, doc=document: self._refresh_editor_state(doc))
        text_area.bind("<MouseWheel>", lambda event, doc=document: self._sync_line_numbers(doc))
        text_area.bind("<Button-4>", lambda event, doc=document: self._sync_line_numbers(doc))
        text_area.bind("<Button-5>", lambda event, doc=document: self._sync_line_numbers(doc))
        text_area.bind("<Configure>", lambda event, doc=document: self._sync_line_numbers(doc))

    def _create_document_tab(self) -> DocumentTab:
        editor_shell = tk.Frame(self.notebook, bg="#5e81ac", bd=0, highlightthickness=0)
        editor_frame = tk.Frame(editor_shell, bg="#d8dee9")
        editor_frame.pack(fill="both", expand=True, padx=2, pady=2)

        line_numbers = tk.Text(
            editor_frame,
            width=5,
            padx=8,
            takefocus=0,
            border=0,
            background="#eceff4",
            foreground="#000000",
            state="disabled",
            wrap="none",
            font=("Monospace", 11),
            relief="flat",
        )
        line_numbers.pack(side="left", fill="y")

        text_frame = tk.Frame(editor_frame, bg="#d8dee9")
        text_frame.pack(side="left", fill="both", expand=True)

        text_area = tk.Text(
            text_frame,
            undo=True,
            wrap="char" if self.wrap_enabled else "none",
            font=("Monospace", 11),
            background="#dadfe7",
            foreground="#000000",
            insertbackground="#000000",
            selectbackground="#5e81ac",
            padx=12,
            pady=12,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#88c0d0",
            highlightcolor="#5e81ac",
        )
        text_area.pack(side="left", fill="both", expand=True)

        scroll_y = tk.Scrollbar(
            text_frame,
            orient="vertical",
            command=lambda *args, ta=text_area, ln=line_numbers: self._on_vertical_scroll(ta, ln, *args),
            relief="flat",
            activebackground="#81a1c1",
            troughcolor="#cfd8e3",
        )
        scroll_y.pack(side="right", fill="y")
        text_area.config(yscrollcommand=lambda first, last, sb=scroll_y, ln=line_numbers: self._set_scrollbars(sb, ln, first, last))

        scroll_x = tk.Scrollbar(
            editor_shell,
            orient="horizontal",
            command=text_area.xview,
            relief="flat",
            activebackground="#81a1c1",
            troughcolor="#cfd8e3",
        )
        if not self.wrap_enabled:
            scroll_x.pack(fill="x")
        text_area.config(xscrollcommand=None if self.wrap_enabled else scroll_x.set)

        for tag, options in {
            "match": {"background": "#ebcb8b", "foreground": "#2e3440"},
            "current_match": {"background": "#bf616a", "foreground": "#ffffff"},
            "keyword": {"foreground": "#81a1c1"},
            "string": {"foreground": "#a3be8c"},
            "comment": {"foreground": "#616e88"},
            "number": {"foreground": "#b48ead"},
            "tag": {"foreground": "#88c0d0"},
            "heading": {"foreground": "#ebcb8b"},
        }.items():
            text_area.tag_configure(tag, **options)

        document = DocumentTab(
            frame=editor_shell,
            line_numbers=line_numbers,
            text_area=text_area,
            scroll_x=scroll_x,
        )
        self._bind_document_events(document)
        return document

    def _event_generate_on_current(self, sequence: str) -> None:
        document = self._current_document()
        if document is not None:
            document.text_area.event_generate(sequence)

    def _current_document(self) -> DocumentTab | None:
        current_tab = self.notebook.select()
        if not current_tab:
            return None
        for document in self.documents:
            if str(document.frame) == current_tab:
                return document
        return None

    def _document_display_name(self, document: DocumentTab) -> str:
        if document.current_file is not None:
            return document.current_file.name
        index = self.documents.index(document) + 1
        return f"Untitled {index}"

    def _update_tab_label(self, document: DocumentTab) -> None:
        label = self._document_display_name(document)
        if document.is_dirty:
            label = f"*{label}"
        self.notebook.tab(document.frame, text=label)

    def _set_scrollbars(self, scrollbar: tk.Scrollbar, line_numbers: tk.Text, first: str, last: str) -> None:
        scrollbar.set(first, last)
        line_numbers.yview_moveto(float(first))

    def _on_vertical_scroll(self, text_area: tk.Text, line_numbers: tk.Text, *args: str) -> None:
        text_area.yview(*args)
        line_numbers.yview(*args)

    def _sync_line_numbers(self, document: DocumentTab) -> None:
        first, _ = document.text_area.yview()
        document.line_numbers.yview_moveto(first)
        self._update_line_numbers(document)

    def _refresh_editor_state(self, document: DocumentTab | None = None) -> None:
        document = self._current_document() if document is None else document
        if document is None:
            return
        self._update_line_numbers(document)
        self._apply_syntax_highlighting(document)
        if document is self._current_document():
            self._update_status()

    def _on_modified(self, document: DocumentTab) -> None:
        if document.text_area.edit_modified():
            document.is_dirty = True
            self._refresh_editor_state(document)
            self._update_tab_label(document)
            if document is self._current_document():
                self._update_title()
            document.text_area.edit_modified(False)

    def _update_line_numbers(self, document: DocumentTab) -> None:
        line_count = int(document.text_area.index("end-1c").split(".")[0])
        content = "\n".join(str(number) for number in range(1, line_count + 1))
        document.line_numbers.config(state="normal")
        document.line_numbers.delete("1.0", "end")
        document.line_numbers.insert("1.0", content)
        document.line_numbers.config(state="disabled")
        first, _ = document.text_area.yview()
        document.line_numbers.yview_moveto(first)

    def _update_status(self) -> None:
        document = self._current_document()
        if document is None:
            self.status_var.set("")
            return
        cursor_line, cursor_column = document.text_area.index("insert").split(".")
        text_content = document.text_area.get("1.0", "end-1c")
        characters = len(text_content)
        words = len(text_content.split())
        filename = self._document_display_name(document)
        wrap = "Wrap On" if self.wrap_enabled else "Wrap Off"
        dirty = "Modified" if document.is_dirty else "Saved"
        self.status_var.set(
            f"{filename} | {document.syntax_name} | Ln {cursor_line}, Col {int(cursor_column) + 1} | "
            f"{characters} chars | {words} words | {wrap} | {dirty}"
        )

    def _update_title(self) -> None:
        document = self._current_document()
        if document is None:
            self.root.title(APP_NAME)
            return
        name = str(document.current_file) if document.current_file else self._document_display_name(document)
        marker = "*" if document.is_dirty else ""
        self.root.title(f"{marker}{name} - {APP_NAME}")

    def _set_syntax_from_path(self, document: DocumentTab, path: Path | None) -> None:
        if path is None:
            document.syntax_name = "Plain Text"
        else:
            scheme = SYNTAX_SCHEMES.get(path.suffix.lower())
            document.syntax_name = scheme["name"] if scheme else "Plain Text"
        if document is self._current_document():
            self.syntax_var.set(document.syntax_name)

    def set_syntax_mode(self, extension: str | None) -> None:
        document = self._current_document()
        if document is None:
            return
        if extension is None:
            document.syntax_name = "Plain Text"
        else:
            scheme = SYNTAX_SCHEMES.get(extension)
            document.syntax_name = "Plain Text" if scheme is None else scheme["name"]
        self.syntax_var.set(document.syntax_name)
        self._apply_syntax_highlighting(document)
        self._update_status()

    def _clear_syntax_tags(self, document: DocumentTab) -> None:
        for tag in ("keyword", "string", "comment", "number", "tag", "heading"):
            document.text_area.tag_remove(tag, "1.0", "end")

    def _clear_search_tags(self, document: DocumentTab) -> None:
        document.text_area.tag_remove("match", "1.0", "end")
        document.text_area.tag_remove("current_match", "1.0", "end")

    def _index_from_offset(self, offset: int) -> str:
        return f"1.0+{offset}c"

    def _apply_pattern(self, document: DocumentTab, pattern: str, tag: str, text: str, flags: int = 0) -> None:
        for match in re.finditer(pattern, text, flags):
            start = self._index_from_offset(match.start())
            end = self._index_from_offset(match.end())
            document.text_area.tag_add(tag, start, end)

    def _highlight_keywords(self, document: DocumentTab, text: str, keywords: set[str]) -> None:
        if not keywords:
            return
        pattern = r"\b(" + "|".join(re.escape(word) for word in sorted(keywords)) + r")\b"
        self._apply_pattern(document, pattern, "keyword", text)

    def _apply_syntax_highlighting(self, document: DocumentTab) -> None:
        self._clear_syntax_tags(document)
        text = document.text_area.get("1.0", "end-1c")
        if not text:
            return

        scheme = None if document.current_file is None else SYNTAX_SCHEMES.get(document.current_file.suffix.lower())
        if scheme is None:
            scheme = SYNTAX_SCHEMES.get(".md") if document.syntax_name == "Markdown" else None

        if scheme is None:
            return

        self._highlight_keywords(document, text, scheme.get("keywords", set()))

        if scheme.get("string"):
            self._apply_pattern(document, scheme["string"], "string", text, re.MULTILINE)
        if scheme.get("comment"):
            self._apply_pattern(document, scheme["comment"], "comment", text, re.MULTILINE)
        if scheme.get("number"):
            self._apply_pattern(document, scheme["number"], "number", text, re.MULTILINE)

        if scheme["name"] == "HTML":
            self._apply_pattern(document, r"</?[a-zA-Z][^>\n]*?>", "tag", text)
        if scheme["name"] == "Markdown":
            self._apply_pattern(document, r"^(#{1,6}\s.*)$", "heading", text, re.MULTILINE)

    def _search_options(self) -> dict[str, object]:
        return {"nocase": not self.match_case_var.get()}

    def _highlight_search_matches(self, document: DocumentTab, search_term: str) -> list[tuple[str, str]]:
        self._clear_search_tags(document)
        if not search_term:
            return []

        ranges: list[tuple[str, str]] = []
        index = "1.0"
        while True:
            index = document.text_area.search(search_term, index, stopindex="end", **self._search_options())
            if not index:
                break
            end_index = f"{index}+{len(search_term)}c"
            document.text_area.tag_add("match", index, end_index)
            ranges.append((index, end_index))
            index = end_index
        return ranges

    def _focus_match(self, document: DocumentTab, start: str, end: str) -> None:
        document.text_area.tag_remove("current_match", "1.0", "end")
        document.text_area.tag_add("current_match", start, end)
        document.text_area.mark_set("insert", start)
        document.text_area.see(start)
        document.text_area.tag_remove("sel", "1.0", "end")
        document.text_area.tag_add("sel", start, end)
        document.text_area.focus_set()

    def _find_in_direction(self, backwards: bool = False) -> bool:
        document = self._current_document()
        search_term = self.find_var.get()
        if document is None or not search_term:
            return False

        self._highlight_search_matches(document, search_term)
        insert_index = document.text_area.index("insert")
        if backwards:
            start_index = document.text_area.search(
                search_term,
                insert_index,
                stopindex="1.0",
                backwards=True,
                **self._search_options(),
            )
            if not start_index:
                start_index = document.text_area.search(
                    search_term,
                    "end-1c",
                    stopindex="1.0",
                    backwards=True,
                    **self._search_options(),
                )
        else:
            start_index = document.text_area.search(search_term, f"{insert_index}+1c", stopindex="end", **self._search_options())
            if not start_index:
                start_index = document.text_area.search(search_term, "1.0", stopindex="end", **self._search_options())

        if not start_index:
            messagebox.showinfo("Find / Replace", f'No matches for "{search_term}".', parent=self.root)
            return False

        end_index = f"{start_index}+{len(search_term)}c"
        self._focus_match(document, start_index, end_index)
        return True

    def _replace_current(self) -> bool:
        document = self._current_document()
        search_term = self.find_var.get()
        replacement = self.replace_var.get()
        if document is None or not search_term:
            return False

        ranges = document.text_area.tag_nextrange("current_match", "1.0")
        if not ranges:
            if not self._find_in_direction(backwards=False):
                return False
            ranges = document.text_area.tag_nextrange("current_match", "1.0")
            if not ranges:
                return False

        start, end = ranges
        if document.text_area.get(start, end) != search_term and self.match_case_var.get():
            if not self._find_in_direction(backwards=False):
                return False
            ranges = document.text_area.tag_nextrange("current_match", "1.0")
            if not ranges:
                return False
            start, end = ranges

        document.text_area.delete(start, end)
        document.text_area.insert(start, replacement)
        new_end = f"{start}+{len(replacement)}c"
        document.is_dirty = True
        document.text_area.edit_modified(False)
        self._refresh_editor_state(document)
        self._update_tab_label(document)
        self._update_title()
        self._highlight_search_matches(document, search_term)
        self._focus_match(document, start, new_end)
        return True

    def _replace_all(self) -> None:
        document = self._current_document()
        search_term = self.find_var.get()
        replacement = self.replace_var.get()
        if document is None or not search_term:
            return

        text = document.text_area.get("1.0", "end-1c")
        if self.match_case_var.get():
            count = text.count(search_term)
            replaced = text.replace(search_term, replacement)
        else:
            pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            replaced, count = pattern.subn(replacement, text)

        if count == 0:
            messagebox.showinfo("Find / Replace", f'No matches for "{search_term}".', parent=self.root)
            return

        document.text_area.delete("1.0", "end")
        document.text_area.insert("1.0", replaced)
        document.is_dirty = True
        document.text_area.edit_modified(False)
        self._refresh_editor_state(document)
        self._update_tab_label(document)
        self._update_title()
        self._highlight_search_matches(document, search_term)
        self._update_status()
        messagebox.showinfo("Find / Replace", f"Replaced {count} occurrence(s).", parent=self.root)

    def _on_find_dialog_close(self) -> None:
        dialog = self.find_dialog
        self.find_dialog = None
        document = self._current_document()
        if document is not None:
            self._clear_search_tags(document)
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()

    def show_find_replace(self) -> None:
        if self.find_dialog is not None and self.find_dialog.winfo_exists():
            self.find_dialog.deiconify()
            self.find_dialog.lift()
            self.find_dialog.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Find / Replace")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(bg="#1f2937")
        dialog.protocol("WM_DELETE_WINDOW", self._on_find_dialog_close)
        self.find_dialog = dialog

        container = tk.Frame(dialog, bg="#1f2937", padx=12, pady=12)
        container.pack(fill="both", expand=True)

        tk.Label(container, text="Find", bg="#1f2937", fg="#eceff4").grid(row=0, column=0, sticky="w", pady=(0, 6))
        find_entry = tk.Entry(container, textvariable=self.find_var, width=32)
        find_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 6))

        tk.Label(container, text="Replace", bg="#1f2937", fg="#eceff4").grid(row=1, column=0, sticky="w", pady=(0, 6))
        replace_entry = tk.Entry(container, textvariable=self.replace_var, width=32)
        replace_entry.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(0, 6))

        match_case = tk.Checkbutton(
            container,
            text="Match case",
            variable=self.match_case_var,
            bg="#1f2937",
            fg="#eceff4",
            selectcolor="#374151",
            activebackground="#1f2937",
            activeforeground="#ffffff",
            command=lambda: self._highlight_search_matches(self._current_document(), self.find_var.get()) if self._current_document() else None,
        )
        match_case.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))

        tk.Button(container, text="Next", command=lambda: self._find_in_direction(False), bg="#5e81ac", fg="#ffffff", relief="flat").grid(row=3, column=0, sticky="ew", padx=(0, 6))
        tk.Button(container, text="Previous", command=lambda: self._find_in_direction(True), bg="#4c6688", fg="#ffffff", relief="flat").grid(row=3, column=1, sticky="ew", padx=(0, 6))
        tk.Button(container, text="Replace", command=self._replace_current, bg="#6b8f71", fg="#ffffff", relief="flat").grid(row=3, column=2, sticky="ew", padx=(0, 6))
        tk.Button(container, text="Replace All", command=self._replace_all, bg="#7c5e8f", fg="#ffffff", relief="flat").grid(row=3, column=3, sticky="ew")

        container.columnconfigure(1, weight=1)
        container.columnconfigure(2, weight=1)
        container.columnconfigure(3, weight=1)

        find_entry.bind("<Return>", lambda event: self._find_in_direction(False))
        replace_entry.bind("<Return>", lambda event: self._replace_current())
        find_entry.bind(
            "<KeyRelease>",
            lambda event: self._highlight_search_matches(self._current_document(), self.find_var.get()) if self._current_document() else None,
        )
        find_entry.focus_set()

    def _confirm_discard_changes(self, document: DocumentTab) -> bool:
        if not document.is_dirty:
            return True

        self.notebook.select(document.frame)
        answer = messagebox.askyesnocancel(
            "Unsaved Changes",
            f'Save changes to "{self._document_display_name(document)}" before continuing?',
            parent=self.root,
        )
        if answer is None:
            return False
        if answer:
            return self.save_file(document)
        return True

    def new_file(self) -> bool:
        document = self._create_document_tab()
        self.documents.append(document)
        self.notebook.add(document.frame, text=f"Untitled {self._tab_counter}")
        self._tab_counter += 1
        self.notebook.select(document.frame)
        document.text_area.edit_modified(False)
        self._refresh_editor_state(document)
        self._update_tab_label(document)
        self._update_status()
        self._update_title()
        document.text_area.focus_set()
        return True

    def open_file(self) -> bool:
        filename = filedialog.askopenfilename(parent=self.root)
        if not filename:
            return False

        path = Path(filename)
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            messagebox.showerror("Open Failed", "Cobz currently supports UTF-8 text files.", parent=self.root)
            return False
        except OSError as error:
            messagebox.showerror("Open Failed", str(error), parent=self.root)
            return False

        document = self._create_document_tab()
        document.text_area.insert("1.0", contents)
        document.current_file = path
        self._set_syntax_from_path(document, path)
        document.text_area.edit_reset()
        document.text_area.edit_modified(False)

        self.documents.append(document)
        self.notebook.add(document.frame, text=path.name)
        self.notebook.select(document.frame)
        self._refresh_editor_state(document)
        self._update_tab_label(document)
        self._update_status()
        self._update_title()
        document.text_area.focus_set()
        return True

    def save_file(self, document: DocumentTab | None = None) -> bool:
        document = self._current_document() if document is None else document
        if document is None:
            return False
        if document.current_file is None:
            return self.save_file_as(document)
        return self._write_to_path(document, document.current_file)

    def save_file_as(self, document: DocumentTab | None = None) -> bool:
        document = self._current_document() if document is None else document
        if document is None:
            return False
        filename = filedialog.asksaveasfilename(parent=self.root)
        if not filename:
            return False
        return self._write_to_path(document, Path(filename))

    def _write_to_path(self, document: DocumentTab, path: Path) -> bool:
        try:
            path.write_text(document.text_area.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Save Failed", str(error), parent=self.root)
            return False

        document.current_file = path
        document.is_dirty = False
        self._set_syntax_from_path(document, path)
        document.text_area.edit_modified(False)
        self._refresh_editor_state(document)
        self._update_tab_label(document)
        if document is self._current_document():
            self._update_title()
            self._update_status()
        return True

    def select_all(self) -> str:
        document = self._current_document()
        if document is None:
            return "break"
        document.text_area.tag_add("sel", "1.0", "end")
        document.text_area.mark_set("insert", "1.0")
        document.text_area.see("insert")
        return "break"

    def toggle_wrap(self) -> None:
        self.wrap_enabled = self.wrap_var.get()

        for document in self.documents:
            if self.wrap_enabled:
                document.text_area.config(wrap="char", xscrollcommand=None)
                document.scroll_x.pack_forget()
            else:
                document.text_area.config(wrap="none", xscrollcommand=document.scroll_x.set)
                document.scroll_x.pack(fill="x")

        self._update_status()

    def _close_document(self, document: DocumentTab) -> bool:
        if not self._confirm_discard_changes(document):
            return False

        self.notebook.forget(document.frame)
        self.documents.remove(document)
        document.frame.destroy()

        if not self.documents:
            self.new_file()
        else:
            current = self._current_document()
            if current is not None:
                self._sync_syntax_menu(current)
                self._update_status()
                self._update_title()
        return True

    def close_current_tab(self) -> bool:
        document = self._current_document()
        if document is None:
            return False
        return self._close_document(document)

    def _sync_syntax_menu(self, document: DocumentTab) -> None:
        self.syntax_var.set(document.syntax_name)

    def _on_tab_changed(self, event: tk.Event | None = None) -> None:
        document = self._current_document()
        if document is None:
            return
        self._sync_syntax_menu(document)
        document.text_area.focus_set()
        self._refresh_editor_state(document)
        self._update_status()
        self._update_title()

    def show_about(self) -> None:
        messagebox.showinfo(
            "About Cobz",
            f"{APP_NAME} {APP_VERSION}\n\nA lightweight Linux text editor with basic syntax highlighting for Python, HTML, CSS, JavaScript, JSON, and Markdown.",
            parent=self.root,
        )

    def on_close(self) -> None:
        for document in self.documents[:]:
            if not self._confirm_discard_changes(document):
                return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    TextEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
