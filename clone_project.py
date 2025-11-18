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
from typing import Callable, List, Tuple

# ==============================================================================
# CONSTANTS
# ==============================================================================

MIN_WINDOW_SIZE = (600, 650)  # Increased height for progress bar
LABEL_WIDTH = 20
ENTRY_WIDTH = 50
BTN_WIDTH = 10

# ==============================================================================
# VALIDATION & HELPER FUNCTIONS
# ==============================================================================


def parse_names(names_str: str) -> List[str]:
    """Parse comma-separated names into a list, handling whitespace and empty entries."""
    if not names_str or not names_str.strip():
        return []

    names = [name.strip() for name in names_str.split(",")]
    return [name for name in names if name]


def validate_inputs(
    src_dir: str,
    dst_dir: str,
    src_names: List[str],
    dst_names: List[str],
    log_func: Callable[[str, str], None],
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
    for i, (src, dst) in enumerate(zip(src_names, dst_names), 1):
        if not src:
            raise ValueError(f"Source name #{i} cannot be empty.")
        if not dst:
            raise ValueError(f"Destination name #{i} cannot be empty.")

        if src == dst and src_dir != dst_dir:
            log_func(
                f"Warning: Replacement pair '{src}' -> '{dst}' is identical. "
                "This will result in no change for this specific name.",
                "warning",
            )

    # Check for directory conflicts
    if src_dir == dst_dir:
        raise ValueError("Source and destination directories cannot be the same.")


def count_files_and_dirs(src_dir: str) -> Tuple[int, int]:
    """Count total files and directories for progress tracking."""
    total_dirs = 0
    total_files = 0

    for root, dirs, files in os.walk(src_dir):
        total_dirs += len(dirs)
        total_files += len(files)

    # Add 1 for the root directory
    total_dirs += 1

    return total_dirs, total_files


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
    log_func: Callable[[str, str], None],
) -> List[int]:
    """Process file content replacements."""
    counts = [0] * len(src_names)

    try:
        with open(file_path, "rb") as f:
            content_bytes = f.read()

        # Heuristic: if null byte is present, assume binary
        if b"\x00" in content_bytes:
            log_func(f"Skipped file (likely binary): {file_path}", "skipped")
            return counts

        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            log_func(f"Skipped file (not UTF-8 decodable): {file_path}", "skipped")
            return counts

        updated = content
        total_repl = 0
        repl_made = []

        for i, (src, dst) in enumerate(zip(src_names, dst_names)):
            repl_count = updated.count(src)
            if repl_count > 0:
                updated = updated.replace(src, dst)
                total_repl += repl_count
                counts[i] += repl_count
                repl_made.append(f"'{src}'→'{dst}':{repl_count}")

        if total_repl > 0:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated)
            norm_path = os.path.normpath(file_path)
            log_func(
                f"Updated contents of: {norm_path} ({total_repl} replacements)",
                "normal",
            )
            if len(repl_made) > 1:
                log_func(f"  Breakdown: {', '.join(repl_made)}", "normal")

        return counts
    except IOError:
        log_func(f"Skipped file (IO Error): {file_path}", "skipped")
        return counts


def replace_in_contents(
    file_path: str,
    src_names: List[str],
    dst_names: List[str],
    log_func: Callable[[str, str], None],
) -> List[int]:
    """Replace text content in a file, skipping binary/unreadable files."""
    return process_file_content(file_path, src_names, dst_names, log_func)


def get_dst_root_path(
    src_dir: str,
    dst_dir: str,
    src_names: List[str],
    dst_names: List[str],
) -> tuple[str, int]:
    """Calculate destination root path and determine if it was renamed."""
    src_base = os.path.basename(src_dir)
    dst_base = src_base

    for src, dst in zip(src_names, dst_names):
        dst_base = re.sub(re.escape(src), dst, dst_base)

    # Check if the destination directory already includes the target project name
    if os.path.basename(os.path.normpath(dst_dir)) == dst_base:
        dst_root = dst_dir
    else:
        dst_root = os.path.join(dst_dir, dst_base)

    was_renamed = 1 if dst_base != src_base else 0

    return dst_root, was_renamed


