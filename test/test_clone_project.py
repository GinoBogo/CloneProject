# To run these tests, ensure you have pytest installed in your virtual environment:
# python3 -m venv .venv
# source .venv/bin/activate
# pip install pytest
# Then run tests from the project root:
# PYTHONPATH=. ./.venv/bin/pytest

import pytest
from unittest.mock import MagicMock, patch
from clone_project import (
    replace_in_contents,
    copy_and_replace,
    validate_inputs,
    cli_logger,
    run_cli,
    show_help,
)


# Mock logger for testing
@pytest.fixture
def mock_logger():
    return MagicMock()


# --- Tests for `replace_in_contents` function ---

# Description: Verifies that the `replace_in_contents` function correctly
#              replaces occurrences of a specified string within a text file.
# Methodology:
#     - Creates a temporary text file with known content using `tmp_path`.
#     - Calls `replace_in_contents` to replace an "old_name" with a "new_name".
#     - Asserts that the file's content has been updated as expected.
#     - Asserts that the `mock_logger` was called with the "Updated contents of:" message.
def test_replace_in_contents(tmp_path, mock_logger):
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("This is an old_name project.")
    replacements = replace_in_contents(file_path, ["old_name"], ["new_name"], mock_logger)
    assert file_path.read_text() == "This is an new_name project."
    assert replacements == [1]
    mock_logger.assert_called_with(
        f"Updated contents of: {file_path} (1 replacements)"
    )


# Description: Verifies the behavior of `replace_in_contents` when duplicate
#              source names are provided, demonstrating sequential replacement.
# Methodology:
#     - Creates a temporary text file with content containing the source name.
#     - Calls `replace_in_contents` with a list containing the same source name twice,
#       mapping to different destination names.
#     - Asserts that the replacements are applied sequentially, and the final
#       content reflects the last replacement for that source string.
#     - Asserts the total number of replacements.
def test_replace_in_contents_duplicate_src_names(tmp_path, mock_logger):
    file_path = tmp_path / "test_duplicate_names.txt"
    file_path.write_text("This is a test with gino.")
    
    # If 'gino' is replaced by 'bogo', and then 'gino' (which is now 'bogo') is replaced by 'bogo',
    # the final content should be 'This is a test with bogo.'
    # The total replacements should be 1, as 'gino' is only found and replaced once.
    replacements = replace_in_contents(file_path, ["gino", "gino"], ["bogo", "bogo"], mock_logger)
    assert file_path.read_text() == "This is a test with bogo."
    assert replacements == [1, 0]
    mock_logger.assert_called_with(
        f"Updated contents of: {file_path} (1 replacements)"
    )


# Description: Verifies the behavior of `replace_in_contents` when duplicate
#              destination names are provided.
# Methodology:
#     - Creates a temporary text file with content containing multiple distinct source names.
#     - Calls `replace_in_contents` with distinct source names mapping to the same destination name.
#     - Asserts that both source names are replaced by the common destination name.
#     - Asserts the total number of replacements.
def test_replace_in_contents_duplicate_dst_names(tmp_path, mock_logger):
    file_path = tmp_path / "test_duplicate_dst_names.txt"
    file_path.write_text("This is a test with gino and bogo.")
    
    replacements = replace_in_contents(file_path, ["gino", "bogo"], ["test", "test"], mock_logger)
    assert file_path.read_text() == "This is a test with test and test."
    assert replacements == [1, 1]
    mock_logger.assert_any_call(
        f"Updated contents of: {file_path} (2 replacements)"
    )
    mock_logger.assert_called_with(
        "  Breakdown: 'gino'→'test':1, 'bogo'→'test':1"
    )


