import logging

from pymodbus.client import ModbusTcpClient

from config import HOVAL_IP, HOVAL_PORT, HOVAL_READ_ONLY, HOVAL_SLAVE

SG_SYSTEMBUS_REGISTER = 27545
SG_TRIGGER_REGISTER = 27546

# (Name, Registeradresse, Datentyp, Nachkommastellen) laut Hoval Modbus-Datenpunktliste, Modul WEZ 1
HOVAL_DATAPOINTS = [
    ("smart_grid_systembus", SG_SYSTEMBUS_REGISTER, "u8", 0),
    ("smart_grid_trigger", SG_TRIGGER_REGISTER, "u8", 0),
    ("smart_grid_available_power_kw", 30572, "s16", 2),
    ("outdoor_temp_c", 1477, "s16", 1),
    ("generator_target_c", 18724, "s16", 1),
    ("generator_actual_c", 18725, "s16", 1),
    ("generator_return_c", 18742, "s16", 1),
    ("generator_status", 18722, "u8", 0),
    ("generator_operating_message", 18737, "u8", 0),
    ("generator_modulation_pct", 18726, "u8", 0),
    ("generator_power_kw", 18731, "u32", 1),
    ("generator_el_power_kw", 25611, "s16", 2),
    ("generator_heat_energy_mwh", 1505, "u32", 3),
    ("generator_el_energy_mwh", 25613, "u32", 3),
    ("generator_operating_hours", 1507, "u32", 0),
    ("generator_switch_cycles", 1518, "u32", 0),
    ("hk1_mode", 1478, "u8", 0),
    ("hk1_status", 1501, "u8", 0),
    ("hk1_room_target_c", 1493, "s16", 1),
    ("hk1_flow_target_c", 19562, "s16", 1),
    ("hk1_flow_actual_c", 1513, "s16", 1),
    ("hk1_return_c", 19610, "s16", 1),
    ("hk1_pump", 19706, "u8", 0),
    ("ww_target_c", 1499, "s16", 1),
    ("ww_actual_c", 1500, "s16", 1),
    ("ww_status", 1504, "u8", 0),
    ("ww_charge_pump", 19754, "u8", 0),
]


def _decode(regs, kind, decimals):
    if kind == "u32":
        raw = (regs[0] << 16) | regs[1]
    elif kind == "s16":
        raw = regs[0] - 0x10000 if regs[0] & 0x8000 else regs[0]
    else:
        raw = regs[0]
    return round(raw / 10 ** decimals, decimals) if decimals else raw


def set_sg_ready(enable_overload):
    if HOVAL_READ_ONLY:
        logging.info(f"HOVAL_READ_ONLY aktiv, kein Schreibzugriff (gewünscht: Überladen={enable_overload}).")
        return False
    client = ModbusTcpClient(HOVAL_IP, port=HOVAL_PORT)
    try:
        if not client.connect():
            logging.error("Verbindung zu Hoval Gateway fehlgeschlagen.")
            return False
        res1 = client.write_register(address=SG_TRIGGER_REGISTER, value=2, device_id=HOVAL_SLAVE)
        if res1.isError():
            logging.error(f"Hoval Systembus-Freigabe fehlgeschlagen: {res1}")
            return False
        res2 = client.write_register(address=SG_SYSTEMBUS_REGISTER, value=1 if enable_overload else 0,
                                     device_id=HOVAL_SLAVE)
        if res2.isError():
            logging.error(f"Hoval SG-Ready Umschaltung fehlgeschlagen: {res2}")
            return False
        return True
    except Exception as e:
        logging.error(f"Unerwarteter Fehler bei Hoval-Steuerung: {e}")
        return False
    finally:
        client.close()


def read_hoval_values():
    client = ModbusTcpClient(HOVAL_IP, port=HOVAL_PORT)
    try:
        if not client.connect():
            raise ConnectionError("Verbindung zu Hoval Gateway fehlgeschlagen.")
        values = {}
        for name, address, kind, decimals in HOVAL_DATAPOINTS:
            count = 2 if kind == "u32" else 1
            res = client.read_holding_registers(address=address, count=count, device_id=HOVAL_SLAVE)
            if res.isError():
                logging.warning(f"Hoval Register {address} ({name}) nicht lesbar: {res}")
                values[name] = None
                continue
            values[name] = _decode(res.registers, kind, decimals)
        return values
    finally:
        client.close()
