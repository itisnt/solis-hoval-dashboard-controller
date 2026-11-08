import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from config import SOLIS_FRAME_DELAY, SOLIS_IP, SOLIS_PORT, SOLIS_SLAVE

# (Startregister, Anzahl Register, [(Name, Offset im Block, Datentyp, Skalierung)])
REGISTER_BLOCKS = [
    (33029, 2, [
        ("pv_energy_total_kwh", 0, "u32", 1),
    ]),
    (33049, 10, [
        ("pv1_voltage_v", 0, "u16", 0.1),
        ("pv1_current_a", 1, "u16", 0.1),
        ("pv2_voltage_v", 2, "u16", 0.1),
        ("pv2_current_a", 3, "u16", 0.1),
        ("pv3_voltage_v", 4, "u16", 0.1),
        ("pv3_current_a", 5, "u16", 0.1),
        ("pv4_voltage_v", 6, "u16", 0.1),
        ("pv4_current_a", 7, "u16", 0.1),
        ("pv_total_dc_power_w", 8, "u32", 1),
    ]),
    (33071, 26, [
        ("ac_active_power_w", 8, "s32", 1),
        ("inverter_temperature_c", 22, "s16", 0.1),
        ("inverter_status", 24, "u16", 1),
    ]),
    (33115, 7, [
        *[(f"fault_code_{i}", i, "u16", 1) for i in range(1, 6)],
        ("operating_status", 6, "u16", 1),
    ]),
    (33126, 23, [
        ("grid_power_w", 4, "s32", 1),
        ("battery_charge_direction", 9, "u16", 1),
        ("battery_soc_pct", 13, "u16", 1),
        ("household_load_w", 21, "u16", 1),
    ]),
    (33149, 2, [
        ("battery_power_w", 0, "s32", 1),
    ]),
    (33161, 18, [
        ("battery_charge_total_kwh", 0, "u32", 1),
        ("battery_discharge_total_kwh", 4, "u32", 1),
        ("grid_import_total_kwh", 8, "u32", 1),
        ("grid_export_total_kwh", 12, "u32", 1),
        ("load_total_kwh", 16, "u32", 1),
    ]),
]


def _decode_fields(regs, fields):
    values = {}
    for name, offset, kind, scale in fields:
        if kind == "u16":
            raw = regs[offset]
        elif kind == "s16":
            raw = regs[offset] - 0x10000 if regs[offset] & 0x8000 else regs[offset]
        else:
            raw = (regs[offset] << 16) | regs[offset + 1]
            if kind == "s32" and raw & 0x80000000:
                raw -= 0x100000000
        values[name] = round(raw * scale, 3)
    return values


async def _read_block(client, address, count):
    result = await client.read_input_registers(address=address, count=count, device_id=SOLIS_SLAVE)
    await asyncio.sleep(SOLIS_FRAME_DELAY)
    if result.isError():
        raise ModbusException(f"Register {address} ({count}) nicht lesbar: {result}")
    return result.registers


async def read_solis_data():
    client = AsyncModbusTcpClient(SOLIS_IP, port=SOLIS_PORT, timeout=10)
    try:
        await client.connect()
        if not client.connected:
            logging.error("Verbindung zu Solis fehlgeschlagen.")
            return None

        data = {}
        for address, count, fields in REGISTER_BLOCKS:
            regs = await _read_block(client, address, count)
            data.update(_decode_fields(regs, fields))
        for i in range(1, 5):
            data[f"pv{i}_power_w"] = round(data[f"pv{i}_voltage_v"] * data[f"pv{i}_current_a"], 1)

        # 0 = Battery wird geladen, 1 = Batterie wird entladen
        if data["battery_charge_direction"] == 1:
            data["battery_power_w"] = (data["battery_power_w"]) * -1

        return data
    except (ModbusException, OSError) as e:
        logging.error(f"Fehler bei Solis-Abfrage: {e}")
        return None
    finally:
        client.close()
