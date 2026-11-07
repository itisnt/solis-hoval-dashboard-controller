SOLIS_IP = "ip of your solis inverter"
SOLIS_PORT = 502
SOLIS_SLAVE = 1
SOLIS_FRAME_DELAY = 0.35  # Datalogger needs at least 300ms between requests

HOVAL_IP = "ip of your Hoval Modbus Gateway"
HOVAL_PORT = 502
HOVAL_SLAVE = 1
HOVAL_READ_ONLY = True

INFLUX_HOST = "ip of your influxdb host"
INFLUX_PORT = 8086
INFLUX_DATABASE = "solis"
INFLUX_MEASUREMENT = "solis_inverter"

BATTERY_MIN_SOC = 80
TRIGGER_SURPLUS_W = 2500
STOP_SURPLUS_W = 200
INTERVAL_SEC = 60
MIN_RUN_TIME_SEC = 20 * 60

WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