# Description: Ensures that `replace_in_contents` correctly identifies and
#              skips binary files, preventing corruption, and logs the
#              skipping action.
# Methodology:
#     - Creates a temporary file containing binary data (null bytes) using `tmp_path`.
#     - Calls `replace_in_contents` with this binary file.
#     - Asserts that the binary file's content remains unchanged.
#     - Asserts that the `mock_logger` was called with the "Skipped file (likely binary):" message.
def test_replace_in_contents_binary_file(tmp_path, mock_logger):
    # Create a dummy binary file (e.g., a few null bytes)
    binary_file_path = tmp_path / "binary.bin"
    binary_file_path.write_bytes(b"\x00\x01\x02\x03")
    replacements = replace_in_contents(
        binary_file_path, ["old_name"], ["new_name"], mock_logger
    )
    # Content should remain unchanged
    assert binary_file_path.read_bytes() == b"\x00\x01\x02\x03"
    assert replacements == [0]
    mock_logger.assert_called_with(f"Skipped file (likely binary): {binary_file_path}", level="skipped")


# --- Tests for `copy_and_replace` function ---

# Description: Validates the end-to-end functionality of `copy_and_replace`,
#              including directory creation, file copying, renaming of
#              files/directories, and content replacement within files.
# Methodology:
#     - Sets up a dummy source directory structure with nested files and
#       directories, some containing the "old_project_name".
#     - Calls `copy_and_replace` to clone this structure to a destination,
#       replacing "old_project_name" with "new_project_name".
#     - Asserts that the destination directory and its renamed
#       subdirectories/files exist.
#     - Asserts that the content of the copied text files has been
#       correctly updated.
#     - Asserts that the `mock_logger` was called with "Updated contents of:"
#       messages for the modified files.
def test_copy_and_replace(tmp_path, mock_logger):
    src_dir = tmp_path / "src_old_project"
    dst_dir = tmp_path / "dst_new_project"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Content with old_project_name.")
    (src_dir / "old_project_name_dir").mkdir()
    (src_dir / "old_project_name_dir" / "file2.txt").write_text(
        "Another old_project_name file."
    )

    folders_created, files_copied, folders_renamed, words_replaced_counts = copy_and_replace(
        src_dir, dst_dir, ["old_project_name"], ["new_project_name"], mock_logger
    )

    assert dst_dir.exists()
    assert (dst_dir / "file1.txt").read_text() == "Content with new_project_name."
    assert (dst_dir / "new_project_name_dir").exists()
    assert (dst_dir / "new_project_name_dir" / "file2.txt").read_text() == (
        "Another new_project_name file."
    )
    assert folders_created == 2
    assert files_copied == 2
    assert folders_renamed == 1
    assert words_replaced_counts == [2]
    mock_logger.assert_any_call(
        f"Updated contents of: {(dst_dir / 'file1.txt').resolve()} (1 replacements)"
    )
    mock_logger.assert_any_call(
        f"Updated contents of: {(dst_dir / 'new_project_name_dir' / 'file2.txt').resolve()} (1 replacements)"
    )


# --- Tests for `validate_inputs` function ---

# Description: Checks that `validate_inputs` does not raise any `ValueError`
#              when provided with a set of valid input parameters.
# Methodology:
#     - Mocks `os.path.isdir` to return `True` for the source directory,
#       simulating its existence.
#     - Calls `validate_inputs` with valid paths and names.
#     - The test passes if no `ValueError` is raised.
@patch("os.path.isdir")
def test_validate_inputs_valid(mock_isdir, mock_logger):
    mock_isdir.return_value = True  # Mock source directory as existing
    validate_inputs("/src", "/dst", ["old"], ["new"], mock_logger)  # Should not raise an error


