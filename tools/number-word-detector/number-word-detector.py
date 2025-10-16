"""
Number Word Detector - Desktop Application
Detects written numbers in text across multiple languages.

Installation:
pip install num2words

To run:
python number-word-detector.py
"""

import tkinter as tk
from tkinter import ttk
import re
from num2words import num2words


class NumberDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Number Word Detector")
        self.root.geometry("1000x750")
        self.root.minsize(800, 600)
        
        # Material Design Colors
        self.colors = {
            'primary': '#2196F3',
            'primary_dark': '#1976D2',
            'accent': '#FF5722',
            'text': '#212121',
            'text_secondary': '#757575',
            'bg': '#FFFFFF',
            'bg_light': '#f5f5f5',
            'highlight': '#FFF9C4'
        }
        
        # Supported languages
        self.languages = {
            'English (US)': 'en',
            'Portuguese (BR)': 'pt_BR'
        }
        
        self.current_lang = tk.StringVar(value='English (US)')
        self.number_dict_cache = {}
        
        self.setup_ui()
        self.generate_number_dictionary()
        
    def setup_ui(self):
        """Create the user interface."""
        self.root.configure(bg=self.colors['bg_light'])
        
        # Header
        self.create_header()
        
        # Main container with grid layout
        main_container = tk.Frame(self.root, bg=self.colors['bg_light'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Configure grid weights for resizing
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_rowconfigure(1, weight=0)
        main_container.grid_rowconfigure(2, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Input section
        self.create_input_section(main_container)
        
        # Control section
        self.create_control_section(main_container)
        
        # Output section
        self.create_output_section(main_container)
        
    def create_header(self):
        """Create the header with title and language selector."""
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Title and language selector container
        header_content = tk.Frame(header_frame, bg=self.colors['primary'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Title
        title_label = tk.Label(
            header_content,
            text="🔍 Number Word Detector",
            font=("Segoe UI", 20, "bold"),
            bg=self.colors['primary'],
            fg="white"
        )
        title_label.pack(side=tk.LEFT, pady=20)
        
        # Language selector frame
        lang_frame = tk.Frame(header_content, bg=self.colors['primary'])
        lang_frame.pack(side=tk.RIGHT, pady=20)
        
        lang_label = tk.Label(
            lang_frame,
            text="Language:",
            font=("Segoe UI", 10),
            bg=self.colors['primary'],
            fg="white"
        )
        lang_label.pack(side=tk.LEFT, padx=(0, 10))
        
        style = ttk.Style()
        style.configure('Custom.TCombobox', fieldbackground='white')
        
        self.lang_dropdown = ttk.Combobox(
            lang_frame,
            textvariable=self.current_lang,
            values=list(self.languages.keys()),
            state='readonly',
            width=18,
            font=("Segoe UI", 9),
            style='Custom.TCombobox'
        )
        self.lang_dropdown.pack(side=tk.LEFT)
        self.lang_dropdown.bind('<<ComboboxSelected>>', self.on_language_change)
        
    def create_input_section(self, parent):
        """Create the input text section."""
        input_card = tk.Frame(parent, bg=self.colors['bg'], relief=tk.FLAT, bd=2)
        input_card.grid(row=0, column=0, sticky='nsew', pady=(0, 10))
        
        # Configure grid
        input_card.grid_rowconfigure(1, weight=1)
        input_card.grid_columnconfigure(0, weight=1)
        
        # Label
        input_label = tk.Label(
            input_card,
            text="Input Text:",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            anchor="w"
        )
        input_label.grid(row=0, column=0, sticky='w', padx=15, pady=(15, 5))
        
        # Text widget with scrollbar
        text_frame = tk.Frame(input_card, bg=self.colors['bg'])
        text_frame.grid(row=1, column=0, sticky='nsew', padx=15, pady=(0, 15))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        # Scrollbar
        scrollbar_input = tk.Scrollbar(text_frame)
        scrollbar_input.grid(row=0, column=1, sticky='ns')
        
        # Text widget
        self.input_text = tk.Text(
            text_frame,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            relief=tk.FLAT,
            bg=self.colors['bg'],
            fg=self.colors['text'],
            insertbackground=self.colors['primary'],
            selectbackground=self.colors['primary'],
            selectforeground="white",
            yscrollcommand=scrollbar_input.set
        )
        self.input_text.grid(row=0, column=0, sticky='nsew')
        scrollbar_input.config(command=self.input_text.yview)
        
        # Sample text
        sample_text = "I bought three apples and five oranges at the market. The event gathered one thousand people and lasted two hours. Zero problems, one hundred solutions! There were three hundred and forty-two registrants."
        self.input_text.insert("1.0", sample_text)
        
    def create_control_section(self, parent):
        """Create the control section with analyze button."""
        control_frame = tk.Frame(parent, bg=self.colors['bg_light'])
        control_frame.grid(row=1, column=0, sticky='ew', pady=10)
        
        # Analyze button
        self.analyze_btn = tk.Button(
            control_frame,
            text="ANALYZE TEXT",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors['primary'],
            fg="white",
            activebackground=self.colors['primary_dark'],
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=40,
            pady=12,
            command=self.analyze_text
        )
        self.analyze_btn.pack()
        
        # Hover effect
        self.analyze_btn.bind("<Enter>", lambda e: self.analyze_btn.config(bg=self.colors['primary_dark']))
        self.analyze_btn.bind("<Leave>", lambda e: self.analyze_btn.config(bg=self.colors['primary']))
        
    def create_output_section(self, parent):
        """Create the output section with results."""
        output_card = tk.Frame(parent, bg=self.colors['bg'], relief=tk.FLAT, bd=2)
        output_card.grid(row=2, column=0, sticky='nsew')
        
        # Configure grid
        output_card.grid_rowconfigure(1, weight=2)
        output_card.grid_rowconfigure(3, weight=1)
        output_card.grid_columnconfigure(0, weight=1)
        
        # Header
        header_frame = tk.Frame(output_card, bg=self.colors['bg'])
        header_frame.grid(row=0, column=0, sticky='ew', padx=15, pady=(15, 5))
        
        result_label = tk.Label(
            header_frame,
            text="Highlighted Text:",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            anchor="w"
        )
        result_label.pack(side=tk.LEFT)
        
        self.counter_label = tk.Label(
            header_frame,
            text="0 numbers found",
            font=("Segoe UI", 9),
            bg=self.colors['bg'],
            fg=self.colors['text_secondary'],
            anchor="e"
        )
        self.counter_label.pack(side=tk.RIGHT)
        
        # Highlighted text area
        text_result_frame = tk.Frame(output_card, bg=self.colors['bg'])
        text_result_frame.grid(row=1, column=0, sticky='nsew', padx=15, pady=(0, 10))
        text_result_frame.grid_rowconfigure(0, weight=1)
        text_result_frame.grid_columnconfigure(0, weight=1)
        
        scrollbar_result = tk.Scrollbar(text_result_frame)
        scrollbar_result.grid(row=0, column=1, sticky='ns')
        
        self.output_text = tk.Text(
            text_result_frame,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
            relief=tk.FLAT,
            bg=self.colors['bg'],
            fg=self.colors['text'],
            state=tk.DISABLED,
            yscrollcommand=scrollbar_result.set
        )
        self.output_text.grid(row=0, column=0, sticky='nsew')
        scrollbar_result.config(command=self.output_text.yview)
        
        # Configure highlight tag
        self.output_text.tag_configure(
            "number",
            background=self.colors['highlight'],
            foreground=self.colors['accent'],
            font=("Segoe UI", 10, "bold")
        )
        
        # Numbers list label
        list_label = tk.Label(
            output_card,
            text="Numbers Found:",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors['bg'],
            fg=self.colors['text'],
            anchor="w"
        )
        list_label.grid(row=2, column=0, sticky='w', padx=15, pady=(10, 5))
        
        # Numbers list
        list_frame = tk.Frame(output_card, bg=self.colors['bg'])
        list_frame.grid(row=3, column=0, sticky='nsew', padx=15, pady=(0, 15))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        scrollbar_list = tk.Scrollbar(list_frame)
        scrollbar_list.grid(row=0, column=1, sticky='ns')
        
        self.numbers_list = tk.Listbox(
            list_frame,
            font=("Segoe UI", 9),
            bg=self.colors['bg_light'],
            fg=self.colors['text'],
            relief=tk.FLAT,
            selectbackground=self.colors['primary'],
            selectforeground="white",
            yscrollcommand=scrollbar_list.set
        )
        self.numbers_list.grid(row=0, column=0, sticky='nsew')
        scrollbar_list.config(command=self.numbers_list.yview)
        
    def generate_number_dictionary(self, max_num=1000):
        """Generate dictionary of number words using num2words."""
        lang_code = self.languages[self.current_lang.get()]
        
        if lang_code in self.number_dict_cache:
            return
        
        numbers_set = set()
        
        # Generate numbers from 0 to max_num
        for i in range(max_num + 1):
            try:
                text_num = num2words(i, lang=lang_code)
                numbers_set.add(text_num.lower())
                # Add individual words from compound numbers
                words = re.findall(r'\b\w+\b', text_num.lower())
                numbers_set.update(words)
            except:
                pass
        
        # Add specific large numbers
        for num in [1000, 10000, 100000, 1000000, 1000000000]:
            try:
                text_num = num2words(num, lang=lang_code)
                numbers_set.add(text_num.lower())
                words = re.findall(r'\b\w+\b', text_num.lower())
                numbers_set.update(words)
            except:
                pass
        
        # Remove common connectors
        connectors = {'and', 'e', 'de', 'a', 'o', 'the', 'of'}
        numbers_set = numbers_set - connectors
        
        self.number_dict_cache[lang_code] = list(numbers_set)
        
    def find_number_words(self, text):
        """Find all number words in the text."""
        lang_code = self.languages[self.current_lang.get()]
        number_words = self.number_dict_cache.get(lang_code, [])
        
        if not number_words:
            return []
        
        pattern = r'\b(' + '|'.join(re.escape(n) for n in number_words) + r')\b'
        occurrences = []
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            occurrences.append({
                'text': match.group(),
                'start': match.start(),
                'end': match.end()
            })
        
        return occurrences
    
    def convert_word_to_number(self, word):
        """Try to convert a number word to its numeric value."""
        lang_code = self.languages[self.current_lang.get()]
        word_lower = word.lower()
        
        # Try numbers up to 1000
        for i in range(1001):
            try:
                if num2words(i, lang=lang_code).lower() == word_lower:
                    return i
            except:
                pass
        
        return None
    
    def analyze_text(self):
        """Analyze the input text and display results."""
        text = self.input_text.get("1.0", tk.END).strip()
        
        if not text:
            return
        
        # Find number words
        occurrences = self.find_number_words(text)
        
        # Update counter
        count = len(occurrences)
        self.counter_label.config(
            text=f"{count} number{'s' if count != 1 else ''} found"
        )
        
        # Clear previous results
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        
        # Display highlighted text
        if occurrences:
            last_pos = 0
            for oc in occurrences:
                # Text before the number
                self.output_text.insert(tk.END, text[last_pos:oc['start']])
                # Highlighted number
                self.output_text.insert(tk.END, oc['text'], "number")
                last_pos = oc['end']
            
            # Remaining text
            self.output_text.insert(tk.END, text[last_pos:])
        else:
            self.output_text.insert(tk.END, text)
        
        self.output_text.config(state=tk.DISABLED)
        
        # Update numbers list
        self.numbers_list.delete(0, tk.END)
        unique_numbers = {}
        numeric_values = {}
        
        for oc in occurrences:
            num_word = oc['text'].lower()
            unique_numbers[num_word] = unique_numbers.get(num_word, 0) + 1
            
            if num_word not in numeric_values:
                numeric_values[num_word] = self.convert_word_to_number(num_word)
        
        for num_word, count in sorted(unique_numbers.items()):
            value = numeric_values.get(num_word)
            if value is not None:
                self.numbers_list.insert(tk.END, f"  • '{num_word}' = {value} - {count}x")
            else:
                self.numbers_list.insert(tk.END, f"  • '{num_word}' - {count}x")
    
    def on_language_change(self, event=None):
        """Handle language selection change."""
        self.generate_number_dictionary()
        
        # Update sample text based on language
        lang_code = self.languages[self.current_lang.get()]
        
        if lang_code == 'pt_BR':
            sample_text = "Comprei três maçãs e cinco laranjas no mercado. O evento reuniu mil pessoas e durou duas horas. Zero problemas, cem soluções! Foram trezentos e quarenta e dois inscritos."
        else:
            sample_text = "I bought three apples and five oranges at the market. The event gathered one thousand people and lasted two hours. Zero problems, one hundred solutions! There were three hundred and forty-two registrants."
        
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", sample_text)
        
        # Clear results
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)
        self.numbers_list.delete(0, tk.END)
        self.counter_label.config(text="0 numbers found")


def main():
    root = tk.Tk()
    app = NumberDetectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()