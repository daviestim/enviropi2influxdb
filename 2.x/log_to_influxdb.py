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

# Logs the data to your InfluxDB
def send_to_influxdb(measurement, location, timestamp, temperature, pressure, humidity, light, oxidised, reduced, nh3, pm1, pm2_5, pm10):
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
                  "pm2_5": pm2_5,
                  "pm10": pm10
              }
          }
        ]
    #print(payload) # uncomment to see the payload being sent
    write_api.write(bucket=bucket, record=payload)


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
url = 'http://192.168.0.100:8086'  # Change this as necessary
org = 'home' # Change this as necessary
bucket = 'home' # Change this as necessary
token = 'secret token' # Change this as necessary

# InfluxDB client to write to
debug = False # set this to True to see the output being sent by the InfluxDB client
with InfluxDBClient(url=url, token=token, org=org, debug=debug) as client:
    write_api = client.write_api(write_options=SYNCHRONOUS)

measurement = "environment"  # A measurement acts as a container for tags, fields, and timestamps. Use a measurement name that describes your data. from https://docs.influxdata.com/influxdb/v2/reference/key-concepts/data-elements/
location = "living-room"  # Change this as necessary

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
pm1 = float(pmsdata.pm_ug_per_m3(1.0))
pm2_5 = float(pmsdata.pm_ug_per_m3(2.5))
pm10 = float(pmsdata.pm_ug_per_m3(10))

# Log the data
send_to_influxdb(measurement, location, timestamp, corr_temperature, pressure, corr_humidity, light, oxidised, reduced, nh3, pm1, pm2_5, pm10)