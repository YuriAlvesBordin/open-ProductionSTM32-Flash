from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from core.openocd_runner import OpenOCDRunner
from core.family_config import FamilyConfig


class FlashWorker(QThread):
    log      = pyqtSignal(str, str)
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(
        self,
        openocd_path: str,
        firmware_path: str,
        interface_cfg: str,
        family: FamilyConfig,
        enable_rdp: bool,
    ) -> None:
        super().__init__()
        self._runner       = OpenOCDRunner(openocd_path)
        self._firmware     = firmware_path
        self._interface    = interface_cfg
        self._family       = family
        self._enable_rdp   = enable_rdp

    def _firmware_format(self) -> str | None:
        suffix = Path(self._firmware).suffix.lower()
        if suffix == ".bin":
            return "bin"
        if suffix in {".hex", ".ihex"}:
            return "ihex"
        if suffix == ".elf":
            return "elf"
        return None

    def _flash_commands(self, escaped: str, fmt: str) -> tuple[str, str]:
        if fmt == "bin":
            write  = f"flash write_image erase {escaped} {self._family.flash_base} bin"
            verify = f"flash verify_image {escaped} {self._family.flash_base} bin"
        else:
            write  = f"flash write_image erase {escaped}"
            verify = f"flash verify_image {escaped}"
        return write, verify

    def run(self) -> None:
        self.log.emit("Starting flash process...", "info")
        self.progress.emit(5)

        # fix: valida existência do arquivo antes de acionar o OpenOCD
        firmware_file = Path(self._firmware)
        if not firmware_file.exists():
            self.finished.emit(
                False,
                f"Firmware file not found: {self._firmware}"
            )
            return

        # fix: valida formato
        fmt = self._firmware_format()
        if fmt is None:
            self.finished.emit(False, "Unsupported firmware format. Use .bin, .hex or .elf.")
            return

        escaped = self._firmware.replace("\\", "/")

        self.log.emit("Checking connection to target...", "info")
        result = self._runner.run(self._interface, self._family.target_cfg, ["init", "reset init", "exit"])
        self.log.emit(result.output, "info")
        if not result.success:
            self.finished.emit(False, "Connection failed. Check cable and probe.")
            return
        self.log.emit("Target connected.", "ok")
        self.progress.emit(20)

        self.log.emit(f"Writing firmware: {firmware_file.name}", "info")
        write_cmd, verify_cmd = self._flash_commands(escaped, fmt)
        flash_result = self._runner.run(
            self._interface,
            self._family.target_cfg,
            ["init", "reset init", write_cmd, verify_cmd, "reset run", "exit"],
        )
        self.log.emit(flash_result.output, "info")
        if not flash_result.success:
            self.finished.emit(False, "Firmware write or verification failed.")
            return
        self.log.emit("Firmware written and verified.", "ok")
        self.progress.emit(75)

        if self._enable_rdp:
            self.log.emit("Activating RDP Level 1...", "info")
            rdp_cmds = ["init", "reset halt"]
            for part in self._family.lock_cmd.split(";"):
                rdp_cmds.append(part.strip())
            rdp_cmds += ["reset run", "exit"]

            rdp_result = self._runner.run(self._interface, self._family.target_cfg, rdp_cmds)
            self.log.emit(rdp_result.output, "info")
            if not rdp_result.success:
                self.log.emit("WARNING: RDP may not have been activated. Verify manually.", "warn")
            else:
                self.log.emit("RDP Level 1 activated \u2014 firmware is protected.", "ok")
            self.progress.emit(95)
        else:
            self.progress.emit(90)

        self.log.emit("Resetting device...", "info")
        self._runner.run(self._interface, self._family.target_cfg, ["init", "reset run", "exit"])
        self.progress.emit(100)

        final_msg = "Flash completed successfully!"
        if self._enable_rdp:
            final_msg += " RDP activated."
        self.finished.emit(True, final_msg)
