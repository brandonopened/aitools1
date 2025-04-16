import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import pandas as pd
from tkinter import ttk
import threading
import sys

import xls_to_word_activities

class TextRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        if string:
            def append():
                self.text_widget.insert(tk.END, string)
                self.text_widget.see(tk.END)
            self.text_widget.after(0, append)

    def flush(self):
        pass

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("Excel to Word Activity Generator")
        self.pack(fill=tk.BOTH, expand=True)
        self.create_widgets()

    def create_widgets(self):
        # Frame for file selection
        file_frame = tk.Frame(self)
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(file_frame, text="Excel File:").grid(row=0, column=0, sticky=tk.W)
        self.excel_path_var = tk.StringVar()
        self.excel_entry = tk.Entry(file_frame, textvariable=self.excel_path_var, width=50)
        self.excel_entry.grid(row=0, column=1, padx=5)
        tk.Button(file_frame, text="Browse...", command=self.browse_excel).grid(row=0, column=2)

        tk.Label(file_frame, text="Output Word File:").grid(row=1, column=0, sticky=tk.W)
        self.output_path_var = tk.StringVar()
        self.output_entry = tk.Entry(file_frame, textvariable=self.output_path_var, width=50)
        self.output_entry.grid(row=1, column=1, padx=5)
        tk.Button(file_frame, text="Browse...", command=self.browse_output).grid(row=1, column=2)

        # Sheet selection:
        # Label and dropdown for selecting a sheet from the Excel file
        tk.Label(file_frame, text="Sheet:").grid(row=2, column=0, sticky=tk.W)
        self.sheet_var = tk.StringVar()
        # Use Combobox for sheet names; will be populated after loading file
        self.sheet_menu = ttk.Combobox(file_frame, textvariable=self.sheet_var, state="readonly", values=[])
        self.sheet_menu.grid(row=2, column=1, padx=5, sticky=tk.W)
        self.sheet_menu.bind('<<ComboboxSelected>>', self.on_sheet_select)

        # Placeholder frame for displaying the Excel sheet data
        self.tree_frame = tk.Frame(self)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Run button
        self.run_button = tk.Button(self, text="Generate Activities", command=self.run_script)
        self.run_button.pack(pady=5)

        # Text area for logs
        self.log_text = scrolledtext.ScrolledText(self, wrap=tk.WORD, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def browse_excel(self):
        filetypes = [
            ("Excel files", "*.xlsx"),
            ("All files", "*.*")
        ]
        path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=filetypes,
            initialdir="."
        )
        if path:
            self.excel_path_var.set(path)
            # Load sheet names from the selected Excel file
            try:
                xls = pd.ExcelFile(path)
                sheets = xls.sheet_names
                # Populate sheet selection dropdown
                self.sheet_menu['values'] = sheets
                if sheets:
                    # Select the first sheet by default and load it
                    self.sheet_var.set(sheets[0])
                    self.load_sheet(path, sheets[0])
            except Exception as e:
                messagebox.showerror("Error loading Excel file", str(e))

    def browse_output(self):
        filetypes = [
            ("Word files", "*.docx"),
            ("All files", "*.*")
        ]
        path = filedialog.asksaveasfilename(
            title="Save Word Document",
            defaultextension=".docx",
            filetypes=filetypes,
            initialdir="."
        )
        if path:
            self.output_path_var.set(path)
    
    def on_sheet_select(self, event):
        """Handle sheet selection change: load and display the selected sheet."""
        excel_path = self.excel_path_var.get().strip()
        sheet = self.sheet_var.get()
        if excel_path and sheet:
            self.load_sheet(excel_path, sheet)

    def load_sheet(self, excel_path, sheet_name):
        """Load the specified sheet into a DataFrame and display it."""
        try:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            self.current_df = df
            self.display_dataframe(df)
        except Exception as e:
            messagebox.showerror("Error loading sheet", str(e))

    def display_dataframe(self, df):
        """Display a pandas DataFrame in a Treeview within the tree_frame."""
        # Clear previous contents
        for widget in self.tree_frame.winfo_children():
            widget.destroy()
        # Prepare columns
        cols = list(df.columns)
        # Create Treeview widget
        tree = ttk.Treeview(self.tree_frame, columns=cols, show='headings')
        # Scrollbars
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        # Grid placement
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        # Configure resizing
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        # Setup headings and columns
        for col in cols:
            tree.heading(col, text=str(col))
            tree.column(col, width=100, anchor='center')
        # Insert data rows
        for _, row in df.iterrows():
            tree.insert('', tk.END, values=[row[col] for col in cols])

    def run_script(self):
        excel_path = self.excel_path_var.get().strip()
        output_path = self.output_path_var.get().strip()
        if not excel_path:
            messagebox.showwarning("Input required", "Please select an Excel file.")
            return
        if not output_path:
            messagebox.showwarning("Output required", "Please specify an output Word file.")
            return
        # Disable button
        self.run_button.config(state=tk.DISABLED)
        self.log_text.delete(1.0, tk.END)
        # Start thread
        thread = threading.Thread(target=self.worker, args=(excel_path, output_path), daemon=True)
        thread.start()

    def worker(self, excel_path, output_path):
        # Redirect stdout and stderr
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text)
        try:
            xls_to_word_activities.main(excel_path, output_path)
            message = f"\n\nAll activities generated.\nDocument saved to: {output_path}\n"
            sys.stdout.write(message)
        except Exception as e:
            sys.stderr.write(f"\nError: {str(e)}\n")
        finally:
            # Restore stdout and stderr
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            # Re-enable button in main thread
            def enable_button():
                self.run_button.config(state=tk.NORMAL)
            self.log_text.after(0, enable_button)

def main():
    root = tk.Tk()
    root.geometry("800x600")
    app = Application(master=root)
    app.mainloop()

if __name__ == "__main__":
    main()