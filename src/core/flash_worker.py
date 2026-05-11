from PyQt6.QtCore import QThread, pyqtSignal
from core.openocd_runner import OpenOCDRunner
from core.family_config import FamilyConfig


RDP_LEVEL_VALUES = {
    "Level 1 (0xBB) — Reversible": "level1",
    "Level 2 (0xCC) — IRREVERSIBLE": "level2",
}


class FlashWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool)

    def __init__(
        self,
        firmware_path: str,
        interface_cfg: str,
        family: FamilyConfig,
        rdp_label: str,
        openocd_path: str = "openocd",
    ) -> None:
        super().__init__()
        self._firmware_path = firmware_path
        self._interface_cfg = interface_cfg
        self._family = family
        self._rdp_label = rdp_label
        self._runner = OpenOCDRunner(openocd_path)

    def _emit(self, message: str, step: int) -> None:
        self.log.emit(message)
        self.progress.emit(step)

    def run(self) -> None:
        self._emit("Connecting to target...", 5)

        connect_result = self._runner.run(
            self._interface_cfg,
            self._family.openocd_target,
            ["init", "reset halt"],
        )
        self.log.emit(connect_result.output)

        if not connect_result.success:
            self.log.emit("ERROR: Could not connect to target. Check cable and probe.")
            self.finished.emit(False)
            return

        self._emit("Target connected. Writing firmware...", 20)

        flash_cmd = (
            f"{self._family.flash_command} "
            f"{self._firmware_path} "
            f"{self._family.flash_base_address}"
        )
        flash_result = self._runner.run(
            self._interface_cfg,
            self._family.openocd_target,
            ["init", "reset halt", flash_cmd],
        )
        self.log.emit(flash_result.output)

        if not flash_result.success:
            self.log.emit("ERROR: Firmware write failed.")
            self.finished.emit(False)
            return

        self._emit("Firmware written. Verifying...", 60)

        verify_result = self._runner.run(
            self._interface_cfg,
            self._family.openocd_target,
            ["init", f"verify_image {self._firmware_path} {self._family.flash_base_address}"],
        )
        self.log.emit(verify_result.output)

        if not verify_result.success:
            self.log.emit("ERROR: Verification failed. Flash may be corrupted.")
            self.finished.emit(False)
            return

        self._emit("Verification passed. Activating RDP...", 80)

        rdp_result = self._runner.run(
            self._interface_cfg,
            self._family.openocd_target,
            ["init", "reset halt", self._family.rdp_command, "reset run"],
        )
        self.log.emit(rdp_result.output)

        if not rdp_result.success:
            self.log.emit("ERROR: RDP activation failed.")
            self.finished.emit(False)
            return

        self._emit("RDP activated. Device is protected and running.", 100)
        self.finished.emit(True)
