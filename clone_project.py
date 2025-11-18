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
from typing import Callable, List

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


def parse_name_list(names_str: str) -> List[str]:
    """Parse comma-separated names into a list, handling whitespace and empty entries."""
    if not names_str or not names_str.strip():
        return []

    names = [name.strip() for name in names_str.split(",")]
    # Filter out empty strings and return
    return [name for name in names if name]


def validate_inputs(
    src_dir: str,
    dst_dir: str,
    src_names: List[str],
    dst_names: List[str],
    logger: Callable[[str, str], None],
) -> None:
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

        if src_name == dst_name and src_dir != dst_dir:
            logger(
                f"Warning: Replacement pair '{src_name}' -> '{dst_name}' is identical. "
                "This will result in no change for this specific name.",
                level="warning",
            )

    # Check for directory conflicts
    if src_dir == dst_dir:
        raise ValueError("Source and destination directories cannot be the same.")


def show_help() -> None:
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


def process_file_content(
    file_path: str,
    src_names: List[str],
    dst_names: List[str],
    logger: Callable[[str, str], None],
) -> List[int]:
    """Process file content replacements."""
    replacement_counts_per_name = [0] * len(src_names)

    try:
        with open(file_path, "rb") as f:
            content_bytes = f.read()

        # Heuristic: if null byte is present, assume binary
        if b"\x00" in content_bytes:
            logger(f"Skipped file (likely binary): {file_path}", level="skipped")
            return replacement_counts_per_name

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            logger(f"Skipped file (not UTF-8 decodable): {file_path}", level="skipped")
            return replacement_counts_per_name

        updated_content = content
        total_replacements = 0
        replacements_made = []

        for i, (src_name, dst_name) in enumerate(zip(src_names, dst_names)):
            replacements = updated_content.count(src_name)
            if replacements > 0:
                updated_content = updated_content.replace(src_name, dst_name)
                total_replacements += replacements
                replacement_counts_per_name[i] += replacements
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

        return replacement_counts_per_name
    except IOError:
        logger(f"Skipped file (IO Error): {file_path}", level="skipped")
        return replacement_counts_per_name


def replace_in_contents(
    file_path: str,
    src_names: List[str],
    dst_names: List[str],
    logger: Callable[[str, str], None],
) -> List[int]:
    """Replace text content in a file, skipping binary/unreadable files."""
    return process_file_content(file_path, src_names, dst_names, logger)


def process_directory_structure(
    src_dir: str,
    dst_dir: str,
    src_names: List[str],
    dst_names: List[str],
    logger: Callable[[str, str], None],
) -> tuple[str, int, int]:
    """Process directory structure creation and counting."""
    src_dir_basename = os.path.basename(src_dir)
    processed_dst_root_name = src_dir_basename

    for src_name, dst_name in zip(src_names, dst_names):
        processed_dst_root_name = re.sub(
            re.escape(src_name), dst_name, processed_dst_root_name
        )

    actual_dst_root = os.path.join(dst_dir, processed_dst_root_name)
    os.makedirs(actual_dst_root, exist_ok=True)

    total_directories = 1
    directories_renamed = 1 if processed_dst_root_name != src_dir_basename else 0

    return actual_dst_root, total_directories, directories_renamed


