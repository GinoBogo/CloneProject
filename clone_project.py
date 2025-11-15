#!/usr/bin/env python3
"""Utility to clone a project via CLI or Tkinter GUI.


Author: Gino Bogo
"""

import os
import shutil
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox


def show_help():
    print("Usage: python script.py <src_dir> <dst_dir> <src_name> <dst_name>")
    sys.exit(1)


def replace_in_contents(file_path, src_name, dst_name):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        updated_content = content.replace(src_name, dst_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print(f"Updated contents of: {file_path}")
    except (UnicodeDecodeError, IOError):
        # Skip binary or unreadable files
        print(f"Skipped file: {file_path}")


def copy_and_replace(src_dir, dst_dir, src_name, dst_name):
    # Walk through the source directory
    for root, dirs, files in os.walk(src_dir, topdown=True):
        # Replace directory names
        new_root = re.sub(re.escape(src_name), dst_name, root.replace(src_dir, dst_dir))
        os.makedirs(new_root, exist_ok=True)

        # Replace file names and copy files
        for file in files:
            src_file_path = os.path.join(root, file)
            new_file_name = re.sub(re.escape(src_name), dst_name, file)
            dst_file_path = os.path.join(new_root, new_file_name)
            shutil.copy2(src_file_path, dst_file_path)
            replace_in_contents(dst_file_path, src_name, dst_name)

        # Replace subdirectory names
        for dir in dirs:
            new_dir_name = re.sub(re.escape(src_name), dst_name, dir)
            os.makedirs(os.path.join(new_root, new_dir_name), exist_ok=True)


def run_gui():
    root = tk.Tk()
    root.title("Clone Project")
    root.minsize(600, 600)

    def log(message):
        log_text.configure(state="normal")
        log_text.insert(tk.END, f"{message}\n")
        log_text.see(tk.END)
        log_text.configure(state="disabled")

    def browse_dir(entry):
        path = filedialog.askdirectory()
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def run_clone():
        src_dir = os.path.abspath(src_entry.get().strip())
        dst_dir = os.path.abspath(dst_entry.get().strip())
        src_name = src_name_entry.get().strip()
        dst_name = dst_name_entry.get().strip()

        if not src_dir or not dst_dir or not src_name or not dst_name:
            messagebox.showerror("Missing data", "All fields are required.")
            return

        if not os.path.isdir(src_dir):
            messagebox.showerror(
                "Invalid source", f"Source directory '{src_dir}' not found."
            )
            return

        if os.path.exists(dst_dir):
            overwrite = messagebox.askyesno(
                "Destination exists",
                f"Destination '{dst_dir}' already exists. Overwrite?",
            )
            if not overwrite:
                return
            shutil.rmtree(dst_dir)

        try:
            log("Copying and replacing...")
            copy_and_replace(src_dir, dst_dir, src_name, dst_name)
            log(f"Operation completed successfully. New project location: {dst_dir}")
            messagebox.showinfo("Success", "Project cloned successfully.")
        except Exception as exc:  # pragma: no cover - GUI feedback only
            messagebox.showerror("Error", str(exc))

    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    label_width = 20

    # Source directory
    tk.Label(main_frame, text="Source Directory:", width=label_width, anchor="e").grid(
        row=0, column=0, sticky="e"
    )
    src_entry = tk.Entry(main_frame, width=50)
    src_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")
    tk.Button(main_frame, text="Browse", command=lambda: browse_dir(src_entry)).grid(
        row=0, column=2, padx=5, pady=5
    )

    # Destination directory
    tk.Label(
        main_frame, text="Destination Directory:", width=label_width, anchor="e"
    ).grid(row=1, column=0, sticky="e")
    dst_entry = tk.Entry(main_frame, width=50)
    dst_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")
    tk.Button(main_frame, text="Browse", command=lambda: browse_dir(dst_entry)).grid(
        row=1, column=2, padx=5, pady=5
    )

    # Source name
    tk.Label(main_frame, text="Source Name:", width=label_width, anchor="e").grid(
        row=2, column=0, sticky="e"
    )
    src_name_entry = tk.Entry(main_frame, width=50)
    src_name_entry.grid(row=2, column=1, padx=5, pady=5, sticky="we")

    # Destination name
    tk.Label(main_frame, text="Destination Name:", width=label_width, anchor="e").grid(
        row=3, column=0, sticky="e"
    )
    dst_name_entry = tk.Entry(main_frame, width=50)
    dst_name_entry.grid(row=3, column=1, padx=5, pady=5, sticky="we")

    # Run button
    tk.Button(main_frame, text="Clone Project", command=run_clone).grid(
        row=4, column=0, columnspan=3, pady=(10, 5), sticky="we"
    )

    # Log output
    log_text = tk.Text(main_frame, height=10, state="disabled")
    log_text.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="nsew")

    scrollbar = tk.Scrollbar(main_frame, command=log_text.yview)
    scrollbar.grid(row=5, column=3, sticky="ns")
    log_text.configure(yscrollcommand=scrollbar.set)

    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(5, weight=1)

    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_gui()
        sys.exit(0)

    if len(sys.argv) != 5:
        print("Error: Invalid number of arguments")
        show_help()

    src_dir = os.path.abspath(sys.argv[1])
    dst_dir = os.path.abspath(sys.argv[2])
    src_name = sys.argv[3]
    dst_name = sys.argv[4]

    if not os.path.isdir(src_dir):
        print(f"Error: Source directory '{src_dir}' not found")
        sys.exit(1)

    if os.path.exists(dst_dir):
        print(
            f"Warning: Destination directory '{dst_dir}' already exists. Overwriting..."
        )
        shutil.rmtree(dst_dir)

    print("Copying and replacing...")
    copy_and_replace(src_dir, dst_dir, src_name, dst_name)
    print(f"Operation completed successfully. New project location: {dst_dir}")