def copy_and_replace(
    src_dir: str,
    dst_dir: str,
    src_names: List[str],
    dst_names: List[str],
    log_func: Callable[[str, str], None],
    prog_cb: Callable[[str, int, int], None],
) -> tuple[int, int, int, int, List[int]]:
    """Copy directory structure while replacing names in contents and filenames."""
    log_func("Replacement mapping:", "info")

    for i, (src, dst) in enumerate(zip(src_names, dst_names), 1):
        log_func(f"  {i}. '{src}' → '{dst}'", "info")

    dst_root, root_renamed = get_dst_root_path(src_dir, dst_dir, src_names, dst_names)

    # Count total files for progress tracking
    total_dirs_count, total_files_count = count_files_and_dirs(src_dir)
    processed_files = 0

    # Create ONLY the destination root directory
    os.makedirs(dst_root, exist_ok=True)

    total_dirs = 1  # Start with root directory
    total_files = 0
    dirs_renamed = root_renamed  # Start with root rename status
    files_renamed = 0
    name_counts = [0] * len(src_names)

    # Walk through source directory and copy everything
    for root, dirs, files in os.walk(src_dir):
        # Calculate relative path from source root
        rel_path = os.path.relpath(root, src_dir)

        # Determine destination path for this directory
        if rel_path == ".":
            # This is the root directory, use dst_root
            curr_dst_dir = dst_root
        else:
            # Apply name replacements to the relative path
            processed_rel_path = rel_path
            for src, dst in zip(src_names, dst_names):
                processed_rel_path = re.sub(re.escape(src), dst, processed_rel_path)

            curr_dst_dir = os.path.join(dst_root, processed_rel_path)

            # Create subdirectory if it doesn't exist
            if not os.path.exists(curr_dst_dir):
                os.makedirs(curr_dst_dir, exist_ok=True)
                total_dirs += 1

        # Process directories for rename counting
        for dir_name in dirs:
            orig_name = dir_name
            new_name = orig_name
            for src, dst in zip(src_names, dst_names):
                new_name = re.sub(re.escape(src), dst, new_name)
            if new_name != orig_name:
                dirs_renamed += 1

        # Process files
        for file_name in files:
            src_file = os.path.join(root, file_name)

            # Apply name replacements to filename
            new_file_name = file_name
            for src, dst in zip(src_names, dst_names):
                new_file_name = re.sub(re.escape(src), dst, new_file_name)

            dst_file = os.path.join(curr_dst_dir, new_file_name)

            # Copy file
            shutil.copy2(src_file, dst_file)
            total_files += 1
            processed_files += 1

            # Update progress
            if prog_cb:
                prog_cb("file", processed_files, total_files_count)

            # Count filename rename
            if new_file_name != file_name:
                files_renamed += 1

            # Process file contents
            file_repl = replace_in_contents(dst_file, src_names, dst_names, log_func)
            for i, count in enumerate(file_repl):
                name_counts[i] += count

    return total_dirs, total_files, dirs_renamed, files_renamed, name_counts


# ==============================================================================
# LOGGERS
# ==============================================================================


def cli_log(message: str, level: str = "normal") -> None:
    """Simple logger for CLI mode."""
    print(message)


# ==============================================================================
# GUI IMPLEMENTATION
# ==============================================================================


