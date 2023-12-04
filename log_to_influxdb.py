#!/usr/bin/env python3

import time
import datetime

from bme280 import BME280
from ltr559 import LTR559

from influxdb import InfluxDBClient

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus


# Logs the data to your InfluxDB
def send_to_influxdb(measurement, location, timestamp, temperature, pressure, humidity, light):
    payload = [
         {"measurement": measurement,
             "tags": {
                 "location": location,
              },
              "time": timestamp,
              "fields": {
                  "temperature" : temperature,
                  "humidity": humidity,
                  "pressure": pressure,
                  "light": light
              }
          }
        ]
    client.write_points(payload)


# Corrects the relative humidity given a raw and corrected temperature reading
def correct_humidity(humidity, temperature, corr_temperature):
    dewpoint = temperature - ((100 - humidity) / 5)
    corr_humidity = 100 - (5 * (corr_temperature - dewpoint)) - 20
    return min(100, max(0, corr_humidity))


# Set up the BME280 weather sensor
bus = SMBus(1)
bme280 = BME280(i2c_dev=bus)
bme280.setup(mode="forced")

time.sleep(5)

# Set up the light sensor
ltr559 = LTR559()

# Set up InfluxDB
host = '192.168.0.100'  # Change this as necessary
port = 8086
username = 'grafana'  # Change this as necessary
password = 'grafana'  # Change this as necessary
db = 'home'  # Change this as necessary

# InfluxDB client to write to
client = InfluxDBClient(host, port, username, password, db)

measurement = "indoor"  # Change this as necessary
location = "living_room"  # Change this as necessary

timestamp = datetime.datetime.utcnow()

# Read temperature (read twice, as the first reading can be artificially high)
temperature = bme280.get_temperature()
time.sleep(5)
temperature = bme280.get_temperature()

# Calculate corrected temperature
offset = 7.5
corr_temperature = temperature - offset

# Read humidity and correct it with the corrected temperature
humidity = bme280.get_humidity()
corr_humidity = correct_humidity(humidity, temperature, corr_temperature)

# Read pressure
pressure = bme280.get_pressure()

# Read light
light = ltr559.get_lux()

# Log the data
send_to_influxdb(measurement, location, timestamp, corr_temperature, pressure, corr_humidity, light)
