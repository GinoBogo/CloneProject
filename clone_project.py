#!/usr/bin/env python3
"""
Utility to clone a project via CLI or Tkinter GUI. This script allows users to
duplicate a project, replacing specific names within file contents and
filenames.

Author: Gino Bogo
"""

import os
import shutil
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================


DEFAULT_WINDOW_SIZE = (600, 600)
LABEL_WIDTH = 20
ENTRY_WIDTH = 50
BUTTON_WIDTH = 10


# ==============================================================================
# CORE FUNCTIONALITY
# ==============================================================================


def replace_in_contents(file_path, src_name, dst_name, logger):
    """Replace text content in a file, skipping binary/unreadable files."""
    try:
        with open(file_path, "rb") as f:  # Open in binary mode
            content_bytes = f.read()

        # Heuristic: if null byte is present, assume binary
        if b"\x00" in content_bytes:
            logger(f"Skipped file (likely binary): {file_path}")
            return

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger(f"Skipped file (not UTF-8 decodable): {file_path}")
            return

        updated_content = content.replace(src_name, dst_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

        logger(f"Updated contents of: {file_path}")
    except IOError:  # Catch other IO errors
        logger(f"Skipped file (IO Error): {file_path}")


def copy_and_replace(src_dir, dst_dir, src_name, dst_name, logger):
    """Copy directory structure while replacing names in contents and filenames."""
    for root, dirs, files in os.walk(src_dir, topdown=True):
        # Replace directory names in path
        new_root = re.sub(
            re.escape(src_name), dst_name, str(root).replace(str(src_dir), str(dst_dir))
        )
        os.makedirs(new_root, exist_ok=True)

        # Replace file names and copy files
        for file in files:
            src_file_path = os.path.join(root, file)
            new_file_name = re.sub(re.escape(src_name), dst_name, file)
            dst_file_path = os.path.join(new_root, new_file_name)

            shutil.copy2(src_file_path, dst_file_path)
            replace_in_contents(dst_file_path, src_name, dst_name, logger)

        # Replace subdirectory names
        for dir in dirs:
            new_dir_name = re.sub(re.escape(src_name), dst_name, dir)
            os.makedirs(os.path.join(new_root, new_dir_name), exist_ok=True)


# ==============================================================================
# VALIDATION & HELPER FUNCTIONS
# ==============================================================================


def validate_inputs(src_dir, dst_dir, src_name, dst_name):
    """Validate all input parameters."""
    if not all([src_dir, dst_dir, src_name, dst_name]):
        raise ValueError("All fields are required.")

    if not os.path.isdir(src_dir):
        raise ValueError(f"Source directory '{src_dir}' not found.")

    if src_name == dst_name and src_dir == dst_dir:
        raise ValueError(
            "Source and destination directories must be different if "
            "source and destination names are identical."
        )


def show_help():
    """Display CLI usage information."""
    print("Usage: python clone_project.py <src_dir> <dst_dir> <src_name> <dst_name>")
    sys.exit(1)


# ==============================================================================
# GUI IMPLEMENTATION
# ==============================================================================


class CloneProjectGUI:
    """Tkinter GUI for the clone project utility."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Clone Project")
        self.root.minsize(*DEFAULT_WINDOW_SIZE)

        self.setup_ui()

    def setup_ui(self):
        """Initialize all GUI components."""
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input fields
        self.setup_input_fields(main_frame)

        # Control buttons
        self.setup_buttons(main_frame)

        # Log output
        self.setup_log_area(main_frame)

        # Layout configuration
        self.configure_layout(main_frame)

    def setup_input_fields(self, parent):
        """Create and arrange input fields with labels."""
        # Source directory
        tk.Label(parent, text="Source Directory:", width=LABEL_WIDTH, anchor="e").grid(
            row=0, column=0, sticky="e"
        )
        self.src_entry = tk.Entry(parent, width=ENTRY_WIDTH)
        self.src_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")

        # Destination directory
        tk.Label(
            parent, text="Destination Directory:", width=LABEL_WIDTH, anchor="e"
        ).grid(row=1, column=0, sticky="e")
        self.dst_entry = tk.Entry(parent, width=ENTRY_WIDTH)
        self.dst_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")

        # Source name
        tk.Label(parent, text="Source Name:", width=LABEL_WIDTH, anchor="e").grid(
            row=2, column=0, sticky="e"
        )
        self.src_name_entry = tk.Entry(parent, width=ENTRY_WIDTH)
        self.src_name_entry.grid(row=2, column=1, padx=5, pady=5, sticky="we")

        # Destination name
        tk.Label(parent, text="Destination Name:", width=LABEL_WIDTH, anchor="e").grid(
            row=3, column=0, sticky="e"
        )
        self.dst_name_entry = tk.Entry(parent, width=ENTRY_WIDTH)
        self.dst_name_entry.grid(row=3, column=1, padx=5, pady=5, sticky="we")

    def setup_buttons(self, parent):
        """Create control buttons."""
        # Browse Source button
        tk.Button(
            parent,
            text="Browse",
            command=lambda: self.browse_dir(self.src_entry),
            width=BUTTON_WIDTH,
            bg="#0078D7",
            fg="#FFFFFF",
            cursor="hand2",
        ).grid(row=0, column=2, padx=5, pady=5)

        # Browse Destination button
        tk.Button(
            parent,
            text="Browse",
            command=lambda: self.browse_dir(self.dst_entry),
            width=BUTTON_WIDTH,
            bg="#0078D7",
            fg="#FFFFFF",
            cursor="hand2",
        ).grid(row=1, column=2, padx=5, pady=5)

        # Clone Project button
        tk.Button(
            parent,
            text="Clone Project",
            command=self.run_clone,
            bg="#FFFF00",
            fg="#000000",
            cursor="hand2",
        ).grid(row=4, column=0, columnspan=3, pady=(10, 5), sticky="we")

    def setup_log_area(self, parent):
        """Create logging text area with scrollbar."""
        self.log_text = tk.Text(
            parent, height=10, state="disabled", wrap="none"
        )
        self.log_text.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="nsew")

        # Horizontal scrollbar
        x_scrollbar = tk.Scrollbar(
            parent, orient=tk.HORIZONTAL, command=self.log_text.xview
        )
        x_scrollbar.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.log_text.configure(xscrollcommand=x_scrollbar.set)

        # Vertical scrollbar
        y_scrollbar = tk.Scrollbar(parent, command=self.log_text.yview)
        y_scrollbar.grid(row=5, column=3, sticky="ns")
        self.log_text.configure(yscrollcommand=y_scrollbar.set)

    def configure_layout(self, parent):
        """Configure grid weights for responsive layout."""
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(5, weight=1)

    def browse_dir(self, entry_widget):
        """Open directory browser and update entry field."""
        path = filedialog.askdirectory()
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def gui_logger(self, message):
        """Log messages to the GUI text area."""
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def run_clone(self):
        """Execute the clone operation from GUI inputs."""
        try:
            src_dir = os.path.abspath(self.src_entry.get().strip())
            dst_dir = os.path.abspath(self.dst_entry.get().strip())
            src_name = self.src_name_entry.get().strip()
            dst_name = self.dst_name_entry.get().strip()

            validate_inputs(src_dir, dst_dir, src_name, dst_name)

            # Handle existing destination
            if os.path.exists(dst_dir):
                overwrite = messagebox.askyesno(
                    "Destination exists",
                    f"Destination '{dst_dir}' already exists. Overwrite?",
                )
                if not overwrite:
                    return
                shutil.rmtree(dst_dir)

            # Perform clone operation
            self.gui_logger("Copying and replacing...")
            copy_and_replace(src_dir, dst_dir, src_name, dst_name, self.gui_logger)
            self.gui_logger(
                f"Operation completed successfully. New project location: {dst_dir}"
            )
            messagebox.showinfo("Success", "Project cloned successfully.")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


def run_gui():
    """Launch the GUI interface."""
    app = CloneProjectGUI()
    app.run()


# ==============================================================================
# CLI IMPLEMENTATION
# ==============================================================================


def cli_logger(message):
    """Simple logger for CLI mode."""
    print(message)


def run_cli():
    """Execute the clone operation in CLI mode."""
    if len(sys.argv) != 5:
        cli_logger("Error: Invalid number of arguments")
        show_help()
        sys.exit(1)
        return  # Ensure function exits after sys.exit(1)

    src_dir = os.path.abspath(sys.argv[1])
    dst_dir = os.path.abspath(sys.argv[2])
    src_name = sys.argv[3]
    dst_name = sys.argv[4]
    try:
        validate_inputs(src_dir, dst_dir, src_name, dst_name)
    except ValueError as e:
        cli_logger(f"Error: {e}")
        sys.exit(1)

    # Handle existing destination
    if os.path.exists(dst_dir):
        cli_logger(
            f"Warning: Destination directory '{dst_dir}' already exists. "
            f"Overwriting..."
        )
        shutil.rmtree(dst_dir)

    # Perform clone operation
    cli_logger("Copying and replacing...")
    copy_and_replace(src_dir, dst_dir, src_name, dst_name, cli_logger)
    cli_logger(f"Operation completed successfully. New project location: {dst_dir}")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - run GUI
        run_gui()
    else:
        # CLI arguments provided - run CLI mode
        run_cli()
