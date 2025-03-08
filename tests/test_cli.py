"""Test suite for the command-line interface functionality."""

import io
import ipaddress
from unittest.mock import patch

import pytest

from netenum.__main__ import get_cidrs_from_stdin, main


def test_get_cidrs_from_stdin() -> None:
    """Test reading CIDR ranges from stdin."""
    with patch("sys.stdin", io.StringIO("192.168.0.0/24\n10.0.0.0/8\n")):
        cidrs = get_cidrs_from_stdin()
        assert cidrs == ["192.168.0.0/24", "10.0.0.0/8"]


def test_get_cidrs_empty_input() -> None:
    """Test handling of empty input."""
    with patch("sys.stdin", io.StringIO("")):
        cidrs = get_cidrs_from_stdin()
        assert cidrs == []


def test_get_cidrs_whitespace() -> None:
    """Test handling of whitespace input."""
    with patch("sys.stdin", io.StringIO("  \n\t\n")):
        cidrs = get_cidrs_from_stdin()
        assert cidrs == []


def test_main_basic_output(capsys) -> None:
    """Test basic output functionality."""
    input_data = "192.168.0.0/30\n"
    expected = "192.168.0.0\n192.168.0.1\n192.168.0.2\n192.168.0.3\n"

    with patch("sys.stdin", io.StringIO(input_data)), patch("sys.argv", ["netenum"]):
        main()
        captured = capsys.readouterr()
        assert captured.out == expected


def test_main_random_order(capsys) -> None:
    """Test output with random ordering."""
    input_data = "192.168.0.0/24\n"
    expected_addresses = {str(ipaddress.IPv4Address(addr)) for addr in range(0xC0A80000, 0xC0A80100)}
    with patch("sys.stdin", io.StringIO(input_data)), patch("sys.argv", ["netenum", "-r"]):
        main()
        output_lines = set(capsys.readouterr().out.splitlines())
        assert len(output_lines) == 256
        assert output_lines == expected_addresses


def test_main_invalid_input(capsys) -> None:
    """Test handling of invalid input."""
    input_data = "invalid\n"
    with patch("sys.stdin", io.StringIO(input_data)), patch("sys.argv", ["netenum"]), pytest.raises(
        SystemExit
    ) as exc_info:
        main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.err


def test_main_empty_input(capsys) -> None:
    """Test handling of empty input."""
    with patch("sys.stdin", io.StringIO("")), patch("sys.argv", ["netenum"]), pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: No CIDR ranges provided" in captured.err
