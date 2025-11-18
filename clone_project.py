#!/usr/bin/env python3
"""
Utility to clone a project via CLI or Tkinter GUI. This script allows users to
duplicate a project, replacing specific names within file contents and
filenames.

Author: Gino Bogo
"""

import configparser
import os
import re
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ==============================================================================
# CONSTANTS
# ==============================================================================

MIN_WINDOW_SIZE = (600, 600)  # Used as minimum window size
LABEL_WIDTH = 20
ENTRY_WIDTH = 50
BUTTON_WIDTH = 10


# ==============================================================================
# VALIDATION & HELPER FUNCTIONS
# ==============================================================================


def parse_name_list(names_str):
    """Parse comma-separated names into a list, handling whitespace and empty entries."""
    if not names_str or not names_str.strip():
        return []

    names = [name.strip() for name in names_str.split(",")]
    # Filter out empty strings and return
    return [name for name in names if name]


def validate_inputs(src_dir, dst_dir, src_names, dst_names, logger):
    """Validate all input parameters."""
    if not all([src_dir, dst_dir]) or not src_names or not dst_names:
        raise ValueError("All fields are required and must contain at least one name.")

    if not os.path.isdir(src_dir):
        raise ValueError(f"Source directory '{src_dir}' not found.")

    if len(src_names) != len(dst_names):
        raise ValueError(
            f"Number of source names ({len(src_names)}) must match number of "
            f"destination names ({len(dst_names)})."
        )

    # Check for empty names and identical names
    for i, (src_name, dst_name) in enumerate(zip(src_names, dst_names), 1):
        if not src_name:
            raise ValueError(f"Source name #{i} cannot be empty.")
        if not dst_name:
            raise ValueError(f"Destination name #{i} cannot be empty.")

        if src_name == dst_name:
            if src_dir != dst_dir:
                logger(
                    f"Warning: Replacement pair '{src_name}' -> '{dst_name}' is identical. "
                    "This will result in no change for this specific name.",
                    level="warning",
                )

    # Check for directory conflicts
    if src_dir == dst_dir:
        raise ValueError("Source and destination directories cannot be the same.")


def show_help():
    """Display CLI usage information."""
    print(
        "Usage: python clone_project.py <src_dir> <dst_dir> <src_name1,src_name2,...> <dst_name1,dst_name2,...>"
    )
    print("\nExamples:")
    print("  python clone_project.py /old/proj /new/proj oldname newname")
    print('  python clone_project.py /old/proj /new/proj "old1,old2" "new1,new2"')
    print(
        '  python clone_project.py /companyA/projX /companyB/projY "companyA,projX" "companyB,projY"'
    )
    print("\nNote: Number of source names must match number of destination names.")
    print("Replacements are processed in order - be careful with overlapping patterns.")
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
        replacements_made = []

        for src_name, dst_name in zip(src_names, dst_names):
            replacements = updated_content.count(src_name)
            if replacements > 0:
                updated_content = updated_content.replace(src_name, dst_name)
                total_replacements += replacements
                replacements_made.append(f"'{src_name}'→'{dst_name}':{replacements}")

        if total_replacements > 0:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            normalized_file_path = os.path.normpath(file_path)
            logger(
                f"Updated contents of: {normalized_file_path} ({total_replacements} replacements)"
            )
            if len(replacements_made) > 1:
                logger(f"  Breakdown: {', '.join(replacements_made)}")
        return total_replacements
    except IOError:
        logger(f"Skipped file (IO Error): {file_path}", level="skipped")
        return 0


