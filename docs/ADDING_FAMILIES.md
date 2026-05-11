# Adding a New MCU Family

This guide explains how to add support for an MCU family that is not yet listed in the tool.

## Step 1 — Find the OpenOCD target file

OpenOCD ships target configuration files for all major STM32 families. On Linux/macOS, they are usually located at:

```
/usr/share/openocd/scripts/target/
```

On Windows, check:

```
C:\Program Files\OpenOCD\share\openocd\scripts\target\
```

Find the `.cfg` file that matches your MCU. Examples:
- `stm32wbx.cfg` → STM32WB
- `stm32u5x.cfg` → STM32U5

## Step 2 — Find the RDP lock command

Search the OpenOCD source or documentation for the `lock` command of your target. It follows the pattern:

```tcl
<family_prefix>x lock <bank_number>
```

Examples:
- STM32WB: `stm32wbx lock 0`
- STM32U5: `stm32l5x lock 0` (uses the same driver)

## Step 3 — Add an entry to `family_config.py`

Open `src/core/family_config.py` and add a new entry to `FAMILY_MAP`:

```python
"STM32WB": FamilyConfig(
    label="STM32WB",
    openocd_target="target/stm32wbx.cfg",
    flash_command="flash write_image erase",
    rdp_command="stm32wbx lock 0",
    flash_base_address="0x08000000",
),
```

That is all. The new family will appear automatically in the UI dropdown on next launch.

## Step 4 — Add a test

Add a test case to `tests/test_family_config.py` to verify the new entry:

```python
def test_stm32wb_config_values():
    cfg = get_config("STM32WB")
    assert "stm32wbx" in cfg.openocd_target
    assert "stm32wbx lock" in cfg.rdp_command
    assert cfg.flash_base_address == "0x08000000"
```
