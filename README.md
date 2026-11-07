# solis-hoval-dashboard-controller

A Flask web dashboard and energy manager that connects a Solis PV inverter with a Hoval UltraSource Comfort 8 heat pump (TopTronic E controller).

## Supported Devices

- Solis S6-EH3P(15-20)K-H 3-phase hybrid inverter
- Hoval Ultrasource Comfort B heatpump with TopTronic® E controller and a Hoval Gateway Module for Modbus access
- Battery connected to the inverter (doesn't matter what kind of battery, is controlled through the inverter)

## What the application does

The application runs one background control loop and one web server.

**Solis inverter (read only)**
- Reads PV power, AC power, grid power, battery power and state of charge, household load, inverter temperature, status, and energy totals via Modbus TCP.
- Writes each reading to an InfluxDB 1.x database (default database `solis`, measurement `solis_inverter`).

**Hybrid energy management**
- Calculates the surplus as grid feed-in plus battery charging power.
- Switches the Hoval heat pump into SG-Ready "overload" (Smart Grid systembus preferred mode) when the surplus is at least `TRIGGER_SURPLUS_W` and the battery is at or above `BATTERY_MIN_SOC`.
- Keeps the overload mode for at least `MIN_RUN_TIME_SEC` and switches it off when the surplus drops below `STOP_SURPLUS_W` or the battery falls below the minimum SoC minus 5 %.
- If the Solis inverter cannot be reached, the heat pump is set back to normal operation.

**Hoval heat pump (read, and optionally write)**
- Reads a set of datapoints from the WEZ 1 heat generator module over Modbus TCP: generator temperatures, modulation, power, operating hours and switch cycles, one heating circuit, hot water, and Smart Grid status.
- The datapoints are taken from Hoval's Modbus datapoint list. The list is written for a system with one heating circuit and one hot water circuit. Datapoints that are not available return no value and are shown as "—".
- Writing is controlled by `HOVAL_READ_ONLY` in `config.py`. It defaults to `True`, so the application never writes to the heat pump until you set it to `False`.

**Web dashboard**
- Served by Flask on `WEB_PORT` (default 5000).
- Shows Solis and Hoval values, the current control state, and connection status. The page refreshes every 5 seconds.
- Raw data is available as JSON at `/api/status`.

## Requirements

- Python 3.14 or newer (tested with 3.14; the target is 3.15)
- A Solis inverter reachable over Modbus TCP
- A Hoval gateway reachable over Modbus TCP
- InfluxDB 1.x (optional for the dashboard, but the control loop writes to it)

## Setup

```bash
pip install -r requirements.txt
cp config_example.py config.py
```

Edit `config.py`:
- `SOLIS_IP`, `HOVAL_IP`, `INFLUX_HOST`: addresses of your devices
- `HOVAL_READ_ONLY`: keep `True` until you have verified the readings
- thresholds (`TRIGGER_SURPLUS_W`, `STOP_SURPLUS_W`, `BATTERY_MIN_SOC`, `MIN_RUN_TIME_SEC`) to match your system

`config.py` is ignored by Git, so your addresses stay out of the repository.

Start the application:

```bash
python app.py
```

Then open `http://<host>:5000/` in a browser.

## Project structure

| File | Purpose |
| --- | --- |
| `app.py` | Flask app, routes `/` and `/api/status`, starts the control loop |
| `controller.py` | Thread-safe state store, control loop, InfluxDB writes |
| `solis.py` | Solis Modbus reads and register decoding |
| `hoval.py` | Hoval datapoint list, SG-Ready switching, read-only guard |
| `templates/index.html`, `static/` | Dashboard page, styles, and polling script |
| `config_example.py` | Template for the local `config.py` |

## Safety notes

- The application is not a certified safety system. It changes the heat pump operating mode automatically, so check the behavior on your system before enabling writes.
- Keep `HOVAL_READ_ONLY = True` while you test readings.
- Verify each Hoval datapoint on your own installation. Some values depend on the sensors that are actually connected.

## Developer note

This application was heavily developed with the help of a KI. 

## License

See [LICENSE](LICENSE).
