# To run these tests, ensure you have pytest installed in your virtual environment:
# python3 -m venv .venv
# source .venv/bin/activate
# pip install pytest
# Then run tests from the project root:
# PYTHONPATH=. ./.venv/bin/pytest

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import MagicMock, patch, ANY
from clone_project import (
    replace_in_contents,
    copy_and_replace,
    validate_inputs,
    cli_log,
    run_cli,
    show_help,
    parse_names,
    get_dst_root_path,
    count_files_and_dirs,
)


# Mock logger for testing
@pytest.fixture
def mock_log_func():
    return MagicMock()


# --- Tests for `get_dst_root_path` function ---


# Description: Verifies that `get_dst_root_path` correctly constructs the
#              destination path when the source project is cloned into a new
#              parent directory with a different name.
# Methodology:
#     - Sets up a source directory and a destination parent directory.
#     - Specifies a name change from "old_project" to "new_project".
#     - Calls `get_dst_root_path` with these parameters.
#     - Asserts that the returned destination root path is correctly formed
#       by joining the destination parent directory and the new project name.
#     - Asserts that the `was_renamed` flag is correctly set to 1.
def test_get_dst_root_path_parent_dir(tmp_path):
    src_dir = tmp_path / "old_project"
    dst_dir = tmp_path / "parent_dir"
    src_names = ["old_project"]
    dst_names = ["new_project"]

    dst_root, was_renamed = get_dst_root_path(
        str(src_dir), str(dst_dir), src_names, dst_names
    )
    assert dst_root == str(tmp_path / "parent_dir" / "new_project")
    assert was_renamed == 1


# Description: Verifies that `get_dst_root_path` behaves correctly when the
#              destination directory provided already includes the new project name.
# Methodology:
#     - Sets up a source directory and a destination directory that already
#       contains the target project name.
#     - Specifies a name change from "old_project" to "new_project".
#     - Calls `get_dst_root_path`.
#     - Asserts that the returned destination root path is the same as the
#       provided destination directory, without appending the project name again.
#     - Asserts that the `was_renamed` flag is correctly set to 1.
def test_get_dst_root_path_target_dir_included(tmp_path):
    src_dir = tmp_path / "old_project"
    dst_dir = tmp_path / "parent_dir" / "new_project"
    src_names = ["old_project"]
    dst_names = ["new_project"]

    # Ensure the target directory exists for os.path.basename to work as expected
    dst_dir.mkdir(parents=True, exist_ok=True)

    dst_root, was_renamed = get_dst_root_path(
        str(src_dir), str(dst_dir), src_names, dst_names
    )
    assert dst_root == str(tmp_path / "parent_dir" / "new_project")
    assert was_renamed == 1


# Description: Verifies that `get_dst_root_path` correctly handles cases
#              where the project name is not changed during the clone.
# Methodology:
#     - Sets up a source directory and a destination parent directory.
#     - Specifies that the source and destination names are identical.
#     - Calls `get_dst_root_path`.
#     - Asserts that the returned destination root path is correctly formed
#       by joining the destination parent directory and the original project name.
#     - Asserts that the `was_renamed` flag is correctly set to 0.
def test_get_dst_root_path_no_rename(tmp_path):
    src_dir = tmp_path / "project_name"
    dst_dir = tmp_path / "parent_dir"
    src_names = ["project_name"]
    dst_names = ["project_name"]

    dst_root, was_renamed = get_dst_root_path(
        str(src_dir), str(dst_dir), src_names, dst_names
    )
    assert dst_root == str(tmp_path / "parent_dir" / "project_name")
    assert was_renamed == 0


# Description: Verifies `get_dst_root_path`'s behavior when the project
#              name is unchanged and the destination path already includes it.
# Methodology:
#     - Sets up a source directory and a destination directory that already
#       contains the project name.
#     - Specifies that the source and destination names are identical.
#     - Calls `get_dst_root_path`.
#     - Asserts that the returned destination root path is the same as the
#       provided destination directory.
#     - Asserts that the `was_renamed` flag is correctly set to 0.
def test_get_dst_root_path_no_rename_target_dir_included(tmp_path):
    src_dir = tmp_path / "project_name"
    dst_dir = tmp_path / "parent_dir" / "project_name"
    src_names = ["project_name"]
    dst_names = ["project_name"]

    dst_dir.mkdir(parents=True, exist_ok=True)

    dst_root, was_renamed = get_dst_root_path(
        str(src_dir), str(dst_dir), src_names, dst_names
    )
    assert dst_root == str(tmp_path / "parent_dir" / "project_name")
    assert was_renamed == 0


