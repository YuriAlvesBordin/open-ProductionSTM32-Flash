import subprocess
import sys
import os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from core.openocd_runner import OpenOCDRunner


def _mock_result(returncode: int, stdout: str = "", stderr: str = ""):
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


@patch("core.openocd_runner.subprocess.run")
def test_success_on_zero_returncode(mock_run):
    mock_run.return_value = _mock_result(0, stdout="Programming done.")
    result = OpenOCDRunner("openocd").run("iface.cfg", "target.cfg", ["init"])
    assert result.success is True
    assert "Programming done." in result.output


@patch("core.openocd_runner.subprocess.run")
def test_failure_on_nonzero_returncode(mock_run):
    mock_run.return_value = _mock_result(1, stderr="Error: target not found")
    result = OpenOCDRunner("openocd").run("iface.cfg", "target.cfg", ["init"])
    assert result.success is False


@patch("core.openocd_runner.subprocess.run")
def test_failure_when_error_in_stderr_despite_zero_returncode(mock_run):
    mock_run.return_value = _mock_result(0, stderr="Error: LIBUSB_ERROR_ACCESS")
    result = OpenOCDRunner("openocd").run("iface.cfg", "target.cfg", ["init"])
    assert result.success is False


@patch("core.openocd_runner.subprocess.run")
def test_success_when_error_word_in_informational_stderr(mock_run):
    """'Error' como substring em mensagem informativa NAO deve causar falha.

    A regex ^Error: so bate em linhas que COMECAM com 'Error:'. Mensagens
    como 'Info: Error level: debug' ou 'No Error occurred' nao devem
    acionar o flag de falha.
    """
    mock_run.return_value = _mock_result(
        0, stderr="Info: Error level: debug\nProgramming done."
    )
    result = OpenOCDRunner("openocd").run("iface.cfg", "target.cfg", ["init"])
    assert result.success is True


@patch("core.openocd_runner.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="openocd", timeout=120))
def test_timeout_returns_failure(mock_run):
    result = OpenOCDRunner("openocd").run("iface.cfg", "target.cfg", ["init"])
    assert result.success is False
    assert "Timeout" in result.output


@patch("core.openocd_runner.subprocess.run", side_effect=FileNotFoundError)
def test_file_not_found_returns_failure(mock_run):
    result = OpenOCDRunner("/bad/path/openocd").run("iface.cfg", "target.cfg", ["init"])
    assert result.success is False
    assert "not found" in result.output
