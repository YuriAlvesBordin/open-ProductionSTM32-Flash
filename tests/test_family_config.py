import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from core.family_config import get_families, get_config, get_interfaces, get_interface_cfg


def test_get_families_returns_list():
    families = get_families()
    assert isinstance(families, list)
    assert len(families) > 0


def test_all_families_have_required_fields():
    for label in get_families():
        cfg = get_config(label)
        assert cfg.target_cfg
        assert cfg.lock_cmd
        assert cfg.unlock_cmd
        assert cfg.flash_base.startswith("0x")


def test_get_config_raises_on_unknown_family():
    with pytest.raises(KeyError):
        get_config("STM32UNKNOWN")


def test_stm32f4_config_values():
    cfg = get_config("STM32F2/F4")
    assert "stm32f4x" in cfg.target_cfg
    assert "stm32f2x lock" in cfg.lock_cmd
    assert cfg.flash_base == "0x08000000"


def test_stm32g0_lock_cmd_has_option_write():
    cfg = get_config("STM32G0")
    assert "option_write" in cfg.lock_cmd
    assert "option_load" in cfg.lock_cmd


def test_get_interfaces_returns_list():
    ifaces = get_interfaces()
    assert "ST-Link V2" in ifaces
    assert "J-Link" in ifaces


def test_get_interface_cfg_stlink():
    cfg = get_interface_cfg("ST-Link V2")
    assert "stlink" in cfg


def test_get_interface_cfg_raises_on_unknown():
    with pytest.raises(KeyError):
        get_interface_cfg("UNKNOWN_PROBE")