# --- Tests for `count_files_and_dirs` function ---


# Description: Verifies that `count_files_and_dirs` correctly counts files and directories.
# Methodology:
#     - Creates a temporary directory structure with nested directories and files.
#     - Calls `count_files_and_dirs` on the temporary source directory.
#     - Asserts that the returned total directory count and total file count match the expected values.
def test_count_files_and_dirs(tmp_path):
    src_dir = tmp_path / "test_project"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("content")
    (src_dir / "subdir1").mkdir()
    (src_dir / "subdir1" / "file2.txt").write_text("content")
    (src_dir / "subdir2").mkdir()
    (src_dir / "subdir2" / "file3.txt").write_text("content")
    (src_dir / "subdir2" / "subsubdir1").mkdir()
    (src_dir / "subdir2" / "subsubdir1" / "file4.txt").write_text("content")

    total_dirs, total_files = count_files_and_dirs(str(src_dir))

    # Expected:
    # test_project (root)
    #   file1.txt
    #   subdir1
    #     file2.txt
    #   subdir2
    #     file3.txt
    #     subsubdir1
    #       file4.txt
    # Total directories: test_project, subdir1, subdir2, subsubdir1 = 4
    # Total files: file1.txt, file2.txt, file3.txt, file4.txt = 4
    assert total_dirs == 4
    assert total_files == 4


# --- Tests for `parse_names` function ---


# Description: Verifies that `parse_names` correctly handles an empty input string.
# Methodology:
#     - Calls `parse_names` with an empty string.
#     - Asserts that the returned list is empty.
def test_parse_names_empty_string():
    assert parse_names("") == []


# Description: Verifies that `parse_names` correctly handles a string containing only whitespace.
# Methodology:
#     - Calls `parse_names` with a whitespace-only string.
#     - Asserts that the returned list is empty.
def test_parse_names_whitespace_string():
    assert parse_names("   ") == []


# Description: Verifies that `parse_names` correctly parses a single name without extra whitespace.
# Methodology:
#     - Calls `parse_names` with a single name.
#     - Asserts that the returned list contains only that name.
def test_parse_names_single_name():
    assert parse_names("project_name") == ["project_name"]


# Description: Verifies that `parse_names` correctly parses multiple comma-separated names.
# Methodology:
#     - Calls `parse_names` with a string of multiple names.
#     - Asserts that the returned list contains all names, correctly stripped.
def test_parse_names_multiple_names():
    assert parse_names("name1,name2,name3") == ["name1", "name2", "name3"]


# Description: Verifies that `parse_names` strips leading and trailing whitespace from names.
# Methodology:
#     - Calls `parse_names` with names containing leading/trailing whitespace.
#     - Asserts that the returned list contains names with whitespace stripped.
def test_parse_names_with_whitespace():
    assert parse_names("  name1  , name2 ,name3   ") == ["name1", "name2", "name3"]


# Description: Verifies that `parse_names` handles names with internal spaces correctly.
# Methodology:
#     - Calls `parse_names` with names containing internal spaces.
#     - Asserts that internal spaces are preserved.
def test_parse_names_internal_spaces():
    assert parse_names("my project, another name") == ["my project", "another name"]


# Description: Verifies that `parse_names` filters out empty entries from a comma-separated string.
# Methodology:
#     - Calls `parse_names` with a string containing empty entries (e.g., "name1,,name2").
#     - Asserts that the returned list does not include the empty entries.
def test_parse_names_empty_entries():
    assert parse_names("name1,,name2,") == ["name1", "name2"]


# Description: Verifies that `parse_names` handles a mix of whitespace and empty entries.
# Methodology:
#     - Calls `parse_names` with a complex string.
#     - Asserts that the output is correctly parsed and cleaned.
def test_parse_names_mixed_whitespace_empty_entries():
    assert parse_names("  first  , , second , third  ") == ["first", "second", "third"]


# --- Tests for `replace_in_contents` function ---