def process_directories_and_files(
    src_dir: str,
    actual_dst_root: str,
    src_names: List[str],
    dst_names: List[str],
    logger: Callable[[str, str], None],
    total_directories: int,
    directories_renamed: int,
) -> tuple[int, int, int, int, List[int]]:
    """Process all directories and files during copy operation."""
    total_files = 0
    files_renamed = 0
    names_replaced_list = [0] * len(src_names)

    for root, dirs, files in os.walk(src_dir, topdown=True):
        rel_path = os.path.relpath(root, src_dir)

        if rel_path == ".":
            current_dst_base_path = actual_dst_root
        else:
            processed_rel_path = rel_path
            for src_name, dst_name in zip(src_names, dst_names):
                processed_rel_path = re.sub(
                    re.escape(src_name), dst_name, processed_rel_path
                )

            current_dst_base_path = os.path.join(actual_dst_root, processed_rel_path)

            if not os.path.exists(current_dst_base_path):
                os.makedirs(current_dst_base_path, exist_ok=True)
                total_directories += 1

        # Count directory renames
        for d in dirs:
            original_dir_name = d
            processed_dir_name = original_dir_name
            for src_name, dst_name in zip(src_names, dst_names):
                processed_dir_name = re.sub(
                    re.escape(src_name), dst_name, processed_dir_name
                )
            if processed_dir_name != original_dir_name:
                directories_renamed += 1

        # Process files
        for file in files:
            total_files, files_renamed, names_replaced_list = process_single_file(
                root,
                file,
                current_dst_base_path,
                src_names,
                dst_names,
                logger,
                total_files,
                files_renamed,
                names_replaced_list,
            )

    return (
        total_directories,
        total_files,
        directories_renamed,
        files_renamed,
        names_replaced_list,
    )


def process_single_file(
    root: str,
    file: str,
    current_dst_base_path: str,
    src_names: List[str],
    dst_names: List[str],
    logger: Callable[[str, str], None],
    total_files: int,
    files_renamed: int,
    names_replaced_list: List[int],
) -> tuple[int, int, List[int]]:
    """Process a single file during copy operation."""
    src_file_path = os.path.join(root, file)
    new_file_name = file

    for src_name, dst_name in zip(src_names, dst_names):
        new_file_name = re.sub(re.escape(src_name), dst_name, new_file_name)

    if new_file_name != file:
        files_renamed += 1

    dst_file_path = os.path.join(current_dst_base_path, new_file_name)
    shutil.copy2(src_file_path, dst_file_path)
    total_files += 1

    file_replacements = replace_in_contents(dst_file_path, src_names, dst_names, logger)

    for i, count in enumerate(file_replacements):
        names_replaced_list[i] += count

    return total_files, files_renamed, names_replaced_list


def copy_and_replace(
    src_dir: str,
    dst_dir: str,
    src_names: List[str],
    dst_names: List[str],
    logger: Callable[[str, str], None],
) -> tuple[int, int, int, int, List[int]]:
    """Copy directory structure while replacing names in contents and filenames."""
    logger("Replacement mapping:")
    for i, (src_name, dst_name) in enumerate(zip(src_names, dst_names), 1):
        logger(f"  {i}. '{src_name}' → '{dst_name}'")

    actual_dst_root, total_directories, directories_renamed = (
        process_directory_structure(src_dir, dst_dir, src_names, dst_names, logger)
    )

    (
        total_directories,
        total_files,
        directories_renamed,
        files_renamed,
        names_replaced_list,
    ) = process_directories_and_files(
        src_dir,
        actual_dst_root,
        src_names,
        dst_names,
        logger,
        total_directories,
        directories_renamed,
    )

    return (
        total_directories,
        total_files,
        directories_renamed,
        files_renamed,
        names_replaced_list,
    )


# ==============================================================================
# LOGGERS
# ==============================================================================


def cli_logger(message: str, level: str = "normal") -> None:
    """Simple logger for CLI mode."""
    print(message)


# ==============================================================================
# GUI IMPLEMENTATION
# ==============================================================================