def copy_and_replace(src_dir, dst_dir, src_names, dst_names, logger):
    """Copy directory structure while replacing names in contents and filenames."""
    folders_created = 0
    files_copied = 0
    words_replaced = 0

    # Log replacement mapping for clarity
    logger("Replacement mapping:")
    for i, (src_name, dst_name) in enumerate(zip(src_names, dst_names), 1):
        logger(f"  {i}. '{src_name}' → '{dst_name}'")

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

    CONFIG_FILE = "clone_project.cfg"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Clone Project")

        # Load window geometry
        self.config = configparser.ConfigParser()
        if os.path.exists(self.CONFIG_FILE):
            self.config.read(self.CONFIG_FILE)
            geometry = self.config.get("window", "geometry", fallback=None)
            if geometry:
                self.root.geometry(geometry)
        
        self.root.minsize(*MIN_WINDOW_SIZE)

        # Configure ttk style
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Status.TFrame", relief="flat")
        self.style.configure("Browse.TButton")
        self.style.configure("Clone.TButton")
        self.style.map(
            "Browse.TButton",
            foreground=[("!disabled", "#FFFFFF")],
            background=[("active", "#0056B3"), ("!active", "#004085")],
        )
        self.style.map(
            "Clone.TButton",
            foreground=[("!disabled", "#000000")],
            background=[("active", "#E0B400"), ("!active", "#C79F00")],
        )

        # Initialize statistics variables
        self.directories_created = tk.StringVar(value="Directories: 0")
        self.files_changed = tk.StringVar(value="Files: 0")
        self.names_replaced = tk.StringVar(value="Names: 0")

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._save_and_exit)


    def setup_ui(self):
        """Initialize all GUI components."""
        main_frame = ttk.Frame(self.root, padding=(10, 10))
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
        ttk.Label(parent, text="Source Directory:", width=LABEL_WIDTH, anchor="e").grid(
            row=0, column=0, sticky="e"
        )
        self.src_entry = ttk.Entry(parent, width=ENTRY_WIDTH)
        self.src_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")

        # Destination directory
        ttk.Label(
            parent, text="Destination Directory:", width=LABEL_WIDTH, anchor="e"
        ).grid(row=1, column=0, sticky="e")
        self.dst_entry = ttk.Entry(parent, width=ENTRY_WIDTH)
        self.dst_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")

        # Source names
        ttk.Label(parent, text="Source Name(s):", width=LABEL_WIDTH, anchor="e").grid(
            row=2, column=0, sticky="e"
        )
        self.src_name_entry = ttk.Entry(parent, width=ENTRY_WIDTH)
        self.src_name_entry.grid(row=2, column=1, padx=5, pady=5, sticky="we")

        # Destination names
        ttk.Label(
            parent, text="Destination Name(s):", width=LABEL_WIDTH, anchor="e"
        ).grid(row=3, column=0, sticky="e")
        self.dst_name_entry = ttk.Entry(parent, width=ENTRY_WIDTH)
        self.dst_name_entry.grid(row=3, column=1, padx=5, pady=5, sticky="we")

    def setup_buttons(self, parent):
        """Create control buttons."""
        browse_src_button = ttk.Button(
            parent,
            text="Browse",
            command=lambda: self.browse_dir(self.src_entry),
            width=BUTTON_WIDTH,
            style="Browse.TButton",
        )
        browse_src_button.grid(row=0, column=2, padx=5, pady=5)
        browse_src_button.bind("<Enter>", self.on_enter)
        browse_src_button.bind("<Leave>", self.on_leave)

        # Browse Destination button
        browse_dst_button = ttk.Button(
            parent,
            text="Browse",
            command=lambda: self.browse_dir(self.dst_entry),
            width=BUTTON_WIDTH,
            style="Browse.TButton",
        )
        browse_dst_button.grid(row=1, column=2, padx=5, pady=5)
        browse_dst_button.bind("<Enter>", self.on_enter)
        browse_dst_button.bind("<Leave>", self.on_leave)

        # Clone Project button
        clone_button = ttk.Button(
            parent,
            text="Clone Project",
            command=self.run_clone,
            style="Clone.TButton",
        )
        clone_button.grid(row=4, column=0, columnspan=3, pady=(10, 5), sticky="we")
        clone_button.bind("<Enter>", self.on_enter)
        clone_button.bind("<Leave>", self.on_leave)

    def setup_log_area(self, parent):
        """Create logging text area with scrollbar."""
        self.log_text = tk.Text(parent, height=10, state="disabled", wrap="none")
        self.log_text.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="nsew")

        # Configure text tags for different message levels
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("success", foreground="green")
        self.log_text.tag_configure("skipped", foreground="darkgray")

        # Horizontal scrollbar
        x_scrollbar = ttk.Scrollbar(
            parent, orient=tk.HORIZONTAL, command=self.log_text.xview
        )
        x_scrollbar.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.log_text.configure(xscrollcommand=x_scrollbar.set)

        # Vertical scrollbar
        y_scrollbar = ttk.Scrollbar(
            parent, orient=tk.VERTICAL, command=self.log_text.yview
        )
        y_scrollbar.grid(row=5, column=3, sticky="ns")
        self.log_text.configure(yscrollcommand=y_scrollbar.set)

    def setup_status_bar(self, parent):
        """Create the status bar."""
        status_bar = ttk.Frame(parent, style="Status.TFrame")
        status_bar.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(5, 0))

        ttk.Label(status_bar, textvariable=self.directories_created, anchor="w").pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(status_bar, textvariable=self.files_changed, anchor="w").pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(status_bar, textvariable=self.names_replaced, anchor="w").pack(
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
        if level == "error":
            self.log_text.insert(tk.END, f"{message}\n", "error")
        elif level == "warning":
            self.log_text.insert(tk.END, f"{message}\n", "warning")
        elif level == "info":
            self.log_text.insert(tk.END, f"{message}\n", "info")
        elif level == "success":
            self.log_text.insert(tk.END, f"{message}\n", "success")
        elif level == "skipped":
            self.log_text.insert(tk.END, f"{message}\n", "skipped")
        else:
            self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def on_enter(self, event):
        """Change cursor to hand."""
        self.root.config(cursor="hand2")

    def on_leave(self, event):
        """Change cursor back to default."""
        self.root.config(cursor="")

    def run_clone(self):
        """Execute the clone operation from GUI inputs."""
        try:
            src_dir = os.path.abspath(self.src_entry.get().strip())
            dst_dir = os.path.abspath(self.dst_entry.get().strip())
            src_names = parse_name_list(self.src_name_entry.get().strip())
            dst_names = parse_name_list(self.dst_name_entry.get().strip())

            validate_inputs(src_dir, dst_dir, src_names, dst_names, self.gui_logger)

            # Log the replacement plan
            self.gui_logger("Replacement plan:", level="info")
            for i, (src_name, dst_name) in enumerate(zip(src_names, dst_names), 1):
                self.gui_logger(f"  {i}. '{src_name}' → '{dst_name}'", level="info")

            if len(src_names) > 1:
                self.gui_logger(
                    "Note: Replacements are processed in order. Be careful with overlapping patterns.",
                    level="info",
                )

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
            self.gui_logger("Starting clone operation...")
            directories, files, names = copy_and_replace(
                src_dir, dst_dir, src_names, dst_names, self.gui_logger
            )

            # Update statistics
            self.directories_created.set(f"Directories: {directories}")
            self.files_changed.set(f"Files: {files}")
            self.names_replaced.set(f"Names: {names}")

            self.gui_logger(
                f"Operation completed successfully. New project location: {dst_dir}",
                level="success",
            )
            messagebox.showinfo("Success", "Project cloned successfully.")

        except Exception as e:
            self.gui_logger(f"Error: {e}", level="error")
            messagebox.showerror("Error", str(e))

    def _save_and_exit(self):
        """Save window geometry and exit."""
        if not self.config.has_section("window"):
            self.config.add_section("window")
        self.config.set("window", "geometry", self.root.geometry())
        with open(self.CONFIG_FILE, "w") as configfile:
            self.config.write(configfile)
        self.root.destroy()

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
    src_names = parse_name_list(sys.argv[3])
    dst_names = parse_name_list(sys.argv[4])

    try:
        validate_inputs(src_dir, dst_dir, src_names, dst_names, cli_logger)
    except ValueError as e:
        cli_logger(f"Error: {e}")
        sys.exit(1)

    # Log the replacement plan
    cli_logger("Replacement plan:")
    for i, (src_name, dst_name) in enumerate(zip(src_names, dst_names), 1):
        cli_logger(f"  {i}. '{src_name}' → '{dst_name}'")

    if len(src_names) > 1:
        cli_logger(
            "Note: Replacements are processed in order. Be careful with overlapping patterns."
        )

    # Handle existing destination
    if os.path.exists(dst_dir):
        cli_logger(
            f"Warning: Destination directory '{dst_dir}' already exists. "
            f"Overwriting..."
        )
        shutil.rmtree(dst_dir)

    # Perform clone operation
    cli_logger("Starting clone operation...")
    directories, files, names = copy_and_replace(
        src_dir, dst_dir, src_names, dst_names, cli_logger
    )
    cli_logger(f"Directories created: {directories}")
    cli_logger(f"Files copied: {files}")
    cli_logger(f"Names replaced: {names}")
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