# Description: Verifies that `validate_inputs` raises a `ValueError` with the
#              specific message "All fields are required." when any of the
#              input parameters are empty.
# Methodology:
#     - Uses `pytest.raises` to assert that `ValueError` is raised when
#       `src_dir` or `dst_dir` are empty strings.
def test_validate_inputs_missing_fields(mock_logger):
    with pytest.raises(ValueError, match="All fields are required and must contain at least one name."):
        validate_inputs("", "/dst", ["old"], ["new"], mock_logger)
    with pytest.raises(ValueError, match="All fields are required and must contain at least one name."):
        validate_inputs("/src", "", ["old"], ["new"], mock_logger)
    with pytest.raises(ValueError, match="All fields are required and must contain at least one name."):
        validate_inputs("/src", "/dst", [], ["new"], mock_logger)
    with pytest.raises(ValueError, match="All fields are required and must contain at least one name."):
        validate_inputs("/src", "/dst", ["old"], [], mock_logger)


# Description: Confirms that `validate_inputs` raises a `ValueError` with the
#              message "Source directory 'non_existent_dir' not found." when
#              the provided source directory does not exist.
# Methodology:
#     - Uses `pytest.raises` to assert that `ValueError` is raised when a
#       non-existent source directory is provided. (Note: `os.path.isdir` is
#       not mocked here, so it behaves realistically for a non-existent path).
def test_validate_inputs_src_dir_not_found(mock_logger):
    with pytest.raises(
        ValueError, match="Source directory 'non_existent_dir' not found."
    ):
        validate_inputs("non_existent_dir", "/dst", ["old"], ["new"], mock_logger)


# Description: Verifies that `validate_inputs` raises a `ValueError` when the
#              number of source names does not match the number of destination names.
# Methodology:
#     - Mocks `os.path.isdir` to return `True` for the source directory.
#     - Calls `validate_inputs` with an unequal number of source and destination names.
#     - Uses `pytest.raises` to assert that a `ValueError` with the correct
#       message about name count mismatch is raised.
@patch("os.path.isdir")
def test_validate_inputs_name_count_mismatch(mock_isdir, mock_logger):
    mock_isdir.return_value = True  # Mock source directory as existing
    with pytest.raises(
        ValueError,
        match=r"Number of source names \(1\) must match number of destination names \(2\).",
    ):
        validate_inputs("/src", "/dst", ["old_name"], ["new_name1", "new_name2"], mock_logger)


# Description: Checks that `validate_inputs` does not raise a `ValueError`
#              when source and destination names are identical but the
#              source and destination directories are different. This is a valid scenario.
# Methodology:
#     - Mocks `os.path.isdir` to return `True` for the source directory.
#     - Calls `validate_inputs` with `src_dir != dst_dir` and `src_name == dst_name`.
#     - The test passes if no `ValueError` is raised.
@patch("os.path.isdir")
def test_validate_inputs_identical_src_dst_names_different_dirs(mock_isdir, mock_logger):
    mock_isdir.return_value = True  # Mock source directory as existing
    validate_inputs("/src_dir", "/dst_dir", ["same_name"], ["same_name"], mock_logger) # Should not raise an error


# Description: Verifies that `validate_inputs` logs a warning when a source name
#              is identical to its destination name, but the source and destination
#              directories are different.
# Methodology:
#     - Mocks `os.path.isdir` to return `True`.
#     - Calls `validate_inputs` with `src_dir != dst_dir` and `src_name == dst_name`.
#     - Asserts that the `mock_logger` was called with the expected warning message.
@patch("os.path.isdir")
def test_validate_inputs_logs_warning_for_identical_names_different_dirs(mock_isdir, mock_logger):
    mock_isdir.return_value = True  # Mock source directory as existing
    src_dir = "/src_dir"
    dst_dir = "/dst_dir"
    src_names = ["same_name"]
    dst_names = ["same_name"]
    
    validate_inputs(src_dir, dst_dir, src_names, dst_names, mock_logger)
    
    mock_logger.assert_called_with(
        "Warning: Replacement pair 'same_name' -> 'same_name' is identical. "
        "This will result in no change for this specific name.",
        level="warning"
    )


