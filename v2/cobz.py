from __future__ import annotations

from pathlib import Path
import keyword
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog


SYNTAX_SCHEMES = {
    ".py": {
        "name": "Python",
        "keywords": set(keyword.kwlist),
        "comment": r"#.*$",
        "string": r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"|'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\")",
        "number": r"\b\d+(?:\.\d+)?\b",
    },
    ".html": {
        "name": "HTML",
        "keywords": {
            "html",
            "head",
            "body",
            "div",
            "span",
            "script",
            "style",
            "title",
            "meta",
            "link",
            "main",
            "section",
            "article",
            "header",
            "footer",
            "nav",
            "button",
            "form",
            "input",
            "label",
            "h1",
            "h2",
            "h3",
            "p",
            "a",
            "img",
            "ul",
            "li",
        },
        "comment": r"<!--[\s\S]*?-->",
        "string": r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\")",
        "number": r"\b\d+(?:\.\d+)?\b",
    },
    ".htm": {
        "name": "HTML",
        "keywords": {
            "html",
            "head",
            "body",
            "div",
            "span",
            "script",
            "style",
            "title",
            "meta",
            "link",
        },
        "comment": r"<!--[\s\S]*?-->",
        "string": r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\")",
        "number": r"\b\d+(?:\.\d+)?\b",
    },
    ".css": {
        "name": "CSS",
        "keywords": {
            "color",
            "background",
            "display",
            "position",
            "padding",
            "margin",
            "font",
            "border",
            "grid",
            "flex",
            "width",
            "height",
        },
        "comment": r"/\*[\s\S]*?\*/",
        "string": r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\")",
        "number": r"\b\d+(?:\.\d+)?(?:px|rem|em|%)?\b",
    },
    ".js": {
        "name": "JavaScript",
        "keywords": {
            "function",
            "return",
            "const",
            "let",
            "var",
            "if",
            "else",
            "for",
            "while",
            "class",
            "import",
            "export",
            "new",
            "async",
            "await",
        },
        "comment": r"//.*$|/\*[\s\S]*?\*/",
        "string": r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"|`([^`\\]|\\.)*`)",
        "number": r"\b\d+(?:\.\d+)?\b",
    },
    ".json": {
        "name": "JSON",
        "keywords": {"true", "false", "null"},
        "comment": None,
        "string": r"\"([^\"\\]|\\.)*\"",
        "number": r"\b\d+(?:\.\d+)?\b",
    },
    ".md": {
        "name": "Markdown",
        "keywords": set(),
        "comment": None,
        "string": r"`[^`]*`",
        "number": None,
    },
}

SYNTAX_MENU_OPTIONS = [
    ("Plain Text", None),
    ("Python", ".py"),
    ("HTML", ".html"),
    ("CSS", ".css"),
    ("JavaScript", ".js"),
    ("JSON", ".json"),
    ("Markdown", ".md"),
]


