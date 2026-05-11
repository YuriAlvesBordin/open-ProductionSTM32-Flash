import subprocess
from dataclasses import dataclass


@dataclass
class RunResult:
    success: bool
    output: str


class OpenOCDRunner:
    def __init__(self, openocd_path: str = "openocd") -> None:
        self._openocd_path = openocd_path

    def run(self, interface_cfg: str, target_cfg: str, commands: list[str]) -> RunResult:
        tcl_commands = " ; ".join(commands)
        args = [
            self._openocd_path,
            "-f", interface_cfg,
            "-f", target_cfg,
            "-c", tcl_commands,
        ]
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        return RunResult(success=result.returncode == 0, output=output)