class CloneProjectGUI:
    """Tkinter GUI for the clone project utility."""

    src_entry: ttk.Entry
    dst_entry: ttk.Entry
    src_name_entry: ttk.Entry
    dst_name_entry: ttk.Entry

    CONFIG_FILE: str = "clone_project.cfg"

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Clone Project")

        # Initialize attributes
        self.src_entry = ttk.Entry()
        self.dst_entry = ttk.Entry()
        self.src_name_entry = ttk.Entry()
        self.dst_name_entry = ttk.Entry()

        # Load window geometry
        self.cfg = configparser.ConfigParser()
        if os.path.exists(self.CONFIG_FILE):
            self.cfg.read(self.CONFIG_FILE)
            geometry = self.cfg.get("window", "geometry", fallback=None)
            if geometry:
                self.root.geometry(geometry)

        self.root.minsize(*MIN_WINDOW_SIZE)

        # Configure ttk style
        self.setup_style()

        # Initialize statistics variables
        self.dir_var = tk.StringVar(value="Directories: 0")
        self.file_var = tk.StringVar(value="Files: 0")
        self.name_var = tk.StringVar(value="Names: 0")

        # Progress tracking
        self.progress_var = tk.DoubleVar()
        self.progress_label = tk.StringVar(value="Ready")

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._save_exit)

    def setup_style(self) -> None:
        """Configure ttk styles."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Status.TFrame", relief="flat")
        self.style.configure("Browse.TButton")
        self.style.configure("Clone.TButton")
        self.style.configure(
            "Horizontal.TProgressbar",
            thickness=20,
            troughcolor="#D4EDDA",
            background="#28A745",
        )
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
        main = ttk.Frame(self.root, padding=(10, 10))
        main.pack(fill=tk.BOTH, expand=True)

        # Setup all UI components
        self.setup_inputs(main)
        self.setup_buttons(main)
        self.setup_progress(main)
        self.setup_log(main)
        self.setup_status(main)
        self.setup_layout(main)

    def setup_inputs(self, parent: ttk.Frame) -> None:
        """Create and arrange input fields with labels."""
        fields = [
            ("Source Directory:", "src_entry"),
            ("Destination Directory:", "dst_entry"),
            ("Source Name(s):", "src_name_entry"),
            ("Destination Name(s):", "dst_name_entry"),
        ]

        for row, (label, attr) in enumerate(fields):
            ttk.Label(parent, text=label, width=LABEL_WIDTH, anchor="e").grid(
                row=row, column=0, sticky="e"
            )
            entry = ttk.Entry(parent, width=ENTRY_WIDTH)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="we")
            setattr(self, attr, entry)

    def setup_buttons(self, parent: ttk.Frame) -> None:
        """Create control buttons."""
        browse_btns = [
            ("Browse", lambda: self.browse_dir(self.src_entry), 0),
            ("Browse", lambda: self.browse_dir(self.dst_entry), 1),
        ]

        for text, cmd, row in browse_btns:
            btn = ttk.Button(
                parent,
                text=text,
                command=cmd,
                width=BTN_WIDTH,
                style="Browse.TButton",
            )
            btn.grid(row=row, column=2, padx=5, pady=5)
            self.bind_events(btn)

        clone_btn = ttk.Button(
            parent,
            text="Clone Project",
            command=self.run_clone,
            style="Clone.TButton",
        )
        clone_btn.grid(row=4, column=0, columnspan=3, pady=(10, 5), sticky="we")
        self.bind_events(clone_btn)

    def setup_progress(self, parent: ttk.Frame) -> None:
        """Create progress bar and label."""
        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=5, column=0, columnspan=3, pady=(10, 5), sticky="we")

        # Progress label
        self.progress_label_widget = ttk.Label(
            progress_frame, textvariable=self.progress_label, anchor="w"
        )
        self.progress_label_widget.pack(fill=tk.X, padx=5)

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            style="Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=(2, 0))

    def bind_events(self, btn: ttk.Button) -> None:
        """Bind common button events."""
        btn.bind("<Enter>", self.on_enter)
        btn.bind("<Leave>", self.on_leave)

    def setup_log(self, parent: ttk.Frame) -> None:
        """Create logging text area with scrollbar."""
        self.log = tk.Text(parent, height=10, state="disabled", wrap="none")
        self.log.grid(row=6, column=0, columnspan=3, pady=(10, 0), sticky="nsew")

        # Configure text tags for different message levels
        self.setup_tags()

        # Scrollbars
        self.setup_scrollbars(parent)

    def setup_tags(self) -> None:
        """Configure text tags for different log levels."""
        tags = {
            "error": "red",
            "warning": "orange",
            "info": "blue",
            "success": "green",
            "skipped": "darkgray",
        }

        for tag, color in tags.items():
            self.log.tag_configure(tag, foreground=color)

    def setup_scrollbars(self, parent: ttk.Frame) -> None:
        """Setup horizontal and vertical scrollbars."""
        x_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.log.xview)
        x_scroll.grid(row=7, column=0, columnspan=3, sticky="ew")
        self.log.configure(xscrollcommand=x_scroll.set)

        y_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.log.yview)
        y_scroll.grid(row=6, column=3, sticky="ns")
        self.log.configure(yscrollcommand=y_scroll.set)

    def setup_status(self, parent: ttk.Frame) -> None:
        """Create the status bar."""
        status = ttk.Frame(parent, style="Status.TFrame")
        status.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(5, 0))

        status_vars = [self.dir_var, self.file_var, self.name_var]

        for var in status_vars:
            ttk.Label(status, textvariable=var, anchor="w").pack(side=tk.LEFT, padx=5)

    def setup_layout(self, parent: ttk.Frame) -> None:
        """Configure grid weights for responsive layout."""
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(6, weight=1)

    def browse_dir(self, entry: ttk.Entry) -> None:
        """Open directory browser and update entry field."""
        path = filedialog.askdirectory()
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def update_progress(self, item_type: str, current: int, total: int) -> None:
        """Update progress bar and label."""
        if total > 0:
            percentage = (current / total) * 100
            self.progress_var.set(percentage)
            self.progress_label.set(
                f"Processing {item_type}s: {current}/{total} ({percentage:.1f}%)"
            )
        self.root.update_idletasks()

    def reset_progress(self) -> None:
        """Reset progress bar to initial state."""
        self.progress_var.set(0)
        self.progress_label.set("Ready")

    def gui_log(self, msg: str, level: str = "normal") -> None:
        """Log messages to the GUI text area."""
        self.log.configure(state="normal")

        tag = (
            level
            if level in ["error", "warning", "info", "success", "skipped"]
            else None
        )
        args = (tk.END, f"{msg}\n", tag) if tag else (tk.END, f"{msg}\n")

        self.log.insert(*args)
        self.log.see(tk.END)
        self.log.configure(state="disabled")
        self.root.update_idletasks()

    def on_enter(self, event: tk.Event) -> None:
        """Change cursor to hand."""
        self.root.config(cursor="hand2")

    def on_leave(self, event: tk.Event) -> None:
        """Change cursor back to default."""
        self.root.config(cursor="")

    def run_clone(self) -> None:
        """Execute the clone operation from GUI inputs."""
        try:
            src = os.path.abspath(self.src_entry.get().strip())
            dst = os.path.abspath(self.dst_entry.get().strip())
            src_names = parse_names(self.src_name_entry.get().strip())
            dst_names = parse_names(self.dst_name_entry.get().strip())

            validate_inputs(src, dst, src_names, dst_names, self.gui_log)
            self.log_plan(src_names, dst_names)

            # Handle existing destination
            dst_root, _ = get_dst_root_path(src, dst, src_names, dst_names)
            if os.path.exists(dst_root):
                if not self.confirm_overwrite(dst_root):
                    return
                shutil.rmtree(dst_root)

            # Reset progress before starting
            self.reset_progress()

            # Reset counters before starting
            self.dir_var.set("Directories: 0")
            self.file_var.set("Files: 0")
            self.name_var.set("Names: 0")

            # Perform clone operation
            self.do_clone(src, dst, src_names, dst_names)

        except Exception as e:
            self.gui_log(f"Error: {e}", level="error")
            messagebox.showerror("Error", str(e))
            self.reset_progress()

    def log_plan(self, src_names: List[str], dst_names: List[str]) -> None:
        """Log the replacement plan."""
        self.gui_log("Replacement plan:", level="info")
        for i, (src, dst) in enumerate(zip(src_names, dst_names), 1):
            self.gui_log(f"  {i}. '{src}' → '{dst}'", level="info")

        if len(src_names) > 1:
            self.gui_log(
                "Note: Replacements are processed in order. Be careful with overlapping patterns.",
                level="info",
            )

    def confirm_overwrite(self, dst: str) -> bool:
        """Confirm overwrite of existing destination directory."""
        return messagebox.askyesno(
            "Destination exists", f"Destination '{dst}' already exists. Overwrite?"
        )

    def do_clone(
        self,
        src: str,
        dst: str,
        src_names: List[str],
        dst_names: List[str],
    ) -> None:
        """Execute the actual clone operation."""
        self.gui_log("Starting clone operation...")
        (
            total_dirs,
            total_files,
            dirs_renamed,
            files_renamed,
            name_counts,
        ) = copy_and_replace(
            src,
            dst,
            src_names,
            dst_names,
            self.gui_log,
            prog_cb=self.update_progress,
        )

        # Update statistics
        self.dir_var.set(f"Directories: {dirs_renamed}/{total_dirs}")
        self.file_var.set(f"Files: {files_renamed}/{total_files}")
        self.name_var.set(f"Names: {', '.join(map(str, name_counts))}")

        # Complete progress
        self.progress_var.set(100)
        self.progress_label.set("Operation completed successfully!")

        self.gui_log(
            f"Operation completed successfully. New project location: {dst}",
            level="success",
        )
        messagebox.showinfo("Success", "Project cloned successfully.")

    def _save_exit(self) -> None:
        """Save window geometry and exit."""
        if not self.cfg.has_section("window"):
            self.cfg.add_section("window")
        self.cfg.set("window", "geometry", self.root.geometry())
        with open(self.CONFIG_FILE, "w") as f:
            self.cfg.write(f)
        self.root.destroy()

    def run(self) -> None:
        """Start the GUI application."""
        self.root.mainloop()


# ==============================================================================
# CLI IMPLEMENTATION
# ==============================================================================


def cli_progress_callback(item_type: str, current: int, total: int) -> None:
    """Update progress for CLI mode."""
    if total > 0:
        percentage = (current / total) * 100
        sys.stdout.write(
            f"\rProcessing {item_type}s: {current}/{total} ({percentage:.1f}%)"
        )
        sys.stdout.flush()


def run_cli() -> None:
    """Execute the clone operation in CLI mode."""
    if len(sys.argv) < 5:
        cli_log("Error: Invalid number of arguments")
        show_help()
        sys.exit(1)

    src_dir = os.path.abspath(sys.argv[1])
    dst_dir = os.path.abspath(sys.argv[2])
    src_names = parse_names(sys.argv[3])
    dst_names = parse_names(sys.argv[4])

    try:
        validate_inputs(src_dir, dst_dir, src_names, dst_names, cli_log)
    except ValueError as e:
        cli_log(f"Error: {e}")
        sys.exit(1)

    # Log the replacement plan
    cli_log("Replacement plan:")
    for i, (src, dst) in enumerate(zip(src_names, dst_names), 1):
        cli_log(f"  {i}. '{src}' → '{dst}'")

    if len(src_names) > 1:
        cli_log(
            "Note: Replacements are processed in order. Be careful with overlapping patterns."
        )

    # Handle existing destination
    dst_root, _ = get_dst_root_path(src_dir, dst_dir, src_names, dst_names)
    if os.path.exists(dst_root):
        cli_log(
            f"Warning: Destination directory '{dst_root}' already exists. Overwriting..."
        )
        shutil.rmtree(dst_root)

    # Perform clone operation
    cli_log("Starting clone operation...")
    (
        total_dirs,
        total_files,
        dirs_renamed,
        files_renamed,
        name_counts,
    ) = copy_and_replace(
        src_dir,
        dst_dir,
        src_names,
        dst_names,
        cli_log,
        prog_cb=cli_progress_callback,
    )
    # Clear the progress line and print final results
    sys.stdout.write("\r" + " " * 50 + "\r")

    cli_log(f"Total Directories: {total_dirs} (renamed: {dirs_renamed})")
    cli_log(f"Total Files: {total_files} (renamed: {files_renamed})")
    cli_log(f"Names replaced: {', '.join(map(str, name_counts))}")
    cli_log(f"Operation completed successfully. New project location: {dst_root}")


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
