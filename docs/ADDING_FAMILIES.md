# Adding a New MCU Family

All family-specific data lives in `src/core/family_config.py`. Adding support for a new STM32 family is a single-file change.

## Steps

**1. Find the OpenOCD target config**

Look in your OpenOCD installation under `scripts/target/`. Common examples:
- `stm32wbx.cfg` — STM32WB
- `stm32u5x.cfg` — STM32U5
- `stm32c0x.cfg` — STM32C0

**2. Find the RDP commands**

Check the ST reference manual (RM) for the option byte register address and the RDP byte values. Cross-reference with the OpenOCD source for the correct TCL command. Most newer families use `stm32l4x option_write`.

**3. Add the entry to FAMILY_MAP**

```python
"STM32WB": FamilyConfig(
    label="STM32WB",
    target_cfg="target/stm32wbx.cfg",
    flash_base="0x08000000",
    lock_cmd="stm32l4x option_write 0 0x20 0xffffbb00 0xffffffff; stm32l4x option_load 0",
    unlock_cmd="stm32l4x option_write 0 0x20 0xffffaa00 0xffffffff; stm32l4x option_load 0",
    read_cmd="stm32l4x option_read 0 0x20",
),
```

**4. Add the IDCODE entry to device_detector.py (optional but recommended)**

This enables auto-detection. Find the part number ID in the ST RM (usually in the *Debug and security* or *Device electronic signature* chapter), then add a line to `_IDCODE_TABLE`:

```python
(0x0FFFF000, 0x00495000, "STM32WB"),  # WB55
```

That's it. No other files need to change.