# Description: Verifies that `validate_inputs` raises a `ValueError` unconditionally
#              when the source and destination directories are the same.
# Methodology:
#     - Mocks `os.path.isdir` to return `True`.
#     - Calls `validate_inputs` with `src_dir == dst_dir`.
#     - Uses `pytest.raises` to assert that a `ValueError` with the correct
#       message "Source and destination directories cannot be the same." is raised.
@patch("os.path.isdir")
def test_validate_inputs_src_dst_same_dir_unconditional_error(mock_isdir, mock_logger):
    mock_isdir.return_value = True  # Mock source directory as existing
    with pytest.raises(
        ValueError,
        match="Source and destination directories cannot be the same.",
    ):
        validate_inputs("/same_dir", "/same_dir", ["name1"], ["name2"], mock_logger)


# --- Tests for `cli_logger` function ---

# Description: Verifies that the `cli_logger` function correctly prints
#              messages to standard output (stdout).
# Methodology:
#     - Uses the `capsys` fixture to capture stdout.
#     - Calls `cli_logger` with a test message.
#     - Asserts that the captured stdout matches the expected message
#       followed by a newline.
def test_cli_logger(capsys):
    cli_logger("CLI log message")
    captured = capsys.readouterr()
    assert captured.out == "CLI log message\n"


# --- Tests for `run_cli` function ---

# Description: Tests the successful execution path of `run_cli` when all
#              inputs are valid and the destination does not initially exist.
# Methodology:
#     - Mocks `os.path.exists` to return `False` (destination does not exist).
#     - Mocks `validate_inputs`, `copy_and_replace`, and `shutil.rmtree` to
#       control their behavior.
#     - Patches `sys.argv` to provide valid CLI arguments.
#     - Calls `run_cli`.
#     - Asserts that `validate_inputs` and `copy_and_replace` were called
#       once with the correct arguments.
#     - Asserts that `shutil.rmtree` was *not* called.
#     - Asserts that the correct success messages are printed to stdout.
@patch("clone_project.copy_and_replace")
@patch("clone_project.validate_inputs")
@patch("os.path.exists")
@patch("shutil.rmtree")
@patch("sys.argv", ["clone_project.py", "/src", "/dst", "old", "new"])
def test_run_cli_success(
    mock_rmtree, mock_exists, mock_validate_inputs, mock_copy_and_replace, capsys
):
    mock_copy_and_replace.return_value = (1, 1, 1, [1])
    run_cli()
    mock_validate_inputs.assert_called_once_with("/src", "/dst", ["old"], ["new"], cli_logger)
    mock_copy_and_replace.assert_called_once_with(
        "/src", "/dst", ["old"], ["new"], cli_logger
    )
    captured = capsys.readouterr()
    assert "Replacement plan:" in captured.out
    assert "  1. 'old' → 'new'" in captured.out
    assert "Starting clone operation..." in captured.out
    assert "Directories created: 1" in captured.out
    assert "Files copied: 1" in captured.out
    assert "Names replaced: 1" in captured.out
    assert "Operation completed successfully." in captured.out


# Description: Verifies that `run_cli` correctly handles an insufficient
#              number of command-line arguments by logging an error,
#              displaying help, and exiting with status code 1.
# Methodology:
#     - Mocks `sys.exit` to raise `SystemExit(1)` when called.
#     - Uses `monkeypatch` to set `sys.argv` with missing arguments.
#     - Uses `pytest.raises(SystemExit)` to catch the program exit.
#     - Asserts that `sys.exit` was called with `1`.
#     - Asserts that the "Error: Invalid number of arguments" and "Usage:"
#       messages are printed to stdout.
@patch("sys.exit")
def test_run_cli_invalid_arguments(mock_exit, capsys, monkeypatch):
    mock_exit.side_effect = SystemExit(1)  # Configure mock_exit to raise SystemExit(1)
    monkeypatch.setattr("sys.argv", ["clone_project.py", "/src", "/dst", "old"])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        run_cli()
        assert pytest_wrapped_e.type is SystemExit
        assert pytest_wrapped_e.value.code == 1
    mock_exit.assert_called_once_with(1)  # This should now pass
    captured = capsys.readouterr()
    assert "Error: Invalid number of arguments" in captured.out
    assert "Usage: python clone_project.py" in captured.out


