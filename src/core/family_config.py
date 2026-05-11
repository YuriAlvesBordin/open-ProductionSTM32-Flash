from dataclasses import dataclass


@dataclass(frozen=True)
class FamilyConfig:
    label: str
    target_cfg: str
    flash_base: str
    lock_cmd: str
    unlock_cmd: str
    read_cmd: str


FAMILY_MAP: dict[str, FamilyConfig] = {
    "STM32F0/F1": FamilyConfig(
        label="STM32F0/F1",
        target_cfg="target/stm32f1x.cfg",
        flash_base="0x08000000",
        lock_cmd="stm32f1x lock 0",
        unlock_cmd="stm32f1x unlock 0",
        read_cmd="stm32f1x options_read 0",
    ),
    "STM32F2/F4": FamilyConfig(
        label="STM32F2/F4",
        target_cfg="target/stm32f4x.cfg",
        flash_base="0x08000000",
        lock_cmd="stm32f2x lock 0",
        unlock_cmd="stm32f2x unlock 0",
        read_cmd="stm32f2x options_read 0",
    ),
    "STM32F7": FamilyConfig(
        label="STM32F7",
        target_cfg="target/stm32f7x.cfg",
        flash_base="0x08000000",
        lock_cmd="stm32f2x lock 0",
        unlock_cmd="stm32f2x unlock 0",
        read_cmd="stm32f2x options_read 0",
    ),
    "STM32G0": FamilyConfig(
        label="STM32G0",
        target_cfg="target/stm32g0x.cfg",
        flash_base="0x08000000",
        lock_cmd="stm32l4x option_write 0 0x20 0xffffbb00 0xffffffff; stm32l4x option_load 0",
        unlock_cmd="stm32l4x option_write 0 0x20 0xffffaa00 0xffffffff; stm32l4x option_load 0",
        read_cmd="stm32l4x option_read 0 0x20",
    ),
    "STM32G4/L4": FamilyConfig(
        label="STM32G4/L4",
        target_cfg="target/stm32l4x.cfg",
        flash_base="0x08000000",
        lock_cmd="stm32l4x option_write 0 0x20 0xffffbb00 0xffffffff; stm32l4x option_load 0",
        unlock_cmd="stm32l4x option_write 0 0x20 0xffffaa00 0xffffffff; stm32l4x option_load 0",
        read_cmd="stm32l4x option_read 0 0x20",
    ),
    "STM32H7": FamilyConfig(
        label="STM32H7",
        target_cfg="target/stm32h7x.cfg",
        flash_base="0x08000000",
        lock_cmd="stm32h7x lock 0",
        unlock_cmd="stm32h7x unlock 0",
        read_cmd="stm32h7x options_read 0",
    ),
    "STM32L0/L1": FamilyConfig(
        label="STM32L0/L1",
        target_cfg="target/stm32l0.cfg",
        flash_base="0x08000000",
        lock_cmd="stm32lx lock 0",
        unlock_cmd="stm32lx unlock 0",
        read_cmd="stm32lx options_read 0",
    ),
}

INTERFACE_MAP: dict[str, str] = {
    "ST-Link V2": "interface/stlink.cfg",
    "ST-Link V3": "interface/stlink.cfg",
    "J-Link":     "interface/jlink.cfg",
    "CMSIS-DAP":  "interface/cmsis-dap.cfg",
}


def get_families() -> list[str]:
    return list(FAMILY_MAP.keys())


def get_interfaces() -> list[str]:
    return list(INTERFACE_MAP.keys())


def get_config(family_label: str) -> FamilyConfig:
    if family_label not in FAMILY_MAP:
        raise KeyError(f"Unknown MCU family: '{family_label}'")
    return FAMILY_MAP[family_label]


def get_interface_cfg(interface_label: str) -> str:
    if interface_label not in INTERFACE_MAP:
        raise KeyError(f"Unknown interface: '{interface_label}'")
    return INTERFACE_MAP[interface_label]