class CloneProjectGUI:
    """Tkinter GUI for the clone project utility."""

    CONFIG_FILE = "clone_project.cfg"

    def __init__(self) -> None:
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
        self.setup_style()

        # Initialize statistics variables
        self.directories_ratio = tk.StringVar(value="Directories: 0")
        self.files_ratio = tk.StringVar(value="Files: 0")
        self.names_replaced = tk.StringVar(value="Names: 0")

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._save_and_exit)

    def setup_style(self) -> None:
        """Configure ttk styles."""
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

    def setup_ui(self) -> None:
        """Initialize all GUI components."""
        main_frame = ttk.Frame(self.root, padding=(10, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Setup all UI components
        self.setup_input_fields(main_frame)
        self.setup_buttons(main_frame)
        self.setup_log_area(main_frame)
        self.setup_status_bar(main_frame)
        self.configure_layout(main_frame)

    def setup_input_fields(self, parent: ttk.Frame) -> None:
        """Create and arrange input fields with labels."""
        fields = [
            ("Source Directory:", "src_entry"),
            ("Destination Directory:", "dst_entry"),
            ("Source Name(s):", "src_name_entry"),
            ("Destination Name(s):", "dst_name_entry"),
        ]

        for row, (label_text, attr_name) in enumerate(fields):
            ttk.Label(parent, text=label_text, width=LABEL_WIDTH, anchor="e").grid(
                row=row, column=0, sticky="e"
            )
            entry = ttk.Entry(parent, width=ENTRY_WIDTH)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="we")
            setattr(self, attr_name, entry)

    def setup_buttons(self, parent: ttk.Frame) -> None:
        """Create control buttons."""
        browse_buttons = [
            ("Browse", lambda: self.browse_dir(self.src_entry), 0),
            ("Browse", lambda: self.browse_dir(self.dst_entry), 1),
        ]

        for text, command, row in browse_buttons:
            button = ttk.Button(
                parent,
                text=text,
                command=command,
                width=BUTTON_WIDTH,
                style="Browse.TButton",
            )
            button.grid(row=row, column=2, padx=5, pady=5)
            self.bind_button_events(button)

        clone_button = ttk.Button(
            parent,
            text="Clone Project",
            command=self.run_clone,
            style="Clone.TButton",
        )
        clone_button.grid(row=4, column=0, columnspan=3, pady=(10, 5), sticky="we")
        self.bind_button_events(clone_button)

    def bind_button_events(self, button: ttk.Button) -> None:
        """Bind common button events."""
        button.bind("<Enter>", self.on_enter)
        button.bind("<Leave>", self.on_leave)

    def setup_log_area(self, parent: ttk.Frame) -> None:
        """Create logging text area with scrollbar."""
        self.log_text = tk.Text(parent, height=10, state="disabled", wrap="none")
        self.log_text.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="nsew")

        # Configure text tags for different message levels
        self.setup_log_tags()

        # Scrollbars
        self.setup_scrollbars(parent)

    def setup_log_tags(self) -> None:
        """Configure text tags for different log levels."""
        tags = {
            "error": "red",
            "warning": "orange",
            "info": "blue",
            "success": "green",
            "skipped": "darkgray",
        }

        for tag, color in tags.items():
            self.log_text.tag_configure(tag, foreground=color)

    def setup_scrollbars(self, parent: ttk.Frame) -> None:
        """Setup horizontal and vertical scrollbars."""
        x_scrollbar = ttk.Scrollbar(
            parent, orient=tk.HORIZONTAL, command=self.log_text.xview
        )
        x_scrollbar.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.log_text.configure(xscrollcommand=x_scrollbar.set)

        y_scrollbar = ttk.Scrollbar(
            parent, orient=tk.VERTICAL, command=self.log_text.yview
        )
        y_scrollbar.grid(row=5, column=3, sticky="ns")
        self.log_text.configure(yscrollcommand=y_scrollbar.set)

    def setup_status_bar(self, parent: ttk.Frame) -> None:
        """Create the status bar."""
        status_bar = ttk.Frame(parent, style="Status.TFrame")
        status_bar.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(5, 0))

        status_vars = [self.directories_ratio, self.files_ratio, self.names_replaced]

        for var in status_vars:
            ttk.Label(status_bar, textvariable=var, anchor="w").pack(
                side=tk.LEFT, padx=5
            )

    def configure_layout(self, parent: ttk.Frame) -> None:
        """Configure grid weights for responsive layout."""
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(5, weight=1)

    def browse_dir(self, entry_widget: ttk.Entry) -> None:
        """Open directory browser and update entry field."""
        path = filedialog.askdirectory()
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def gui_logger(self, message: str, level: str = "normal") -> None:
        """Log messages to the GUI text area."""
        self.log_text.configure(state="normal")

        tag = (
            level
            if level in ["error", "warning", "info", "success", "skipped"]
            else None
        )
        insert_args = (tk.END, f"{message}\n", tag) if tag else (tk.END, f"{message}\n")

        self.log_text.insert(*insert_args)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def on_enter(self, event: tk.Event) -> None:
        """Change cursor to hand."""
        self.root.config(cursor="hand2")

    def on_leave(self, event: tk.Event) -> None:
        """Change cursor back to default."""
        self.root.config(cursor="")

    def run_clone(self) -> None:
        """Execute the clone operation from GUI inputs."""
        try:
            src_dir = os.path.abspath(self.src_entry.get().strip())
            dst_dir = os.path.abspath(self.dst_entry.get().strip())
            src_names = parse_name_list(self.src_name_entry.get().strip())
            dst_names = parse_name_list(self.dst_name_entry.get().strip())

            validate_inputs(src_dir, dst_dir, src_names, dst_names, self.gui_logger)
            self.log_replacement_plan(src_names, dst_names)

            # Handle existing destination
            if os.path.exists(dst_dir):
                if not self.confirm_overwrite(dst_dir):
                    return
                shutil.rmtree(dst_dir)

            # Perform clone operation
            self.execute_clone_operation(src_dir, dst_dir, src_names, dst_names)

        except Exception as e:
            self.gui_logger(f"Error: {e}", level="error")
            messagebox.showerror("Error", str(e))

    def log_replacement_plan(self, src_names: List[str], dst_names: List[str]) -> None:
        """Log the replacement plan."""
        self.gui_logger("Replacement plan:", level="info")
        for i, (src_name, dst_name) in enumerate(zip(src_names, dst_names), 1):
            self.gui_logger(f"  {i}. '{src_name}' → '{dst_name}'", level="info")

        if len(src_names) > 1:
            self.gui_logger(
                "Note: Replacements are processed in order. Be careful with overlapping patterns.",
                level="info",
            )

    def confirm_overwrite(self, dst_dir: str) -> bool:
        """Confirm overwrite of existing destination directory."""
        return messagebox.askyesno(
            "Destination exists",
            f"Destination '{dst_dir}' already exists. Overwrite?",
        )

    def execute_clone_operation(
        self,
        src_dir: str,
        dst_dir: str,
        src_names: List[str],
        dst_names: List[str],
    ) -> None:
        """Execute the actual clone operation."""
        self.gui_logger("Starting clone operation...")
        (
            total_directories,
            total_files,
            directories_renamed,
            files_renamed,
            names_replaced_list,
        ) = copy_and_replace(src_dir, dst_dir, src_names, dst_names, self.gui_logger)

        # Update statistics
        self.directories_ratio.set(
            f"Directories: {directories_renamed}/{total_directories}"
        )
        self.files_ratio.set(f"Files: {files_renamed}/{total_files}")
        self.names_replaced.set(f"Names: {', '.join(map(str, names_replaced_list))}")

        self.gui_logger(
            f"Operation completed successfully. New project location: {dst_dir}",
            level="success",
        )
        messagebox.showinfo("Success", "Project cloned successfully.")

    def _save_and_exit(self) -> None:
        """Save window geometry and exit."""
        if not self.config.has_section("window"):
            self.config.add_section("window")
        self.config.set("window", "geometry", self.root.geometry())
        with open(self.CONFIG_FILE, "w") as configfile:
            self.config.write(configfile)
        self.root.destroy()

    def run(self) -> None:
        """Start the GUI application."""
        self.root.mainloop()


# ==============================================================================
# CLI IMPLEMENTATION
# ==============================================================================


def run_cli() -> None:
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
    (
        total_directories,
        total_files,
        directories_renamed,
        files_renamed,
        names_replaced_list,
    ) = copy_and_replace(src_dir, dst_dir, src_names, dst_names, cli_logger)

    cli_logger(
        f"Total Directories: {total_directories} (renamed: {directories_renamed})"
    )

    cli_logger(f"Total Files: {total_files} (renamed: {files_renamed})")

    cli_logger(f"Names replaced: {', '.join(map(str, names_replaced_list))}")

    cli_logger(f"Operation completed successfully. New project location: {dst_dir}")


def run_gui() -> None:
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
