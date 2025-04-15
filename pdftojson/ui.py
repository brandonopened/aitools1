import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import sys
import io
import subprocess
import json
import threading
import importlib

# Dynamically import the required module
try:
    json_to_word = importlib.import_module("json_to_word")
except ImportError:
    json_to_word = None
    print("Error: Could not import json_to_word.py. Make sure it's in the same directory.", file=sys.stderr)

class JsonProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON to Document Processor")
        self.root.geometry("1000x700")
        self.json_file_path = None
        self.processing_module = json_to_word # Directly assign the module
        self.output_docx = "preschool_curriculum.docx" # Simplified filename
        self.output_pdf = "preschool_curriculum.pdf"  # Simplified filename

        # --- Main Layout ---
        main_pane = tk.PanedWindow(root, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_pane = tk.PanedWindow(main_pane, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_pane.add(top_pane, stretch="always")

        bottom_frame = tk.Frame(main_pane, bd=2, relief=tk.GROOVE)
        main_pane.add(bottom_frame, stretch="never")

        # --- Left Control Panel ---
        control_frame = tk.Frame(top_pane, bd=2, relief=tk.GROOVE, width=250)
        top_pane.add(control_frame, stretch="never")
        control_frame.pack_propagate(False)

        tk.Label(control_frame, text="Controls", font=("Arial", 14, "bold")).pack(pady=10)

        self.load_button = tk.Button(control_frame, text="Load JSON and Process", command=self.load_and_process_thread)
        self.load_button.pack(pady=20, padx=10, fill=tk.X)

        self.json_file_label = tk.Label(control_frame, text="No JSON loaded", wraplength=200)
        self.json_file_label.pack(pady=5, padx=10)

        # --- Center Preview Panel ---
        preview_frame = tk.Frame(top_pane, bd=2, relief=tk.GROOVE)
        top_pane.add(preview_frame, stretch="always")

        tk.Label(preview_frame, text="Preview", font=("Arial", 14, "bold")).pack(pady=10)
        self.preview_text = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.preview_text.configure(state='disabled')

        # --- Right Output Panel ---
        output_frame = tk.Frame(top_pane, bd=2, relief=tk.GROOVE, width=250)
        top_pane.add(output_frame, stretch="never")
        output_frame.pack_propagate(False)

        tk.Label(output_frame, text="Generated Files", font=("Arial", 14, "bold")).pack(pady=10)
        self.output_list_frame = tk.Frame(output_frame)
        self.output_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # --- Bottom Log Panel ---
        bottom_frame.pack_propagate(False)
        bottom_frame.configure(height=200)

        tk.Label(bottom_frame, text="Logs / Status", font=("Arial", 14, "bold")).pack(pady=5)
        self.log_text = scrolledtext.ScrolledText(bottom_frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_text.configure(state='disabled')

        # Redirect stdout
        sys.stdout = self.TextRedirector(self.log_text, "stdout")
        sys.stderr = self.TextRedirector(self.log_text, "stderr")

        # Initial setup
        self.update_output_panel() # Update buttons if files already exist


    def log(self, message):
        print(message)

    def display_preview(self, text):
        self.preview_text.configure(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert(tk.END, text)
        self.preview_text.configure(state='disabled')

    def update_output_panel(self):
        for widget in self.output_list_frame.winfo_children():
            widget.destroy()

        if os.path.exists(self.output_docx):
            docx_button = tk.Button(self.output_list_frame, text=f"Open {os.path.basename(self.output_docx)}", 
                                    command=lambda p=self.output_docx: self.open_file(p))
            docx_button.pack(pady=5, padx=5, fill=tk.X)

        if os.path.exists(self.output_pdf):
            pdf_button = tk.Button(self.output_list_frame, text=f"Open {os.path.basename(self.output_pdf)}", 
                                   command=lambda p=self.output_pdf: self.open_file(p))
            pdf_button.pack(pady=5, padx=5, fill=tk.X)

    def load_and_process_thread(self):
        if not self.processing_module:
            messagebox.showerror("Module Error", "Could not load json_to_word.py. Processing cannot continue.")
            return
        self.load_button.config(state=tk.DISABLED)
        self.log("Starting processing...")
        thread = threading.Thread(target=self.load_and_process)
        thread.start()

    def load_and_process(self):
        try:
            # Ensure module is loaded
            if not self.processing_module:
                self.log("Error: json_to_word.py module is not loaded.")
                return # Should have been caught in thread start, but double-check

            # 1. Select JSON file (if not already loaded)
            if not self.json_file_path:
                file_path = filedialog.askopenfilename(
                    title="Select JSON file",
                    initialdir=os.getcwd(),
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    initialfile="craft_data.json"
                )
                if not file_path:
                    self.log("File selection cancelled.")
                    return
                self.json_file_path = file_path
                self.json_file_label.config(text=f"Loaded: {os.path.basename(file_path)}")
            
            self.log(f"Loading JSON from: {self.json_file_path}")

            # 2. Load JSON data
            try:
                with open(self.json_file_path, "r") as f:
                    data = json.load(f)
                self.log("JSON data loaded successfully.")
            except Exception as e:
                self.log(f"Error loading JSON: {e}")
                messagebox.showerror("JSON Load Error", f"Failed to load JSON file: {e}")
                self.json_file_path = None
                self.json_file_label.config(text="No JSON loaded")
                return

            # 3. Generate and display preview
            self.log("Generating preview...")
            try:
                preview_content = self.processing_module.generate_text_preview(data)
                self.display_preview(preview_content)
                self.log("Preview generated.")
            except AttributeError:
                 self.log("Error: 'generate_text_preview' function not found in json_to_word.py")
                 messagebox.showerror("Preview Error", "Function 'generate_text_preview' not found in json_to_word.py.")
            except Exception as e:
                 self.log(f"Error generating preview: {e}")
                 messagebox.showerror("Preview Error", f"Failed to generate preview: {e}")

            # 4. Call export functions
            self.log(f"Starting Word export to {self.output_docx}...")
            try:
                self.processing_module.export_to_word(data, self.output_docx)
            except AttributeError:
                self.log("Error: 'export_to_word' function not found in json_to_word.py")
                messagebox.showerror("Word Export Error", "Function 'export_to_word' not found in json_to_word.py.")
            except Exception as e:
                self.log(f"Error during Word export: {e}")
                messagebox.showerror("Word Export Error", f"Failed to export to Word: {e}")

            self.log(f"Starting PDF export to {self.output_pdf}...")
            try:
                self.processing_module.export_to_pdf(data, self.output_pdf)
            except AttributeError:
                self.log("Error: 'export_to_pdf' function not found in json_to_word.py")
                messagebox.showerror("PDF Export Error", "Function 'export_to_pdf' not found in json_to_word.py.")
            except Exception as e:
                self.log(f"Error during PDF export: {e}")
                messagebox.showerror("PDF Export Error", f"Failed to export to PDF: {e}")

            # 5. Update output panel
            self.update_output_panel()
            self.log("Processing finished.")

        except Exception as e:
            self.log(f"An unexpected error occurred: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        finally:
            self.load_button.config(state=tk.NORMAL)


    def open_file(self, file_path):
        try:
            if not os.path.exists(file_path):
                self.log(f"Error: File not found - {file_path}")
                messagebox.showerror("File Not Found", f"The file could not be found:\n{os.path.abspath(file_path)}")
                return
                
            abs_path = os.path.abspath(file_path)
            if sys.platform == "win32":
                os.startfile(abs_path)
            elif sys.platform == "darwin": # macOS
                subprocess.Popen(["open", abs_path])
            else: # Linux variants
                subprocess.Popen(["xdg-open", abs_path])
            self.log(f"Attempting to open: {abs_path}")
        except Exception as e:
            self.log(f"Error opening file {file_path}: {e}")
            messagebox.showerror("Error", f"Could not open file: {file_path}\n{e}")

    # Class to redirect stdout/stderr to the tkinter text widget
    class TextRedirector(io.TextIOBase):
        def __init__(self, widget, tag="stdout"):
            self.widget = widget
            self.tag = tag

        def write(self, str):
            self.widget.after(0, self._write_to_widget, str)
            return len(str)

        def _write_to_widget(self, str):
            self.widget.configure(state='normal')
            self.widget.insert(tk.END, str, (self.tag,))
            self.widget.see(tk.END)
            self.widget.configure(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    app = JsonProcessorApp(root)
    # Check if module loaded before starting mainloop
    if not app.processing_module:
         messagebox.showerror("Startup Error", "Failed to load json_to_word.py. Please ensure the file exists.")
         # Optionally destroy root window or exit
         # root.destroy()
         # sys.exit(1)
    else:
        root.mainloop() 