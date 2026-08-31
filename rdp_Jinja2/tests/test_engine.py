import pytest
from engine import generate_workflow

def test_engine_valid_combinations():
    # Valid combinations should not raise any exceptions
    yaml = generate_workflow("password123", True, "linux", "ubuntu:latest", "amd64", "xfce", "1,2", "", "", "pinggy", "")
    assert "password123" in yaml
    assert "ubuntu-latest" in yaml # ubuntu:latest gets replaced with ubuntu-latest
    assert "actions/cache@v4" in yaml
    assert "pinggy" in yaml

def test_engine_invalid_os():
    with pytest.raises(ValueError, match="Unknown OS choice: invalid_os"):
        generate_workflow("pass", True, "invalid_os", "ubuntu")

def test_engine_no_cache():
    yaml = generate_workflow("pass", False, "linux", "debian:latest", "amd64", "cli")
    assert "actions/cache@v4" not in yaml

def test_engine_custom_iso():
    yaml = generate_workflow("pass", False, "custom_iso", "custom", "amd64", "gui", "", "echo 'custom download'", "pubkey")
    assert "echo 'custom download'" in yaml
    assert "5900" in yaml # VNC port

def test_engine_windows_cli():
    yaml = generate_workflow("pass", False, "windows", "windows-latest", "amd64", "cli")
    assert "port: 22" in yaml or "22" in yaml # Should use SSH port
