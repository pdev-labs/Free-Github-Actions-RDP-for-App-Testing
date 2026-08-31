import pytest
import subprocess
from github_api import check_gh_auth, get_gh_user, run_command, ensure_git_config
from unittest.mock import patch, MagicMock

@patch('subprocess.run')
def test_check_gh_auth_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    # Should not raise SystemExit
    check_gh_auth()

@patch('subprocess.run')
def test_check_gh_auth_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1)
    with pytest.raises(SystemExit) as exc:
        check_gh_auth()
    assert exc.value.code == 1

@patch('subprocess.run')
def test_get_gh_user_success(mock_run):
    mock_run.return_value = MagicMock(stdout="testuser\n")
    user = get_gh_user()
    assert user == "testuser"

@patch('subprocess.run')
def test_get_gh_user_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd')
    with pytest.raises(SystemExit) as exc:
        get_gh_user()
    assert exc.value.code == 1

@patch('subprocess.run')
def test_run_command_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    run_command(["ls"])
    mock_run.assert_called_with(["ls"], cwd=None, check=True, capture_output=False)

@patch('subprocess.run')
def test_run_command_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd')
    with pytest.raises(SystemExit) as exc:
        run_command(["ls"])
    assert exc.value.code == 1