# Description: Checks that `run_cli` gracefully handles `ValueError`
#              exceptions raised by `validate_inputs`, logging the error
#              and exiting with status code 1.
# Methodology:
#     - Mocks `validate_inputs` to raise a `ValueError`.
#     - Patches `sys.argv` with valid-looking arguments that would trigger
#       the validation error.
#     - Uses `pytest.raises(SystemExit)` to catch the program exit.
#     - Asserts that the specific validation error message is printed to stdout.
@patch("clone_project.validate_inputs")
@patch("sys.argv", ["clone_project.py", "/src", "/dst", "old", "new"])
def test_run_cli_validation_error(mock_validate_inputs, capsys):
    mock_validate_inputs.side_effect = ValueError("Test validation error.")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        run_cli()
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Test validation error." in captured.out


# Description: Tests the scenario where the destination directory already
#              exists in CLI mode, ensuring it's removed before cloning proceeds.
# Methodology:
#     - Mocks `os.path.exists` to return `True` (destination exists).
#     - Mocks `shutil.rmtree` to verify its call.
#     - Patches `sys.argv` to provide valid CLI arguments.
#     - Calls `run_cli`.
#     - Asserts that `shutil.rmtree` was called once with the destination path.
#     - Asserts that the "Warning: Destination directory already exists. Overwriting..."
#       message is printed to stdout.
@patch("clone_project.copy_and_replace")
@patch("clone_project.validate_inputs")
@patch("os.path.exists")
@patch("shutil.rmtree")
@patch("sys.argv", ["clone_project.py", "/src", "/dst", "old", "new"])
def test_run_cli_dst_exists_overwrite(
    mock_rmtree, mock_exists, mock_validate_inputs, mock_copy_and_replace, capsys
):
    mock_exists.return_value = True  # Destination exists
    mock_copy_and_replace.return_value = (1, 1, 1, [1]) # Add return value for copy_and_replace
    run_cli()
    mock_rmtree.assert_called_once_with("/dst")
    mock_validate_inputs.assert_called_once_with("/src", "/dst", ["old"], ["new"], cli_logger) # Update mock call
    mock_copy_and_replace.assert_called_once_with( # Add assertion for copy_and_replace
        "/src", "/dst", ["old"], ["new"], cli_logger
    )
    captured = capsys.readouterr()
    assert "Replacement plan:" in captured.out
    assert "  1. 'old' → 'new'" in captured.out
    assert (
        "Warning: Destination directory '/dst' already exists. Overwriting..."
        in captured.out
    )
    assert "Starting clone operation..." in captured.out
    assert "Directories created: 1" in captured.out
    assert "Files copied: 1" in captured.out
    assert "Names replaced: 1" in captured.out
    assert "Operation completed successfully." in captured.out


# --- Tests for `show_help` function ---

# Description: Verifies that the `show_help` function prints the correct
#              usage message to stdout and then exits the program with
#              status code 1.
# Methodology:
#     - Mocks `sys.exit` to prevent actual program termination.
#     - Uses `capsys` to capture stdout.
#     - Calls `show_help`.
#     - Asserts that the captured stdout contains the expected "Usage:" message.
#     - Asserts that `sys.exit` was called once with `1`.
@patch("sys.exit")
def test_show_help(mock_exit, capsys):
    show_help()
    captured = capsys.readouterr()
    assert "Usage: python clone_project.py <src_dir> <dst_dir> <src_name1,src_name2,...> <dst_name1,dst_name2,...>" in captured.out
    mock_exit.assert_called_once_with(1)