class TextEditor:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Cobz")
        self.root.geometry("1100x720")
        self.root.minsize(720, 480)

        self.current_file: Path | None = None
        self.is_dirty = False
        self.wrap_enabled = False
        self.status_var = tk.StringVar()
        self.wrap_var = tk.BooleanVar(value=False)
        self.syntax_var = tk.StringVar(value="Plain Text")
        self.syntax_name = "Plain Text"

        self._build_ui()
        self._bind_events()
        self._update_line_numbers()
        self._update_status()
        self._update_title()

    def _build_ui(self) -> None:
        self.root.option_add("*tearOff", False)

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

        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.on_close)

        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self.text_area.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self.text_area.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self.text_area.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self.text_area.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self.text_area.event_generate("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Find...", accelerator="Ctrl+F", command=self.find_text)
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

        editor_frame = tk.Frame(self.root, bg="#d8dee9")
        editor_frame.pack(fill="both", expand=True)

        self.line_numbers = tk.Text(
            editor_frame,
            width=5,
            padx=8,
            takefocus=0,
            border=0,
            background="#eceff4",
            foreground="#4c566a",
            state="disabled",
            wrap="none",
            font=("Monospace", 11),
        )
        self.line_numbers.pack(side="left", fill="y")

        text_frame = tk.Frame(editor_frame)
        text_frame.pack(side="left", fill="both", expand=True)

        self.text_area = tk.Text(
            text_frame,
            undo=True,
            wrap="none",
            font=("Monospace", 11),
            background="#2e3440",
            foreground="#eceff4",
            insertbackground="#eceff4",
            selectbackground="#5e81ac",
            padx=12,
            pady=12,
        )
        self.text_area.pack(side="left", fill="both", expand=True)

        scroll_y = tk.Scrollbar(text_frame, orient="vertical", command=self._on_vertical_scroll)
        scroll_y.pack(side="right", fill="y")
        self.text_area.config(yscrollcommand=lambda first, last: self._set_scrollbars(scroll_y, first, last))

        scroll_x = tk.Scrollbar(self.root, orient="horizontal", command=self.text_area.xview)
        scroll_x.pack(fill="x")
        self.text_area.config(xscrollcommand=scroll_x.set)

        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padx=10,
            pady=6,
            background="#3b4252",
            foreground="#eceff4",
        )
        status_bar.pack(fill="x")

        self.text_area.tag_configure("match", background="#ebcb8b", foreground="#2e3440")
        self.text_area.tag_configure("keyword", foreground="#81a1c1")
        self.text_area.tag_configure("string", foreground="#a3be8c")
        self.text_area.tag_configure("comment", foreground="#616e88")
        self.text_area.tag_configure("number", foreground="#b48ead")
        self.text_area.tag_configure("tag", foreground="#88c0d0")
        self.text_area.tag_configure("heading", foreground="#ebcb8b")

    def _bind_events(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.root.bind("<Control-n>", lambda event: self.new_file())
        self.root.bind("<Control-o>", lambda event: self.open_file())
        self.root.bind("<Control-s>", lambda event: self.save_file())
        self.root.bind("<Control-S>", lambda event: self.save_file_as())
        self.root.bind("<Control-q>", lambda event: self.on_close())
        self.root.bind("<Control-f>", lambda event: self.find_text())
        self.root.bind("<Control-a>", lambda event: self.select_all())

        self.text_area.bind("<<Modified>>", self._on_modified)
        self.text_area.bind("<KeyRelease>", lambda event: self._refresh_editor_state())
        self.text_area.bind("<ButtonRelease-1>", lambda event: self._refresh_editor_state())
        self.text_area.bind("<MouseWheel>", lambda event: self._sync_line_numbers())
        self.text_area.bind("<Button-4>", lambda event: self._sync_line_numbers())
        self.text_area.bind("<Button-5>", lambda event: self._sync_line_numbers())
        self.text_area.bind("<Configure>", lambda event: self._sync_line_numbers())

    def _set_scrollbars(self, scrollbar: tk.Scrollbar, first: str, last: str) -> None:
        scrollbar.set(first, last)
        self.line_numbers.yview_moveto(float(first))

    def _on_vertical_scroll(self, *args: str) -> None:
        self.text_area.yview(*args)
        self.line_numbers.yview(*args)

    def _sync_line_numbers(self) -> None:
        first, _ = self.text_area.yview()
        self.line_numbers.yview_moveto(first)
        self._update_line_numbers()

    def _refresh_editor_state(self) -> None:
        self._update_line_numbers()
        self._apply_syntax_highlighting()
        self._update_status()

    def _on_modified(self, event: tk.Event | None = None) -> None:
        if self.text_area.edit_modified():
            self.is_dirty = True
            self._refresh_editor_state()
            self._update_title()
            self.text_area.edit_modified(False)

    def _update_line_numbers(self) -> None:
        line_count = int(self.text_area.index("end-1c").split(".")[0])
        content = "\n".join(str(number) for number in range(1, line_count + 1))
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", content)
        self.line_numbers.config(state="disabled")
        first, _ = self.text_area.yview()
        self.line_numbers.yview_moveto(first)

    def _update_status(self) -> None:
        cursor_line, cursor_column = self.text_area.index("insert").split(".")
        text_content = self.text_area.get("1.0", "end-1c")
        characters = len(text_content)
        words = len(text_content.split())
        filename = self.current_file.name if self.current_file else "Untitled"
        wrap = "Wrap On" if self.wrap_enabled else "Wrap Off"
        dirty = "Modified" if self.is_dirty else "Saved"
        self.status_var.set(
            f"{filename} | {self.syntax_name} | Ln {cursor_line}, Col {int(cursor_column) + 1} | "
            f"{characters} chars | {words} words | {wrap} | {dirty}"
        )

    def _update_title(self) -> None:
        name = str(self.current_file) if self.current_file else "Untitled"
        marker = "*" if self.is_dirty else ""
        self.root.title(f"{marker}{name} - Cobz")

    def _set_syntax_from_path(self, path: Path | None) -> None:
        if path is None:
            self.syntax_name = "Plain Text"
        else:
            scheme = SYNTAX_SCHEMES.get(path.suffix.lower())
            self.syntax_name = scheme["name"] if scheme else "Plain Text"
        self.syntax_var.set(self.syntax_name)

    def set_syntax_mode(self, extension: str | None) -> None:
        if extension is None:
            self.syntax_name = "Plain Text"
        else:
            scheme = SYNTAX_SCHEMES.get(extension)
            self.syntax_name = "Plain Text" if scheme is None else scheme["name"]
        self.syntax_var.set(self.syntax_name)
        self._apply_syntax_highlighting()
        self._update_status()

    def _clear_syntax_tags(self) -> None:
        for tag in ("keyword", "string", "comment", "number", "tag", "heading"):
            self.text_area.tag_remove(tag, "1.0", "end")

    def _index_from_offset(self, offset: int) -> str:
        return f"1.0+{offset}c"

    def _apply_pattern(self, pattern: str, tag: str, text: str, flags: int = 0) -> None:
        for match in re.finditer(pattern, text, flags):
            start = self._index_from_offset(match.start())
            end = self._index_from_offset(match.end())
            self.text_area.tag_add(tag, start, end)

    def _highlight_keywords(self, text: str, keywords: set[str]) -> None:
        if not keywords:
            return
        pattern = r"\b(" + "|".join(re.escape(word) for word in sorted(keywords)) + r")\b"
        self._apply_pattern(pattern, "keyword", text)

    def _apply_syntax_highlighting(self) -> None:
        self._clear_syntax_tags()
        text = self.text_area.get("1.0", "end-1c")
        if not text:
            return

        scheme = None if self.current_file is None else SYNTAX_SCHEMES.get(self.current_file.suffix.lower())
        if scheme is None:
            markdown_scheme = SYNTAX_SCHEMES.get(".md") if self.syntax_name == "Markdown" else None
            scheme = markdown_scheme

        if scheme is None:
            return

        self._highlight_keywords(text, scheme.get("keywords", set()))

        if scheme.get("string"):
            self._apply_pattern(scheme["string"], "string", text, re.MULTILINE)
        if scheme.get("comment"):
            self._apply_pattern(scheme["comment"], "comment", text, re.MULTILINE)
        if scheme.get("number"):
            self._apply_pattern(scheme["number"], "number", text, re.MULTILINE)

        if scheme["name"] == "HTML":
            self._apply_pattern(r"</?[a-zA-Z][^>\n]*?>", "tag", text)
        if scheme["name"] == "Markdown":
            self._apply_pattern(r"^(#{1,6}\s.*)$", "heading", text, re.MULTILINE)

    def _confirm_discard_changes(self) -> bool:
        if not self.is_dirty:
            return True

        answer = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes. Save them before continuing?",
            parent=self.root,
        )
        if answer is None:
            return False
        if answer:
            return self.save_file()
        return True

    def new_file(self) -> bool:
        if not self._confirm_discard_changes():
            return False

        self.text_area.delete("1.0", "end")
        self.current_file = None
        self.is_dirty = False
        self._set_syntax_from_path(None)
        self.text_area.edit_reset()
        self.text_area.edit_modified(False)
        self._refresh_editor_state()
        self._update_title()
        return True

    def open_file(self) -> bool:
        if not self._confirm_discard_changes():
            return False

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

        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", contents)
        self.current_file = path
        self.is_dirty = False
        self._set_syntax_from_path(path)
        self.text_area.edit_reset()
        self.text_area.edit_modified(False)
        self._refresh_editor_state()
        self._update_title()
        return True

    def save_file(self) -> bool:
        if self.current_file is None:
            return self.save_file_as()
        return self._write_to_path(self.current_file)

    def save_file_as(self) -> bool:
        filename = filedialog.asksaveasfilename(parent=self.root)
        if not filename:
            return False
        path = Path(filename)
        return self._write_to_path(path)

    def _write_to_path(self, path: Path) -> bool:
        try:
            path.write_text(self.text_area.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Save Failed", str(error), parent=self.root)
            return False

        self.current_file = path
        self.is_dirty = False
        self._set_syntax_from_path(path)
        self.text_area.edit_modified(False)
        self._refresh_editor_state()
        self._update_title()
        return True

    def find_text(self) -> None:
        search_term = simpledialog.askstring("Find", "Find text:", parent=self.root)
        self.text_area.tag_remove("match", "1.0", "end")
        if not search_term:
            return

        index = "1.0"
        found_any = False
        while True:
            index = self.text_area.search(search_term, index, stopindex="end", nocase=True)
            if not index:
                break
            end_index = f"{index}+{len(search_term)}c"
            self.text_area.tag_add("match", index, end_index)
            index = end_index
            found_any = True

        if found_any:
            first_match = self.text_area.tag_nextrange("match", "1.0")
            if first_match:
                self.text_area.mark_set("insert", first_match[0])
                self.text_area.see(first_match[0])
        else:
            messagebox.showinfo("Find", f'No matches for "{search_term}".', parent=self.root)

    def select_all(self) -> str:
        self.text_area.tag_add("sel", "1.0", "end")
        self.text_area.mark_set("insert", "1.0")
        self.text_area.see("insert")
        return "break"

    def toggle_wrap(self) -> None:
        self.wrap_enabled = self.wrap_var.get()
        self.text_area.config(wrap="word" if self.wrap_enabled else "none")
        self._update_status()

    def show_about(self) -> None:
        messagebox.showinfo(
            "About Cobz",
            "Cobz\n\nA lightweight Linux text editor with basic syntax highlighting for Python, HTML, CSS, JavaScript, JSON, and Markdown.",
            parent=self.root,
        )

    def on_close(self) -> None:
        if self._confirm_discard_changes():
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    TextEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
