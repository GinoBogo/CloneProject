# To run these tests, ensure you have pytest installed in your virtual environment:
# python3 -m venv .venv
# source .venv/bin/activate
# pip install pytest
# Then run tests from the project root:
# PYTHONPATH=. ./.venv/bin/pytest

import sys
import pytest
import os
import shutil
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


# Test replace_in_contents
def test_replace_in_contents(tmp_path, mock_logger):
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("This is an old_name project.")
    replace_in_contents(file_path, "old_name", "new_name", mock_logger)
    assert file_path.read_text() == "This is an new_name project."
    mock_logger.assert_called_with(f"Updated contents of: {file_path}")


def test_replace_in_contents_binary_file(tmp_path, mock_logger):
    # Create a dummy binary file (e.g., a few null bytes)
    binary_file_path = tmp_path / "binary.bin"
    binary_file_path.write_bytes(b"\x00\x01\x02\x03")
    replace_in_contents(binary_file_path, "old_name", "new_name", mock_logger)
    # Content should remain unchanged
    assert binary_file_path.read_bytes() == b"\x00\x01\x02\x03"
    mock_logger.assert_called_with(f"Skipped file (likely binary): {binary_file_path}")


# Test copy_and_replace
def test_copy_and_replace(tmp_path, mock_logger):
    src_dir = tmp_path / "src_old_project"
    dst_dir = tmp_path / "dst_new_project"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Content with old_project_name.")
    (src_dir / "old_project_name_dir").mkdir()
    (src_dir / "old_project_name_dir" / "file2.txt").write_text(
        "Another old_project_name file."
    )

    copy_and_replace(
        src_dir, dst_dir, "old_project_name", "new_project_name", mock_logger
    )

    assert dst_dir.exists()
    assert (dst_dir / "file1.txt").read_text() == "Content with new_project_name."
    assert (dst_dir / "new_project_name_dir").exists()
    assert (dst_dir / "new_project_name_dir" / "file2.txt").read_text() == (
        "Another new_project_name file."
    )
    mock_logger.assert_any_call(f"Updated contents of: {dst_dir / 'file1.txt'}")
    mock_logger.assert_any_call(
        f"Updated contents of: {dst_dir / 'new_project_name_dir' / 'file2.txt'}"
    )


# Test validate_inputs
@patch("os.path.isdir")
def test_validate_inputs_valid(mock_isdir):
    mock_isdir.return_value = True  # Mock source directory as existing
    validate_inputs("/src", "/dst", "old", "new")  # Should not raise an error


def test_validate_inputs_missing_fields():
    with pytest.raises(ValueError, match="All fields are required."):
        validate_inputs("", "/dst", "old", "new")
    with pytest.raises(ValueError, match="All fields are required."):
        validate_inputs("/src", "", "old", "new")


def test_validate_inputs_src_dir_not_found():
    with pytest.raises(
        ValueError, match="Source directory 'non_existent_dir' not found."
    ):
        validate_inputs("non_existent_dir", "/dst", "old", "new")


@patch("os.path.isdir")
def test_validate_inputs_identical_src_dst_with_same_name(mock_isdir):
    mock_isdir.return_value = True  # Mock source directory as existing
    with pytest.raises(
        ValueError,
        match="Source and destination directories must be different if "
        "source and destination names are identical.",
    ):
        validate_inputs("/same_dir", "/same_dir", "same_name", "same_name")


# Test cli_logger
def test_cli_logger(capsys):
    cli_logger("CLI log message")
    captured = capsys.readouterr()
    assert captured.out == "CLI log message\n"


# Test run_cli
@patch("clone_project.copy_and_replace")
@patch("clone_project.validate_inputs")
@patch("os.path.exists")
@patch("shutil.rmtree")
@patch("sys.argv", ["clone_project.py", "/src", "/dst", "old", "new"])
def test_run_cli_success(
    mock_rmtree, mock_exists, mock_validate_inputs, mock_copy_and_replace, capsys
):
    mock_exists.return_value = False  # Destination does not exist
    run_cli()
    mock_validate_inputs.assert_called_once_with("/src", "/dst", "old", "new")
    mock_copy_and_replace.assert_called_once_with(
        "/src", "/dst", "old", "new", cli_logger
    )
    captured = capsys.readouterr()
    assert "Copying and replacing..." in captured.out
    assert "Operation completed successfully." in captured.out


@patch("sys.exit")
def test_run_cli_invalid_arguments(mock_exit, capsys, monkeypatch):
    mock_exit.side_effect = SystemExit(1)  # Configure mock_exit to raise SystemExit(1)
    monkeypatch.setattr(sys, "argv", ["clone_project.py", "/src", "/dst", "old"])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        run_cli()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
    mock_exit.assert_called_once_with(1)  # This should now pass
    captured = capsys.readouterr()
    assert "Error: Invalid number of arguments" in captured.out
    assert "Usage: python clone_project.py" in captured.out  # show_help prints this


@patch("clone_project.validate_inputs")
@patch("sys.argv", ["clone_project.py", "/src", "/dst", "old", "new"])
def test_run_cli_validation_error(mock_validate_inputs, capsys):
    mock_validate_inputs.side_effect = ValueError("Test validation error.")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        run_cli()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Test validation error." in captured.out


@patch("clone_project.copy_and_replace")
@patch("clone_project.validate_inputs")
@patch("os.path.exists")
@patch("shutil.rmtree")
@patch("sys.argv", ["clone_project.py", "/src", "/dst", "old", "new"])
def test_run_cli_dst_exists_overwrite(
    mock_rmtree, mock_exists, mock_validate_inputs, mock_copy_and_replace, capsys
):
    mock_exists.return_value = True  # Destination exists
    run_cli()
    mock_rmtree.assert_called_once_with("/dst")
    captured = capsys.readouterr()
    assert (
        "Warning: Destination directory '/dst' already exists. Overwriting..."
        in captured.out
    )


# Test show_help
@patch("sys.exit")
def test_show_help(mock_exit, capsys):
    show_help()
    captured = capsys.readouterr()
    assert (
        "Usage: python clone_project.py <src_dir> <dst_dir> <src_name> <dst_name>"
        in captured.out
    )
    mock_exit.assert_called_once_with(1)
