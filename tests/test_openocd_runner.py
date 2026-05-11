import subprocess
from unittest.mock import patch, MagicMock
from src.core.openocd_runner import OpenOCDRunner


def _make_mock_result(returncode: int, stdout: str = "", stderr: str = ""):
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


@patch("src.core.openocd_runner.subprocess.run")
def test_run_returns_success_on_zero_returncode(mock_run):
    mock_run.return_value = _make_mock_result(0, stdout="Programming done.")
    runner = OpenOCDRunner("openocd")
    result = runner.run("iface.cfg", "target.cfg", ["init", "reset halt"])
    assert result.success is True
    assert "Programming done." in result.output


@patch("src.core.openocd_runner.subprocess.run")
def test_run_returns_failure_on_nonzero_returncode(mock_run):
    mock_run.return_value = _make_mock_result(1, stderr="Error: target not found")
    runner = OpenOCDRunner("openocd")
    result = runner.run("iface.cfg", "target.cfg", ["init"])
    assert result.success is False
    assert "Error: target not found" in result.output


@patch("src.core.openocd_runner.subprocess.run")
def test_run_joins_multiple_commands(mock_run):
    mock_run.return_value = _make_mock_result(0)
    runner = OpenOCDRunner("/usr/bin/openocd")
    runner.run("iface.cfg", "target.cfg", ["init", "reset halt", "flash write_image erase fw.bin"])
    call_args = mock_run.call_args[0][0]
    assert "-c" in call_args
    joined = call_args[call_args.index("-c") + 1]
    assert "init" in joined
    assert "reset halt" in joined
