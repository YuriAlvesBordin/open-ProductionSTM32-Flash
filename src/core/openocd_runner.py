import re
import subprocess
from dataclasses import dataclass

# Padrão de erro fatal emitido pelo OpenOCD: linhas que começam com "Error:"
_ERROR_PATTERN = re.compile(r"^Error:", re.MULTILINE | re.IGNORECASE)


@dataclass
class RunResult:
    success: bool
    output: str


class OpenOCDRunner:
    def __init__(self, openocd_path: str = "openocd") -> None:
        self._path = openocd_path

    def run(self, interface_cfg: str, target_cfg: str, commands: list[str]) -> RunResult:
        args = [self._path, "-f", interface_cfg, "-f", target_cfg]
        for cmd in commands:
            args += ["-c", cmd]

        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=120)
            output = result.stdout + result.stderr
            # fix: usa regex para detectar linhas "Error:" do OpenOCD,
            # evitando falso negativo em mensagens que contêm a palavra
            # "Error" como parte de texto informativo (ex: "Error level: Info").
            has_error = bool(_ERROR_PATTERN.search(result.stderr))
            success = result.returncode == 0 and not has_error
            return RunResult(success=success, output=output)
        except subprocess.TimeoutExpired:
            return RunResult(success=False, output="Timeout: OpenOCD took more than 120s")
        except FileNotFoundError:
            return RunResult(success=False, output=f"OpenOCD not found at: {self._path}")
        except Exception as exc:
            return RunResult(success=False, output=str(exc))
