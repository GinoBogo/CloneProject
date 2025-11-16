#!/usr/bin/env python3
"""
Utility to clone a project via CLI or Tkinter GUI. This script allows users to
duplicate a project, replacing specific names within file contents and
filenames.

Author: Gino Bogo
"""

import os
import re
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


# ==============================================================================
# CONSTANTS
# ==============================================================================

DEFAULT_WINDOW_SIZE = (600, 600)
LABEL_WIDTH = 20
ENTRY_WIDTH = 50
BUTTON_WIDTH = 10


# ==============================================================================
# VALIDATION & HELPER FUNCTIONS
# ==============================================================================


def validate_inputs(src_dir, dst_dir, src_names, dst_names):
    """Validate all input parameters."""
    if not all([src_dir, dst_dir, src_names, dst_names]):
        raise ValueError("All fields are required.")

    if not os.path.isdir(src_dir):
        raise ValueError(f"Source directory '{src_dir}' not found.")

    if len(src_names) != len(dst_names):
        raise ValueError(
            "Number of source names must match number of destination names."
        )

    if src_dir == dst_dir:
        for src_name, dst_name in zip(src_names, dst_names):
            if src_name == dst_name:
                raise ValueError(
                    "Source and destination directories must be different if "
                    "any source and destination names are identical."
                )


def show_help():
    """Display CLI usage information."""
    print("Usage: python clone_project.py <src_dir> <dst_dir> <src_name> <dst_name>")
    sys.exit(1)


# ==============================================================================
# CORE FUNCTIONALITY
# ==============================================================================


def replace_in_contents(file_path, src_names, dst_names, logger):
    """Replace text content in a file, skipping binary/unreadable files."""
    total_replacements = 0
    try:
        with open(file_path, "rb") as f:  # Open in binary mode
            content_bytes = f.read()

        # Heuristic: if null byte is present, assume binary
        if b"\x00" in content_bytes:
            logger(f"Skipped file (likely binary): {file_path}", level="skipped")
            return 0

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger(f"Skipped file (not UTF-8 decodable): {file_path}", level="skipped")
            return 0

        updated_content = content
        for src_name, dst_name in zip(src_names, dst_names):
            replacements = updated_content.count(src_name)
            if replacements > 0:
                updated_content = updated_content.replace(src_name, dst_name)
                total_replacements += replacements

        if total_replacements > 0:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            normalized_file_path = os.path.normpath(file_path)
            logger(
                f"Updated contents of: {normalized_file_path} ({total_replacements} replacements)"
            )
        return total_replacements
    except IOError:
        logger(f"Skipped file (IO Error): {file_path}", level="skipped")
        return 0


def copy_and_replace(src_dir, dst_dir, src_names, dst_names, logger):
    """Copy directory structure while replacing names in contents and filenames."""
    folders_created = 0
    files_copied = 0
    words_replaced = 0

    for root, dirs, files in os.walk(src_dir, topdown=True):
        # Calculate the relative path from src_dir to the current root
        rel_path = os.path.relpath(root, src_dir)

        # Apply all name replacements to the relative path
        processed_rel_path = rel_path
        for src_name, dst_name in zip(src_names, dst_names):
            processed_rel_path = re.sub(
                re.escape(src_name), dst_name, processed_rel_path
            )

        # Construct the new root path in the destination
        new_root = os.path.join(dst_dir, processed_rel_path)

        if not os.path.exists(new_root):
            os.makedirs(new_root, exist_ok=True)
            folders_created += 1

        # Replace file names and copy files
        for file in files:
            src_file_path = os.path.join(root, file)
            new_file_name = file
            for src_name, dst_name in zip(src_names, dst_names):
                new_file_name = re.sub(re.escape(src_name), dst_name, new_file_name)
            dst_file_path = os.path.join(new_root, new_file_name)

            shutil.copy2(src_file_path, dst_file_path)
            files_copied += 1
            words_replaced += replace_in_contents(
                dst_file_path, src_names, dst_names, logger
            )

        # Replace subdirectory names in the 'dirs' list for os.walk to traverse correctly
        for i in range(len(dirs)):
            dir_name = dirs[i]
            new_dir_name = dir_name
            for src_name, dst_name in zip(src_names, dst_names):
                new_dir_name = re.sub(re.escape(src_name), dst_name, new_dir_name)

            # Note: The actual creation of the directory in the destination is
            # handled by the new_root logic in the next iteration of os.walk
            # when this renamed directory becomes the 'root'. We don't need to
            # explicitly create it here.

    return folders_created, files_copied, words_replaced


# ==============================================================================
# LOGGERS
# ==============================================================================


def cli_logger(message, level="normal"):
    """Simple logger for CLI mode."""
    print(message)


# ==============================================================================
# GUI IMPLEMENTATION
# ==============================================================================


