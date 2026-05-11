import pytest
from src.core.family_config import get_families, get_config


def test_get_families_returns_list():
    families = get_families()
    assert isinstance(families, list)
    assert len(families) > 0


def test_all_families_have_required_fields():
    for label in get_families():
        cfg = get_config(label)
        assert cfg.openocd_target
        assert cfg.flash_command
        assert cfg.rdp_command
        assert cfg.flash_base_address.startswith("0x")


def test_get_config_raises_on_unknown_family():
    with pytest.raises(KeyError):
        get_config("STM32UNKNOWN")


def test_stm32f4_config_values():
    cfg = get_config("STM32F2 / F4")
    assert "stm32f4x" in cfg.openocd_target
    assert "stm32f2x lock" in cfg.rdp_command
    assert cfg.flash_base_address == "0x08000000"
