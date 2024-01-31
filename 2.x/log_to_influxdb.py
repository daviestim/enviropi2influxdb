#!/usr/bin/env python3

import time
import datetime

from bme280 import BME280
from ltr559 import LTR559
from pms5003 import PMS5003, ReadTimeoutError as pmsReadTimeoutError
from enviroplus import gas

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus


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

# Set up the PMS5003 particulate sensor
pms5003 = PMS5003()

# Set up InfluxDB
host = '192.168.0.100'  # Change this as necessary
port = 8086
my_token = 'zgQSeYlZSh7u07VuRREzhSLU5BWaNYFkBo6cmjRsV-XB6T-B-RYYL3sw5JbJl2oCQQPXEXMTBrX392PlcubpbA=='
my_org = 'home'
my_bucket = 'home'

# Logs the data to your InfluxDB

with InfluxDBClient(url=host, token=my_token, org=my_org) as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)
def send_to_influxdb(measurement, location, timestamp, temperature, pressure, humidity, light, oxidised, reduced, nh3, pm1, pm25, pm10):
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
                  "light": light,
                  "oxidised": oxidised,
                  "reduced": reduced,
                  "nh3": nh3,
                  "pm1": pm1,
                  "pm25": pm25,
                  "pm10": pm10
              }
          }
        ]
   
    write_api.write(bucket=my_bucket, record=payload)

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

# Read gas data
gas_data = gas.read_all()
oxidised = gas_data.oxidising
reduced = gas_data.reducing
nh3 = gas_data.nh3

# Read data from particulate matter sensor
pmsdata = pms5003.read()
pm1 = pmsdata.pm_ug_per_m3(1.0)
pm25 = pmsdata.pm_ug_per_m3(2.5)
pm10 = pmsdata.pm_ug_per_m3(10)

# Log the data
send_to_influxdb(measurement, location, timestamp, corr_temperature, pressure, corr_humidity, light, oxidised, reduced, nh3, pm1, pm25, pm10)