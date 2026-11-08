import asyncio
import copy
import logging
import threading
import time

from influxdb import InfluxDBClient

from config import (
    BATTERY_MIN_SOC, INFLUX_DATABASE, INFLUX_HOST, INFLUX_MEASUREMENT, INFLUX_PORT, INTERVAL_SEC,
    MIN_RUN_TIME_SEC, STOP_SURPLUS_W, TRIGGER_SURPLUS_W,
)
from hoval import read_hoval_values, set_sg_ready
from solis import read_solis_data


class Store:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = {
            "solis": {"values": None, "updated": None},
            "control": {"total_surplus_w": None, "bat_charge_w": None, "soc": None, "updated": None},
            "hoval": {"overloading": False, "overload_since": None, "registers": None,
                      "registers_error": None, "updated": None},
            "system": {"last_error": None, "started": time.time()},
        }

    def set(self, section, **values):
        with self._lock:
            self._state[section].update(values)

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self._state)


def _write_solis_data(influx, data, is_overloading):
    fields = {k: v for k, v in data.items() if not (k.startswith("fault_code_") and v == 0)}
    fields["hoval_overload"] = int(is_overloading)
    influx.write_points([{"measurement": INFLUX_MEASUREMENT, "fields": fields}])


async def _publish_hoval(store, is_overloading, start_time, now):
    store.set("hoval", overloading=is_overloading, overload_since=start_time, updated=now)
    try:
        registers = await asyncio.to_thread(read_hoval_values)
        store.set("hoval", registers=registers, registers_error=None)
    except Exception as e:
        logging.error(f"Hoval-Statusabfrage fehlgeschlagen: {e}")
        store.set("hoval", registers_error=str(e))


async def _control_loop(store):
    logging.info("Start des Solis-Hoval Hybrid-Energiemanagers...")
    is_overloading = False
    start_time = None

    with InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT, database=INFLUX_DATABASE) as influx:
        while True:
            delay_start_time = time.perf_counter()
            data = await read_solis_data()
            current_time = time.time()

            if data is not None:
                store.set("solis", values=data, updated=current_time)
                store.set("system", last_error=None)
                logging.debug(f"Solis-Werte: {data}")
                try:
                    await asyncio.to_thread(_write_solis_data, influx, data, is_overloading)
                except Exception as e:
                    logging.error(f"Schreiben nach InfluxDB fehlgeschlagen: {e}")
                    store.set("system", last_error=f"InfluxDB: {e}")

                net_surplus = -data["grid_power_w"]
                bat_charge = data["battery_power_w"] if data["battery_power_w"] > 0 else 0
                total_surplus_w = net_surplus + bat_charge
                soc = data["battery_soc_pct"]
                store.set("control", total_surplus_w=total_surplus_w, bat_charge_w=bat_charge,
                          soc=soc, updated=current_time)

                logging.info(f"Battery Charge Level: {soc}%")
                logging.info(f"Grid                : {data['grid_power_w']}W")
                logging.info(f"Grid New            : {data['grid_power_w_new']}W")
                logging.info(f"Bat Laden/Entladen  : {bat_charge}W")
                logging.info(f"Total Überschuss    : {total_surplus_w}W")
                logging.info(f"net_surplus         : {net_surplus}")
                logging.info(f"battery_power_w     : {data['battery_power_w']}W")

                if not is_overloading:
                    if total_surplus_w >= TRIGGER_SURPLUS_W and soc >= BATTERY_MIN_SOC:
                        logging.info("Bedingungen erfüllt (SoC & Leistung). Aktiviere Hoval.")
                        if await asyncio.to_thread(set_sg_ready, True):
                            is_overloading = True
                            start_time = current_time
                    else:
                        await asyncio.to_thread(set_sg_ready, False)

                elif is_overloading:
                    elapsed_time = current_time - start_time

                    if total_surplus_w < STOP_SURPLUS_W or soc < (BATTERY_MIN_SOC - 5):
                        if elapsed_time < MIN_RUN_TIME_SEC:
                            remaining_min = round((MIN_RUN_TIME_SEC - elapsed_time) / 60, 1)
                            logging.info(f"Abschaltkriterium erreicht, aber Mindestlaufzeit aktiv. Noch {remaining_min} Min.")
                            await asyncio.to_thread(set_sg_ready, True)
                        else:
                            logging.info("Mindestlaufzeit rum. Deaktiviere Hoval.")
                            if await asyncio.to_thread(set_sg_ready, False):
                                is_overloading = False
                                start_time = None
                    else:
                        await asyncio.to_thread(set_sg_ready, True)
            else:
                logging.warning("Verbindungsfehler zu Solis. Hoval zur Sicherheit auf Normalbetrieb.")
                store.set("system", last_error="Solis nicht erreichbar")
                await asyncio.to_thread(set_sg_ready, False)
                is_overloading = False
                start_time = None

            await _publish_hoval(store, is_overloading, start_time, current_time)

            elapsed_time = time.perf_counter() - delay_start_time
            sleep_time = INTERVAL_SEC - elapsed_time
            # await asyncio.sleep(INTERVAL_SEC)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                logging.warning("Controller While-Loop took longer than 60s")


async def _run(store):
    try:
        await _control_loop(store)
    except Exception as e:
        logging.exception("Hybrid-Regelung abgebrochen")
        store.set("system", last_error=f"Regelung abgebrochen: {e}")


def start_worker(store):
    thread = threading.Thread(target=lambda: asyncio.run(_run(store)), name="hybrid-control", daemon=True)
    thread.start()
    return thread
