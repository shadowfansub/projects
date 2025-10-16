"""
Fuzzy Text Checker - Material Design Edition
Detects potential typos using fuzzy matching.

Installation:
pip install rapidfuzz

To run:
python fuzzy-text-checker.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from rapidfuzz import fuzz
import re


class LineNumberText(tk.Text):
    """Custom Text widget with line numbers."""

    def __init__(self, master, **kwargs):
        self.frame = tk.Frame(master)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)

        self.linenumbers = tk.Text(
            self.frame,
            width=4,
            padx=4,
            takefocus=0,
            border=0,
            background="#f0f0f0",
            state="disabled",
            wrap="none",
            font=kwargs.get("font"),
        )
        self.linenumbers.grid(row=0, column=0, sticky="ns")

        super().__init__(self.frame, **kwargs)
        self.grid(row=0, column=1, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.frame, command=self._on_scrollbar)
        scrollbar.grid(row=0, column=2, sticky="ns")
        self["yscrollcommand"] = scrollbar.set

        self.bind("<<Modified>>", self._on_change)
        self.bind("<Configure>", self._on_change)

        self._update_line_numbers()

    def _on_scrollbar(self, *args):
        self.yview(*args)
        self.linenumbers.yview(*args)

    def _on_change(self, event=None):
        self._update_line_numbers()

    def _update_line_numbers(self):
        line_count = int(self.index("end-1c").split(".")[0])
        line_numbers_text = "\n".join(str(i) for i in range(1, line_count + 1))

        self.linenumbers.config(state="normal")
        self.linenumbers.delete("1.0", "end")
        self.linenumbers.insert("1.0", line_numbers_text)
        self.linenumbers.config(state="disabled")


class FuzzyCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fuzzy Text Checker")
        self.root.geometry("1400x850")
        self.root.minsize(1000, 600)

        # Material Design Colors
        self.colors = {
            "primary": "#2196F3",
            "primary_dark": "#1976D2",
            "accent": "#FF5722",
            "success": "#4CAF50",
            "warning": "#FFC107",
            "text": "#212121",
            "text_secondary": "#757575",
            "bg": "#FFFFFF",
            "bg_light": "#f5f5f5",
            "bg_card": "#FAFAFA",
            "highlight": "#FFF9C4",
            "border": "#E0E0E0",
        }

        self.terms_file = None
        self.text_file = None
        self.terms_modified = False
        self.text_modified = False
        self.results = []
        self.resolved_items = set()

        self.setup_ui()

    def setup_ui(self):
        """Create the user interface."""
        self.root.configure(bg=self.colors["bg_light"])

        # Header
        self.create_header()

        # Main container
        main_container = tk.Frame(self.root, bg=self.colors["bg_light"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Configure grid
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        main_container.grid_columnconfigure(1, weight=2)
        main_container.grid_columnconfigure(2, weight=1)

        # Create three columns
        self.create_terms_section(main_container)
        self.create_text_section(main_container)
        self.create_results_section(main_container)

    def create_header(self):
        """Create the header."""
        header_frame = tk.Frame(self.root, bg=self.colors["primary"], height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        header_content = tk.Frame(header_frame, bg=self.colors["primary"])
        header_content.pack(fill=tk.BOTH, expand=True, padx=20)

        title_label = tk.Label(
            header_content,
            text="📝 Fuzzy Text Checker",
            font=("Segoe UI", 20, "bold"),
            bg=self.colors["primary"],
            fg="white",
        )
        title_label.pack(side=tk.LEFT, pady=20)

        subtitle_label = tk.Label(
            header_content,
            text="Detect potential typos using fuzzy matching",
            font=("Segoe UI", 10),
            bg=self.colors["primary"],
            fg="white",
        )
        subtitle_label.pack(side=tk.LEFT, pady=20, padx=(20, 0))

    def create_terms_section(self, parent):
        """Create the terms section."""
        terms_card = tk.Frame(parent, bg=self.colors["bg"], relief=tk.FLAT, bd=2)
        terms_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Configure grid
        terms_card.grid_rowconfigure(2, weight=1)
        terms_card.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = tk.Frame(terms_card, bg=self.colors["bg"])
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        label = tk.Label(
            header_frame,
            text="Terms Dictionary",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"],
        )
        label.pack(side=tk.LEFT)

        self.terms_status = tk.Label(
            header_frame,
            text="●",
            font=("Segoe UI", 16),
            bg=self.colors["bg"],
            fg=self.colors["text_secondary"],
        )
        self.terms_status.pack(side=tk.RIGHT)

        # Buttons
        btn_frame = tk.Frame(terms_card, bg=self.colors["bg"])
        btn_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))

        load_btn = tk.Button(
            btn_frame,
            text="LOAD",
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["primary"],
            fg="white",
            activebackground=self.colors["primary_dark"],
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=self._load_terms,
        )
        load_btn.pack(side=tk.LEFT, padx=(0, 5))
        load_btn.bind(
            "<Enter>", lambda e: load_btn.config(bg=self.colors["primary_dark"])
        )
        load_btn.bind("<Leave>", lambda e: load_btn.config(bg=self.colors["primary"]))

        self.save_terms_btn = tk.Button(
            btn_frame,
            text="SAVE",
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["success"],
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            state="disabled",
            command=self._save_terms,
        )
        self.save_terms_btn.pack(side=tk.LEFT)

        # Text area
        text_frame = tk.Frame(terms_card, bg=self.colors["bg"])
        text_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.terms_text = tk.Text(
            text_frame,
            font=("Consolas", 10),
            wrap="word",
            relief=tk.FLAT,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["primary"],
            selectbackground=self.colors["primary"],
            selectforeground="white",
            yscrollcommand=scrollbar.set,
        )
        self.terms_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.terms_text.yview)
        self.terms_text.bind("<<Modified>>", self._on_terms_modified)

    def create_text_section(self, parent):
        """Create the text section."""
        text_card = tk.Frame(parent, bg=self.colors["bg"], relief=tk.FLAT, bd=2)
        text_card.grid(row=0, column=1, sticky="nsew", padx=10)

        # Configure grid
        text_card.grid_rowconfigure(2, weight=1)
        text_card.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = tk.Frame(text_card, bg=self.colors["bg"])
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        label = tk.Label(
            header_frame,
            text="Document Text",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"],
        )
        label.pack(side=tk.LEFT)

        self.text_status = tk.Label(
            header_frame,
            text="●",
            font=("Segoe UI", 16),
            bg=self.colors["bg"],
            fg=self.colors["text_secondary"],
        )
        self.text_status.pack(side=tk.RIGHT)

        # Buttons
        btn_frame = tk.Frame(text_card, bg=self.colors["bg"])
        btn_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))

        load_btn = tk.Button(
            btn_frame,
            text="LOAD",
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["primary"],
            fg="white",
            activebackground=self.colors["primary_dark"],
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=self._load_text,
        )
        load_btn.pack(side=tk.LEFT, padx=(0, 5))
        load_btn.bind(
            "<Enter>", lambda e: load_btn.config(bg=self.colors["primary_dark"])
        )
        load_btn.bind("<Leave>", lambda e: load_btn.config(bg=self.colors["primary"]))

        self.save_text_btn = tk.Button(
            btn_frame,
            text="SAVE",
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["success"],
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            state="disabled",
            command=self._save_text,
        )
        self.save_text_btn.pack(side=tk.LEFT)

        # Text area with line numbers
        text_container = tk.Frame(text_card, bg=self.colors["bg"])
        text_container.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))
        text_container.grid_rowconfigure(0, weight=1)
        text_container.grid_columnconfigure(0, weight=1)

        self.text_widget = LineNumberText(
            text_container,
            wrap="word",
            font=("Consolas", 10),
            relief=tk.FLAT,
            bg=self.colors["bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["primary"],
            selectbackground=self.colors["primary"],
            selectforeground="white",
        )
        self.text_widget.frame.grid(row=0, column=0, sticky="nsew")
        self.text_widget.bind("<<Modified>>", self._on_text_modified)

        # Highlight tag
        self.text_widget.tag_configure(
            "highlight",
            background=self.colors["highlight"],
            foreground=self.colors["accent"],
        )

    def create_results_section(self, parent):
        """Create the results section."""
        results_card = tk.Frame(parent, bg=self.colors["bg"], relief=tk.FLAT, bd=2)
        results_card.grid(row=0, column=2, sticky="nsew", padx=(10, 0))

        # Configure grid
        results_card.grid_rowconfigure(3, weight=1)
        results_card.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = tk.Frame(results_card, bg=self.colors["bg"])
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))

        label = tk.Label(
            header_frame,
            text="Analysis Results",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"],
        )
        label.pack(side=tk.LEFT)

        self.results_count = tk.Label(
            header_frame,
            text="0",
            font=("Segoe UI", 9),
            bg=self.colors["bg"],
            fg=self.colors["text_secondary"],
        )
        self.results_count.pack(side=tk.RIGHT)

        # Ratio control
        control_frame = tk.Frame(results_card, bg=self.colors["bg"])
        control_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))

        ratio_label = tk.Label(
            control_frame,
            text="Similarity Ratio:",
            font=("Segoe UI", 9),
            bg=self.colors["bg"],
            fg=self.colors["text"],
        )
        ratio_label.pack(side=tk.LEFT, padx=(0, 5))

        self.ratio_var = tk.StringVar(value="80")
        ratio_entry = tk.Entry(
            control_frame,
            textvariable=self.ratio_var,
            width=5,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            bg=self.colors["bg_light"],
            fg=self.colors["text"],
        )
        ratio_entry.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(
            control_frame,
            text="%",
            font=("Segoe UI", 9),
            bg=self.colors["bg"],
            fg=self.colors["text"],
        ).pack(side=tk.LEFT)

        # Check button
        check_btn = tk.Button(
            results_card,
            text="ANALYZE TEXT",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#E64A19",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=30,
            pady=10,
            command=self._check_text,
        )
        check_btn.grid(row=2, column=0, padx=15, pady=(0, 10))
        check_btn.bind("<Enter>", lambda e: check_btn.config(bg="#E64A19"))
        check_btn.bind("<Leave>", lambda e: check_btn.config(bg=self.colors["accent"]))

        # Results list
        list_frame = tk.Frame(results_card, bg=self.colors["bg"])
        list_frame.grid(row=3, column=0, sticky="nsew", padx=15, pady=(0, 10))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        scrollbar_y = tk.Scrollbar(list_frame, orient="vertical")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        scrollbar_x = tk.Scrollbar(list_frame, orient="horizontal")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        self.results_listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 9),
            bg=self.colors["bg_light"],
            fg=self.colors["text"],
            relief=tk.FLAT,
            selectbackground=self.colors["primary"],
            selectforeground="white",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )
        self.results_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.config(command=self.results_listbox.yview)
        scrollbar_x.config(command=self.results_listbox.xview)
        self.results_listbox.bind("<<ListboxSelect>>", self._on_result_select)

        # Resolve button
        resolve_btn = tk.Button(
            results_card,
            text="MARK AS RESOLVED",
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["success"],
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
            command=self._mark_resolved,
        )
        resolve_btn.grid(row=4, column=0, padx=15, pady=(0, 15))
        resolve_btn.bind("<Enter>", lambda e: resolve_btn.config(bg="#45a049"))
        resolve_btn.bind(
            "<Leave>", lambda e: resolve_btn.config(bg=self.colors["success"])
        )

    def _load_terms(self):
        """Load terms from file."""
        filepath = filedialog.askopenfilename(
            title="Select Terms File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if filepath:
            self.terms_file = filepath
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.terms_text.delete("1.0", tk.END)
            self.terms_text.insert("1.0", content)
            self.terms_text.edit_modified(False)
            self.terms_modified = False
            self.save_terms_btn["state"] = "disabled"
            self.terms_status.config(fg=self.colors["success"])

    def _save_terms(self):
        """Save terms to file."""
        if self.terms_file:
            content = self.terms_text.get("1.0", "end-1c")
            with open(self.terms_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.terms_text.edit_modified(False)
            self.terms_modified = False
            self.save_terms_btn["state"] = "disabled"
            self.terms_status.config(fg=self.colors["success"])
            messagebox.showinfo("Success", "Terms saved successfully")

    def _load_text(self):
        """Load text from file."""
        filepath = filedialog.askopenfilename(
            title="Select Text File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if filepath:
            self.text_file = filepath
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert("1.0", content)
            self.text_widget.edit_modified(False)
            self.text_modified = False
            self.save_text_btn["state"] = "disabled"
            self.text_status.config(fg=self.colors["success"])

    def _save_text(self):
        """Save text to file."""
        if self.text_file:
            content = self.text_widget.get("1.0", "end-1c")
            with open(self.text_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.text_widget.edit_modified(False)
            self.text_modified = False
            self.save_text_btn["state"] = "disabled"
            self.text_status.config(fg=self.colors["success"])
            messagebox.showinfo("Success", "Text saved successfully")

    def _on_terms_modified(self, event=None):
        """Handle terms text modification."""
        if self.terms_text.edit_modified():
            self.terms_modified = True
            self.save_terms_btn["state"] = "normal"
            self.terms_status.config(fg=self.colors["warning"])
            self.terms_text.edit_modified(False)

    def _on_text_modified(self, event=None):
        """Handle text modification."""
        if self.text_widget.edit_modified():
            self.text_modified = True
            self.save_text_btn["state"] = "normal"
            self.text_status.config(fg=self.colors["warning"])
            self.text_widget.edit_modified(False)

    def _normalize_for_comparison(self, text):
        """Normalize text for comparison."""
        return text.strip().lower()

    def _check_text(self):
        """Check text for potential typos."""
        try:
            ratio_threshold = float(self.ratio_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid ratio value")
            return

        terms_content = self.terms_text.get("1.0", "end-1c")
        text_content = self.text_widget.get("1.0", "end-1c")

        if not terms_content.strip():
            messagebox.showwarning("Warning", "Terms list is empty")
            return

        if not text_content.strip():
            messagebox.showwarning("Warning", "Text is empty")
            return

        terms = [t.strip() for t in terms_content.split("\n") if t.strip()]
        lines = text_content.split("\n")

        self.results = []
        self.resolved_items = set()

        for line_num, line in enumerate(lines, 1):
            words_in_line = re.finditer(r"\b[\w\-]+\b", line)

            for match in words_in_line:
                word = match.group()
                word_normalized = self._normalize_for_comparison(word)

                for term in terms:
                    term_normalized = self._normalize_for_comparison(term)

                    if word_normalized == term_normalized:
                        continue

                    ratio = fuzz.ratio(word_normalized, term_normalized)

                    if ratio >= ratio_threshold:
                        context_start = max(0, match.start() - 20)
                        context_end = min(len(line), match.end() + 20)
                        context = line[context_start:context_end].strip()

                        self.results.append(
                            {
                                "line": line_num,
                                "term": term,
                                "found": word,
                                "ratio": ratio,
                                "context": context,
                            }
                        )

        self._update_results_list()

        if not self.results:
            messagebox.showinfo("Results", "No potential typos found! ✓")

    def _update_results_list(self):
        """Update the results listbox."""
        self.results_listbox.delete(0, tk.END)

        visible_count = 0
        for idx, result in enumerate(self.results):
            if idx not in self.resolved_items:
                display = f"L{result['line']}: '{result['found']}' → '{result['term']}' ({result['ratio']:.0f}%)"
                self.results_listbox.insert(tk.END, display)
                visible_count += 1

        self.results_count.config(
            text=f"{visible_count} issue{'s' if visible_count != 1 else ''}"
        )

    def _on_result_select(self, event=None):
        """Handle result selection."""
        selection = self.results_listbox.curselection()
        if selection:
            visible_idx = selection[0]

            actual_idx = 0
            for idx, result in enumerate(self.results):
                if idx not in self.resolved_items:
                    if actual_idx == visible_idx:
                        actual_idx = idx
                        break
                    actual_idx += 1

            if actual_idx < len(self.results):
                result = self.results[actual_idx]
                line_num = result["line"]
                self.text_widget.see(f"{line_num}.0")
                self.text_widget.tag_remove("highlight", "1.0", tk.END)
                self.text_widget.tag_add(
                    "highlight", f"{line_num}.0", f"{line_num}.end"
                )

    def _mark_resolved(self):
        """Mark selected result as resolved."""
        selection = self.results_listbox.curselection()
        if selection:
            visible_idx = selection[0]

            actual_idx = 0
            for idx, result in enumerate(self.results):
                if idx not in self.resolved_items:
                    if actual_idx == visible_idx:
                        actual_idx = idx
                        break
                    actual_idx += 1

            self.resolved_items.add(actual_idx)
            self._update_results_list()


def main():
    root = tk.Tk()
    app = FuzzyCheckerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
