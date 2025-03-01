import pytest
from unittest.mock import patch
import io
import sys
from netenum.__main__ import main, get_cidrs_from_stdin

def test_get_cidrs_from_stdin():
    with patch('sys.stdin', io.StringIO("192.168.0.0/24\n10.0.0.0/8\n")):
        cidrs = get_cidrs_from_stdin()
        assert cidrs == ["192.168.0.0/24", "10.0.0.0/8"]

def test_get_cidrs_empty_input():
    with patch('sys.stdin', io.StringIO("")):
        cidrs = get_cidrs_from_stdin()
        assert cidrs == []

def test_get_cidrs_whitespace():
    with patch('sys.stdin', io.StringIO("  192.168.0.0/24  \n  \n  10.0.0.0/8  ")):
        cidrs = get_cidrs_from_stdin()
        assert cidrs == ["192.168.0.0/24", "10.0.0.0/8"]

def test_main_basic_output(capsys):
    test_input = "192.168.0.0/30\n"  # Will generate 4 addresses
    with patch('sys.stdin', io.StringIO(test_input)):
        with patch('sys.argv', ['netenum']):
            main()
    
    captured = capsys.readouterr()
    addresses = captured.out.strip().split('\n')
    assert len(addresses) == 4
    assert addresses[0] == "192.168.0.0"
    assert addresses[-1] == "192.168.0.3"

def test_main_random_order(capsys):
    test_input = "192.168.0.0/24\n"
    with patch('sys.stdin', io.StringIO(test_input)):
        with patch('sys.argv', ['netenum', '-r']):
            with patch('random.shuffle') as mock_shuffle:
                main()
                assert mock_shuffle.called

def test_main_invalid_input(capsys):
    test_input = "invalid\n"
    with patch('sys.stdin', io.StringIO(test_input)):
        with patch('sys.argv', ['netenum']):
            with pytest.raises(SystemExit):
                main()
    
    captured = capsys.readouterr()
    assert "Error" in captured.err

def test_main_empty_input(capsys):
    with patch('sys.stdin', io.StringIO("")):
        with patch('sys.argv', ['netenum']):
            with pytest.raises(SystemExit):
                main()
    
    captured = capsys.readouterr()
    assert "Error: No CIDR ranges provided" in captured.err 