class CloneProjectGUI:
    """Tkinter GUI for the clone project utility."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Clone Project")
        self.root.minsize(*DEFAULT_WINDOW_SIZE)

        # Initialize statistics variables
        self.directories_created = tk.StringVar(value="Directories: 0")
        self.files_changed = tk.StringVar(value="Files: 0")
        self.names_replaced = tk.StringVar(value="Names: 0")

        self.setup_ui()

    def setup_ui(self):
        """Initialize all GUI components."""
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Setup all UI components
        self.setup_input_fields(main_frame)
        self.setup_buttons(main_frame)
        self.setup_log_area(main_frame)
        self.setup_status_bar(main_frame)
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
        tk.Label(parent, text="Source Name(s):", width=LABEL_WIDTH, anchor="e").grid(
            row=2, column=0, sticky="e"
        )
        self.src_name_entry = tk.Entry(parent, width=ENTRY_WIDTH)
        self.src_name_entry.grid(row=2, column=1, padx=5, pady=5, sticky="we")

        # Destination name
        tk.Label(
            parent, text="Destination Name(s):", width=LABEL_WIDTH, anchor="e"
        ).grid(row=3, column=0, sticky="e")
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
        self.log_text = tk.Text(parent, height=10, state="disabled", wrap="none")
        self.log_text.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="nsew")

        # Configure text tags for different message levels
        self.log_text.tag_configure("skipped", foreground="darkgray")
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("error", foreground="red")

        # Horizontal scrollbar
        x_scrollbar = tk.Scrollbar(
            parent, orient=tk.HORIZONTAL, command=self.log_text.xview
        )
        x_scrollbar.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.log_text.configure(xscrollcommand=x_scrollbar.set)

        # Vertical scrollbar
        y_scrollbar = tk.Scrollbar(
            parent, orient=tk.VERTICAL, command=self.log_text.yview
        )
        y_scrollbar.grid(row=5, column=3, sticky="ns")
        self.log_text.configure(yscrollcommand=y_scrollbar.set)

    def setup_status_bar(self, parent):
        """Create the status bar."""
        status_bar = tk.Frame(parent, bd=1, relief=tk.SUNKEN)
        status_bar.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(5, 0))

        tk.Label(status_bar, textvariable=self.directories_created, anchor="w").pack(
            side=tk.LEFT, padx=5
        )
        tk.Label(status_bar, textvariable=self.files_changed, anchor="w").pack(
            side=tk.LEFT, padx=5
        )
        tk.Label(status_bar, textvariable=self.names_replaced, anchor="w").pack(
            side=tk.LEFT, padx=5
        )

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

    def gui_logger(self, message, level="normal"):
        """Log messages to the GUI text area."""
        self.log_text.configure(state="normal")
        if level == "skipped":
            self.log_text.insert(tk.END, f"{message}\n", "skipped")
        elif level == "success":
            self.log_text.insert(tk.END, f"{message}\n", "success")
        elif level == "error":
            self.log_text.insert(tk.END, f"{message}\n", "error")
        else:
            self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def run_clone(self):
        """Execute the clone operation from GUI inputs."""
        try:
            src_dir = os.path.abspath(self.src_entry.get().strip())
            dst_dir = os.path.abspath(self.dst_entry.get().strip())
            src_names = [
                name.strip() for name in self.src_name_entry.get().strip().split(",")
            ]
            dst_names = [
                name.strip() for name in self.dst_name_entry.get().strip().split(",")
            ]

            validate_inputs(src_dir, dst_dir, src_names, dst_names)

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
            folders, files, words = copy_and_replace(
                src_dir, dst_dir, src_names, dst_names, self.gui_logger
            )

            # Update statistics
            self.directories_created.set(f"Directories: {folders}")
            self.files_changed.set(f"Files: {files}")
            self.names_replaced.set(f"Names: {words}")

            self.gui_logger(
                f"Operation completed successfully. New project location: {dst_dir}",
                level="success",
            )
            messagebox.showinfo("Success", "Project cloned successfully.")

        except Exception as e:
            self.gui_logger(f"Error: {e}", level="error")
            messagebox.showerror("Error", str(e))

    def run(self):
        """Start the GUI application."""
        self.root.mainloop()


# ==============================================================================
# CLI IMPLEMENTATION
# ==============================================================================


def run_cli():
    """Execute the clone operation in CLI mode."""
    if len(sys.argv) != 5:
        cli_logger("Error: Invalid number of arguments")
        show_help()
        sys.exit(1)

    src_dir = os.path.abspath(sys.argv[1])
    dst_dir = os.path.abspath(sys.argv[2])
    src_names = [name.strip() for name in sys.argv[3].split(",")]
    dst_names = [name.strip() for name in sys.argv[4].split(",")]

    try:
        validate_inputs(src_dir, dst_dir, src_names, dst_names)
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
    folders, files, words = copy_and_replace(
        src_dir, dst_dir, src_names, dst_names, cli_logger
    )
    cli_logger(f"Directories created: {folders}")
    cli_logger(f"Files copied: {files}")
    cli_logger(f"Names replaced: {words}")
    cli_logger(f"Operation completed successfully. New project location: {dst_dir}")


def run_gui():
    """Launch the GUI interface."""
    app = CloneProjectGUI()
    app.run()


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
