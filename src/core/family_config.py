from dataclasses import dataclass


@dataclass(frozen=True)
class FamilyConfig:
    label: str
    openocd_target: str
    flash_command: str
    rdp_command: str
    flash_base_address: str


FAMILY_MAP: dict[str, FamilyConfig] = {
    "STM32F0 / F1": FamilyConfig(
        label="STM32F0 / F1",
        openocd_target="target/stm32f1x.cfg",
        flash_command="flash write_image erase",
        rdp_command="stm32f1x lock 0",
        flash_base_address="0x08000000",
    ),
    "STM32F2 / F4": FamilyConfig(
        label="STM32F2 / F4",
        openocd_target="target/stm32f4x.cfg",
        flash_command="flash write_image erase",
        rdp_command="stm32f2x lock 0",
        flash_base_address="0x08000000",
    ),
    "STM32F7": FamilyConfig(
        label="STM32F7",
        openocd_target="target/stm32f7x.cfg",
        flash_command="flash write_image erase",
        rdp_command="stm32f7x lock 0",
        flash_base_address="0x08000000",
    ),
    "STM32G0": FamilyConfig(
        label="STM32G0",
        openocd_target="target/stm32g0x.cfg",
        flash_command="flash write_image erase",
        rdp_command="stm32l4x lock 0",
        flash_base_address="0x08000000",
    ),
    "STM32G4 / L4": FamilyConfig(
        label="STM32G4 / L4",
        openocd_target="target/stm32l4x.cfg",
        flash_command="flash write_image erase",
        rdp_command="stm32l4x lock 0",
        flash_base_address="0x08000000",
    ),
    "STM32H7": FamilyConfig(
        label="STM32H7",
        openocd_target="target/stm32h7x.cfg",
        flash_command="flash write_image erase",
        rdp_command="stm32h7x lock 0",
        flash_base_address="0x08000000",
    ),
    "STM32L0 / L1": FamilyConfig(
        label="STM32L0 / L1",
        openocd_target="target/stm32lx.cfg",
        flash_command="flash write_image erase",
        rdp_command="stm32lx lock 0",
        flash_base_address="0x08000000",
    ),
}


def get_families() -> list[str]:
    return list(FAMILY_MAP.keys())


def get_config(family_label: str) -> FamilyConfig:
    if family_label not in FAMILY_MAP:
        raise KeyError(f"Unknown MCU family: '{family_label}'")
    return FAMILY_MAP[family_label]