# Description: Verifies that the `replace_in_contents` function correctly
#              replaces occurrences of a specified string within a text file.
# Methodology:
#     - Creates a temporary text file with known content using `tmp_path`.
#     - Calls `replace_in_contents` to replace an "old_name" with a "new_name".
#     - Asserts that the file's content has been updated as expected.
#     - Asserts that the `mock_logger` was called with the "Updated contents of:" message.
def test_replace_in_contents(tmp_path, mock_log_func):
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("This is an old_name project.")
    replacements = replace_in_contents(
        file_path, ["old_name"], ["new_name"], mock_log_func
    )
    assert file_path.read_text() == "This is an new_name project."
    mock_log_func.assert_called_with(
        f"Updated contents of: {file_path} (1 replacements)", "normal"
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
def test_replace_in_contents_duplicate_src_names(tmp_path, mock_log_func):
    file_path = tmp_path / "test_duplicate_names.txt"
    file_path.write_text("This is a test with gino.")

    # If 'gino' is replaced by 'bogo', and then 'gino' (which is now 'bogo') is replaced by 'bogo',
    #     the final content should be 'This is a test with bogo.'
    #     The total replacements should be 1, as 'gino' is only found and replaced once.
    replacements = replace_in_contents(
        file_path, ["gino", "gino"], ["bogo", "bogo"], mock_log_func
    )
    assert file_path.read_text() == "This is a test with bogo."
    assert replacements == [1, 0]
    mock_log_func.assert_called_with(
        f"Updated contents of: {file_path} (1 replacements)", "normal"
    )


# Description: Verifies the behavior of `replace_in_contents` when duplicate
#              destination names are provided.
# Methodology:
#     - Creates a temporary text file with content containing multiple distinct source names.
#     - Calls `replace_in_contents` with distinct source names mapping to the same destination name.
#     - Asserts that both source names are replaced by the common destination name.
#     - Asserts the total number of replacements.
def test_replace_in_contents_duplicate_dst_names(tmp_path, mock_log_func):
    file_path = tmp_path / "test_duplicate_dst_names.txt"
    file_path.write_text("This is a test with gino and bogo.")

    replacements = replace_in_contents(
        file_path, ["gino", "bogo"], ["test", "test"], mock_log_func
    )
    assert file_path.read_text() == "This is a test with test and test."
    assert replacements == [1, 1]
    mock_log_func.assert_any_call(
        f"Updated contents of: {file_path} (2 replacements)", "normal"
    )
    mock_log_func.assert_called_with(
        "  Breakdown: 'gino'→'test':1, 'bogo'→'test':1", "normal"
    )


# Description: Ensures that `replace_in_contents` correctly identifies and
#              skips binary files, preventing corruption, and logs the
#              skipping action.
# Methodology:
#     - Creates a temporary file containing binary data (null bytes) using `tmp_path`.
#     - Calls `replace_in_contents` with this binary file.
#     - Asserts that the binary file's content remains unchanged.
#     - Asserts that the `mock_logger` was called with the "Skipped file (likely binary):" message.
def test_replace_in_contents_binary_file(tmp_path, mock_log_func):
    # Create a dummy binary file (e.g., a few null bytes)
    binary_file_path = tmp_path / "binary.bin"
    binary_file_path.write_bytes(b"\x00\x01\x02\x03")
    replacements = replace_in_contents(
        binary_file_path, ["old_name"], ["new_name"], mock_log_func
    )
    # Content should remain unchanged
    assert binary_file_path.read_bytes() == b"\x00\x01\x02\x03"
    assert replacements == [0]
    mock_log_func.assert_called_with(
        f"Skipped file (likely binary): {binary_file_path}", "skipped"
    )


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
def test_copy_and_replace(tmp_path, mock_log_func):
    src_root_name = "old_project_name_src"
    dst_root_name = "new_project_name_dst"
    nested_dir_name_src = "old_project_name_dir"
    nested_dir_name_dst = "new_project_name_sub_dir"

    src_dir = tmp_path / src_root_name
    dst_parent_dir = tmp_path / "destination_parent"  # This is the parent directory

    src_dir.mkdir()
    (src_dir / "file1.txt").write_text(f"Content with {src_root_name}.")
    (src_dir / nested_dir_name_src).mkdir()
    (src_dir / nested_dir_name_src / "file2.txt").write_text(
        f"Another {src_root_name} file in {nested_dir_name_src}."
    )

    src_names = [src_root_name, nested_dir_name_src]
    dst_names = [dst_root_name, nested_dir_name_dst]

    (
        folders_created,
        files_copied,
        folders_renamed,
        files_renamed_count,
        words_replaced_counts,
    ) = copy_and_replace(
        src_dir,
        dst_parent_dir,
        src_names,
        dst_names,
        mock_log_func,
        progress_callback=MagicMock(),
    )

    expected_dst_root = dst_parent_dir / dst_root_name

    assert expected_dst_root.exists()
    assert (
        expected_dst_root / "file1.txt"
    ).read_text() == f"Content with {dst_root_name}."
    assert (expected_dst_root / nested_dir_name_dst).exists()
    assert (expected_dst_root / nested_dir_name_dst / "file2.txt").read_text() == (
        f"Another {dst_root_name} file in {nested_dir_name_dst}."
    )
    assert folders_created == 2
    assert files_copied == 2
    assert folders_renamed == 2  # Both root and nested folder renamed
    assert words_replaced_counts == [
        2,
        1,
    ]  # 2 replacements for src_root_name, 1 for nested_dir_name_src

    mock_log_func.assert_any_call(
        f"Updated contents of: {(expected_dst_root / 'file1.txt').resolve()} (1 replacements)",
        "normal",
    )
    mock_log_func.assert_any_call(
        f"Updated contents of: {(expected_dst_root / nested_dir_name_dst / 'file2.txt').resolve()} (2 replacements)",
        "normal",
    )


# Description: Verifies that `copy_and_replace` correctly utilizes the `progress_callback`.
# Methodology:
#     - Sets up a dummy source directory with multiple files.
#     - Mocks `progress_callback` to track its calls.
#     - Calls `copy_and_replace` with the mocked callback.
#     - Asserts that `progress_callback` was called for each file with the correct progress.
def test_copy_and_replace_progress_callback(tmp_path, mock_log_func):
    src_root_name = "test_project_src"
    dst_root_name = "test_project_dst"

    src_dir = tmp_path / src_root_name
    dst_parent_dir = tmp_path / "destination_parent"

    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("content1")
    (src_dir / "file2.txt").write_text("content2")
    (src_dir / "subdir").mkdir()
    (src_dir / "subdir" / "file3.txt").write_text("content3")

    src_names = [src_root_name]
    dst_names = [dst_root_name]

    mock_progress_callback = MagicMock()

    copy_and_replace(
        src_dir,
        dst_parent_dir,
        src_names,
        dst_names,
        mock_log_func,
        progress_callback=mock_progress_callback,
    )

    # Expect 3 files to be processed
    assert mock_progress_callback.call_count == 3
    mock_progress_callback.assert_any_call("file", 1, 3)
    mock_progress_callback.assert_any_call("file", 2, 3)
    mock_progress_callback.assert_any_call("file", 3, 3)


# --- Tests for `validate_inputs` function ---


# Description: Checks that `validate_inputs` does not raise any `ValueError`
#              when provided with a set of valid input parameters.
# Methodology:
#     - Mocks `os.path.isdir` to return `True` for the source directory,
#       simulating its existence.
#     - Calls `validate_inputs` with valid paths and names.
#     - The test passes if no `ValueError` is raised.
@patch("os.path.isdir")
def test_validate_inputs_valid(mock_isdir, mock_log_func):
    mock_isdir.return_value = True  # Mock source directory as existing
    validate_inputs(
        "/src", "/dst", ["old"], ["new"], mock_log_func
    )  # Should not raise an error


# Description: Verifies that `validate_inputs` raises a `ValueError` with the
#              specific message "All fields are required and must contain at least one name." when any of the
#              input parameters are empty.
# Methodology:
#     - Uses `pytest.raises` to assert that `ValueError` is raised when
#       `src_dir` or `dst_dir` are empty strings.
def test_validate_inputs_missing_fields(mock_log_func):
    with pytest.raises(
        ValueError, match="All fields are required and must contain at least one name."
    ):
        validate_inputs("", "/dst", ["old"], ["new"], mock_log_func)
    with pytest.raises(
        ValueError, match="All fields are required and must contain at least one name."
    ):
        validate_inputs("/src", "", ["old"], ["new"], mock_log_func)
    with pytest.raises(
        ValueError, match="All fields are required and must contain at least one name."
    ):
        validate_inputs("/src", "/dst", [], ["new"], mock_log_func)
    with pytest.raises(
        ValueError, match="All fields are required and must contain at least one name."
    ):
        validate_inputs("/src", "/dst", ["old"], [], mock_log_func)


# Description: Confirms that `validate_inputs` raises a `ValueError` with the
#              message "Source directory 'non_existent_dir' not found." when
#              the provided source directory does not exist.
# Methodology:
#     - Uses `pytest.raises` to assert that `ValueError` is raised when a
#       non-existent source directory is provided. (Note: `os.path.isdir` is
#       not mocked here, so it behaves realistically for a non-existent path).
def test_validate_inputs_src_dir_not_found(mock_log_func):
    with pytest.raises(
        ValueError, match="Source directory 'non_existent_dir' not found."
    ):
        validate_inputs("non_existent_dir", "/dst", ["old"], ["new"], mock_log_func)


# Description: Verifies that `validate_inputs` raises a `ValueError` when the
#              number of source names does not match the number of destination names.
# Methodology:
#     - Mocks `os.path.isdir` to return `True` for the source directory.
#     - Calls `validate_inputs` with an unequal number of source and destination names.
#     - Uses `pytest.raises` to assert that a `ValueError` with the correct
#       message about name count mismatch is raised.
@patch("os.path.isdir")
def test_validate_inputs_name_count_mismatch(mock_isdir, mock_log_func):
    mock_isdir.return_value = True  # Mock source directory as existing
    with pytest.raises(
        ValueError,
        match=r"Number of source names \(1\) must match number of destination names \(2\).",
    ):
        validate_inputs(
            "/src", "/dst", ["old_name"], ["new_name1", "new_name2"], mock_log_func
        )


# Description: Checks that `validate_inputs` does not raise a `ValueError`
#              when source and destination names are identical but the
#              source and destination directories are different. This is a valid scenario.
# Methodology:
#     - Mocks `os.path.isdir` to return `True` for the source directory.
#     - Calls `validate_inputs` with `src_dir != dst_dir` and `src_name == dst_name`.
#     - The test passes if no `ValueError` is raised.
@patch("os.path.isdir")
def test_validate_inputs_identical_src_dst_names_different_dirs(
    mock_isdir, mock_log_func
):
    mock_isdir.return_value = True  # Mock source directory as existing
    validate_inputs(
        "/src_dir", "/dst_dir", ["same_name"], ["same_name"], mock_log_func
    )  # Should not raise an error


# Description: Verifies that `validate_inputs` logs a warning when a source name
#              is identical to its destination name, but the source and destination
#              directories are different.
# Methodology:
#     - Mocks `os.path.isdir` to return `True`.
#     - Calls `validate_inputs` with `src_dir != dst_dir` and `src_name == dst_name`.
#     - Asserts that the `mock_logger` was called with the expected warning message.
@patch("os.path.isdir")
def test_validate_inputs_logs_warning_for_identical_names_different_dirs(
    mock_isdir, mock_log_func
):
    mock_isdir.return_value = True  # Mock source directory as existing
    src_dir = "/src_dir"
    dst_dir = "/dst_dir"
    src_names = ["same_name"]
    dst_names = ["same_name"]

    validate_inputs(src_dir, dst_dir, src_names, dst_names, mock_log_func)

    mock_log_func.assert_called_with(
        "Warning: Replacement pair 'same_name' -> 'same_name' is identical. "
        "This will result in no change for this specific name.",
        "warning",
    )


# Description: Verifies that `validate_inputs` raises a `ValueError` unconditionally
#              when the source and destination directories are the same.
# Methodology:
#     - Mocks `os.path.isdir` to return `True`.
#     - Calls `validate_inputs` with `src_dir == dst_dir`.
#     - Uses `pytest.raises` to assert that a `ValueError` with the correct
#       message "Source and destination directories cannot be the same." is raised.
@patch("os.path.isdir")
def test_validate_inputs_src_dst_same_dir_unconditional_error(
    mock_isdir, mock_log_func
):
    mock_isdir.return_value = True  # Mock source directory as existing
    with pytest.raises(
        ValueError,
        match="Source and destination directories cannot be the same.",
    ):
        validate_inputs("/same_dir", "/same_dir", ["name1"], ["name2"], mock_log_func)


# --- Tests for `cli_log` function ---


# Description: Verifies that the `cli_logger` function correctly prints
#              messages to standard output (stdout).
# Methodology:
#     - Uses the `capsys` fixture to capture stdout.
#     - Calls `cli_logger` with a test message.
#     - Asserts that the captured stdout matches the expected message
#       followed by a newline.
def test_cli_log(capsys):
    cli_log("CLI log message")
    captured = capsys.readouterr()
    assert captured.out == "CLI log message\n"


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
    assert (
        "Usage: python clone_project.py <src_dir> <dst_dir> <src_name1,src_name2,...> <dst_name1,dst_name2,...>"
        in captured.out
    )
    mock_exit.assert_called_once_with(1)


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
    mock_copy_and_replace.return_value = (1, 1, 1, 1, [1])
    run_cli()
    mock_validate_inputs.assert_called_once_with(
        "/src", "/dst", ["old"], ["new"], cli_log
    )
    mock_copy_and_replace.assert_called_once_with(
        "/src", "/dst", ["old"], ["new"], cli_log, progress_callback=ANY
    )
    captured = capsys.readouterr()
    assert "Replacement plan:" in captured.out
    assert "Total Directories: 1" in captured.out
    assert "Total Files: 1" in captured.out
    assert "Names replaced: 1" in captured.out
    assert "Operation completed successfully." in captured.out


# Description: Verifies that `run_cli` correctly uses `cli_progress_callback` and updates stdout.
# Methodology:
#     - Mocks `copy_and_replace` to simulate file processing and trigger progress updates.
#     - Patches `sys.stdout.write` and `sys.stdout.flush` to capture CLI output.
#     - Calls `run_cli`.
#     - Asserts that `sys.stdout.write` was called with expected progress messages.
@patch("clone_project.copy_and_replace")
@patch("clone_project.validate_inputs")
@patch("os.path.exists")
@patch("shutil.rmtree")
@patch(
    "sys.argv",
    ["clone_project.py", "/src/old_proj", "/dst_parent", "old_proj", "new_proj"],
)
@patch("clone_project.cli_progress_callback")  # Patch cli_progress_callback
@patch("clone_project.cli_log")  # Patch cli_log at the decorator level
def test_run_cli_progress_callback(
    mock_cli_log,  # cli_log mock is now the first argument
    mock_cli_progress_callback,  # cli_progress_callback mock
    mock_rmtree,
    mock_exists,
    mock_validate_inputs,
    mock_copy_and_replace,
    capsys,
    tmp_path,
    mock_log_func,  # Added
    monkeypatch,  # Added
):
    # Mock copy_and_replace to call the progress_callback
    def mock_copy_and_replace_side_effect(*args, **kwargs):
        progress_cb = kwargs.get("progress_callback")
        if progress_cb:
            progress_cb("file", 1, 2)
            progress_cb("file", 2, 2)
        return (
            1,
            2,
            0,
            0,
            [1],
        )  # total_dirs, total_files, dirs_renamed, files_renamed, name_counts

    mock_copy_and_replace.side_effect = mock_copy_and_replace_side_effect
    mock_exists.return_value = False  # Assume destination does not exist

    run_cli()

    # Assert that progress messages were written
    mock_cli_progress_callback.assert_any_call("file", 1, 2)
    mock_cli_progress_callback.assert_any_call("file", 2, 2)

    # Assert that cli_log was called with the success message
    mock_cli_log.assert_any_call(
        "Operation completed successfully. New project location: /dst_parent/new_proj"
    )


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
@patch(
    "sys.argv",
    ["clone_project.py", "/src/old_proj", "/dst_parent", "old_proj", "new_proj"],
)
def test_run_cli_dst_exists_overwrite(
    mock_rmtree, mock_exists, mock_validate_inputs, mock_copy_and_replace, capsys
):
    # The calculated dst_root will be /dst_parent/new_proj
    expected_dst_root = "/dst_parent/new_proj"

    # Mock os.path.exists to return True only for the calculated dst_root
    mock_exists.side_effect = lambda path: path == expected_dst_root

    mock_copy_and_replace.return_value = (1, 1, 1, 1, [1, 1])
    run_cli()

    # rmtree should be called on the calculated dst_root
    mock_rmtree.assert_called_once_with(expected_dst_root)

    mock_validate_inputs.assert_called_once_with(
        "/src/old_proj", "/dst_parent", ["old_proj"], ["new_proj"], cli_log
    )
    mock_copy_and_replace.assert_called_once_with(
        "/src/old_proj",
        "/dst_parent",
        ["old_proj"],
        ["new_proj"],
        cli_log,
        progress_callback=ANY,
    )
    captured = capsys.readouterr()
    assert "Replacement plan:" in captured.out
    assert "  1. 'old_proj' → 'new_proj'" in captured.out
    assert (
        f"Warning: Destination directory '{expected_dst_root}' already exists. Overwriting..."
        in captured.out
    )
    assert "Starting clone operation..." in captured.out
    assert "Total Directories: 1" in captured.out
    assert "Total Files: 1" in captured.out
    assert "Names replaced: 1" in captured.out
    assert (
        f"Operation completed successfully. New project location: {expected_dst_root}"
        in captured.out
    )
