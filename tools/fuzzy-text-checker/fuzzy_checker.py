import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from rapidfuzz import fuzz
import re
from pathlib import Path


class LineNumberText(tk.Text):
    def __init__(self, master, **kwargs):
        self.frame = tk.Frame(master)
        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        
        self.linenumbers = tk.Text(self.frame, width=4, padx=4, takefocus=0,
                                   border=0, background='#f0f0f0', state='disabled',
                                   wrap='none', font=kwargs.get('font'))
        self.linenumbers.grid(row=0, column=0, sticky='ns')
        
        super().__init__(self.frame, **kwargs)
        self.grid(row=0, column=1, sticky='nsew')
        
        scrollbar = ttk.Scrollbar(self.frame, command=self._on_scrollbar)
        scrollbar.grid(row=0, column=2, sticky='ns')
        self['yscrollcommand'] = scrollbar.set
        
        self.bind('<<Modified>>', self._on_change)
        self.bind('<Configure>', self._on_change)
        
        self._update_line_numbers()
    
    def _on_scrollbar(self, *args):
        self.yview(*args)
        self.linenumbers.yview(*args)
    
    def _on_change(self, event=None):
        self._update_line_numbers()
    
    def _update_line_numbers(self):
        line_count = int(self.index('end-1c').split('.')[0])
        line_numbers_text = "\n".join(str(i) for i in range(1, line_count + 1))
        
        self.linenumbers.config(state='normal')
        self.linenumbers.delete('1.0', 'end')
        self.linenumbers.insert('1.0', line_numbers_text)
        self.linenumbers.config(state='disabled')


class FuzzyCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fuzzy Text Checker")
        self.root.geometry("1400x800")
        
        self.terms_file = None
        self.text_file = None
        self.terms_modified = False
        self.text_modified = False
        self.results = []
        self.resolved_items = set()
        
        self._create_widgets()
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=3)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.grid(row=0, column=0, rowspan=2, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        terms_frame = ttk.LabelFrame(main_frame, text="Terms", padding="5")
        paned_window.add(terms_frame, weight=1)
        terms_frame.columnconfigure(0, weight=1)
        terms_frame.rowconfigure(1, weight=1)
        
        terms_buttons = ttk.Frame(terms_frame)
        terms_buttons.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(terms_buttons, text="Load Terms", command=self._load_terms).pack(side=tk.LEFT, padx=2)
        self.save_terms_btn = ttk.Button(terms_buttons, text="Save Terms", command=self._save_terms, state='disabled')
        self.save_terms_btn.pack(side=tk.LEFT, padx=2)
        
        self.terms_text = tk.Text(terms_frame, width=30, wrap='word', font=('Consolas', 10))
        self.terms_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.terms_text.bind('<<Modified>>', self._on_terms_modified)
        
        terms_scroll = ttk.Scrollbar(terms_frame, command=self.terms_text.yview)
        terms_scroll.grid(row=1, column=1, sticky='ns')
        self.terms_text['yscrollcommand'] = terms_scroll.set
        
        text_frame = ttk.LabelFrame(main_frame, text="Text", padding="5")
        paned_window.add(text_frame, weight=3)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)
        
        text_buttons = ttk.Frame(text_frame)
        text_buttons.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(text_buttons, text="Load Text", command=self._load_text).pack(side=tk.LEFT, padx=2)
        self.save_text_btn = ttk.Button(text_buttons, text="Save Text", command=self._save_text, state='disabled')
        self.save_text_btn.pack(side=tk.LEFT, padx=2)
        
        self.text_widget = LineNumberText(text_frame, wrap='word', font=('Consolas', 10))
        self.text_widget.frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.text_widget.bind('<<Modified>>', self._on_text_modified)
        
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="5")
        paned_window.add(results_frame, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
        
        results_top = ttk.Frame(results_frame)
        results_top.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(results_top, text="Ratio:").pack(side=tk.LEFT, padx=2)
        self.ratio_var = tk.StringVar(value="80")
        ratio_entry = ttk.Entry(results_top, textvariable=self.ratio_var, width=5)
        ratio_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(results_top, text="Check", command=self._check_text).pack(side=tk.LEFT, padx=10)
        
        results_list_frame = ttk.Frame(results_frame)
        results_list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_list_frame.columnconfigure(0, weight=1)
        results_list_frame.rowconfigure(0, weight=1)
        
        self.results_listbox = tk.Listbox(results_list_frame, font=('Consolas', 9))
        self.results_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.results_listbox.bind('<<ListboxSelect>>', self._on_result_select)
        
        results_yscroll = ttk.Scrollbar(results_list_frame, orient='vertical', command=self.results_listbox.yview)
        results_yscroll.grid(row=0, column=1, sticky='ns')
        self.results_listbox['yscrollcommand'] = results_yscroll.set
        
        results_xscroll = ttk.Scrollbar(results_list_frame, orient='horizontal', command=self.results_listbox.xview)
        results_xscroll.grid(row=1, column=0, sticky='ew')
        self.results_listbox['xscrollcommand'] = results_xscroll.set
        
        ttk.Button(results_frame, text="Mark as Resolved", command=self._mark_resolved).grid(row=2, column=0, pady=(5, 0))
        
    def _load_terms(self):
        filepath = filedialog.askopenfilename(
            title="Select Terms File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            self.terms_file = filepath
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.terms_text.delete('1.0', tk.END)
            self.terms_text.insert('1.0', content)
            self.terms_text.edit_modified(False)
            self.terms_modified = False
            self.save_terms_btn['state'] = 'disabled'
    
    def _save_terms(self):
        if self.terms_file:
            content = self.terms_text.get('1.0', 'end-1c')
            with open(self.terms_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.terms_text.edit_modified(False)
            self.terms_modified = False
            self.save_terms_btn['state'] = 'disabled'
            messagebox.showinfo("Success", "Terms saved successfully")
    
    def _load_text(self):
        filepath = filedialog.askopenfilename(
            title="Select Text File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            self.text_file = filepath
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', content)
            self.text_widget.edit_modified(False)
            self.text_modified = False
            self.save_text_btn['state'] = 'disabled'
    
    def _save_text(self):
        if self.text_file:
            content = self.text_widget.get('1.0', 'end-1c')
            with open(self.text_file, 'w', encoding='utf-8') as f:
                f.write(content)
            self.text_widget.edit_modified(False)
            self.text_modified = False
            self.save_text_btn['state'] = 'disabled'
            messagebox.showinfo("Success", "Text saved successfully")
    
    def _on_terms_modified(self, event=None):
        if self.terms_text.edit_modified():
            self.terms_modified = True
            self.save_terms_btn['state'] = 'normal'
            self.terms_text.edit_modified(False)
    
    def _on_text_modified(self, event=None):
        if self.text_widget.edit_modified():
            self.text_modified = True
            self.save_text_btn['state'] = 'normal'
            self.text_widget.edit_modified(False)
    
    def _normalize_for_comparison(self, text):
        return text.strip().lower()
    
    def _check_text(self):
        try:
            ratio_threshold = float(self.ratio_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid ratio value")
            return
        
        terms_content = self.terms_text.get('1.0', 'end-1c')
        text_content = self.text_widget.get('1.0', 'end-1c')
        
        if not terms_content.strip():
            messagebox.showwarning("Warning", "Terms list is empty")
            return
        
        if not text_content.strip():
            messagebox.showwarning("Warning", "Text is empty")
            return
        
        terms = [t.strip() for t in terms_content.split('\n') if t.strip()]
        lines = text_content.split('\n')
        
        self.results = []
        self.resolved_items = set()
        
        for line_num, line in enumerate(lines, 1):
            words_in_line = re.finditer(r'\b[\w\-]+\b', line)
            
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
                        
                        self.results.append({
                            'line': line_num,
                            'term': term,
                            'found': word,
                            'ratio': ratio,
                            'context': context
                        })
        
        self._update_results_list()
        
        if not self.results:
            messagebox.showinfo("Results", "No potential typos found")
    
    def _update_results_list(self):
        self.results_listbox.delete(0, tk.END)
        
        for idx, result in enumerate(self.results):
            if idx not in self.resolved_items:
                display = f"Line {result['line']}: '{result['found']}' → '{result['term']}' ({result['ratio']:.0f}%)"
                self.results_listbox.insert(tk.END, display)
                self.results_listbox.itemconfig(tk.END, {'fg': 'black'})
    
    def _on_result_select(self, event=None):
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
                line_num = result['line']
                self.text_widget.see(f"{line_num}.0")
                self.text_widget.tag_remove('highlight', '1.0', tk.END)
                self.text_widget.tag_add('highlight', f"{line_num}.0", f"{line_num}.end")
                self.text_widget.tag_config('highlight', background='yellow')
    
    def _mark_resolved(self):
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


if __name__ == "__main__":
    root = tk.Tk()
    app = FuzzyCheckerApp(root)
    root.mainloop()