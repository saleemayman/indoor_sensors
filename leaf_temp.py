import time
import numpy as np
import pandas as pd
from datetime import datetime

import statistics as stats
import thingspeak
import requests as req
from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_air_quality import BrickletAirQuality
from tinkerforge.bricklet_air_quality import BrickletAirQuality
from tinkerforge.bricklet_humidity_v2 import BrickletHumidityV2
from tinkerforge.bricklet_temperature_ir_v2 import BrickletTemperatureIRV2

HOST = "localhost"
PORT = 4223
UID_IT = "Ls8" # UID of IR temperature sensor

CALLBACK_PERIOD = 500 # sensor callback function time in milliseconds
SAMPLE_TIME = 20
LEAF_COUNT = 0

_IRT_DTYPES = np.dtype([('00_TIME', str),
                        ('01_LEAF_COUNT', int),
                        ('02_OBJ_TEMP', float),
                        ('03_AMB_TEMP', float)
                        ])
_CURRENT_IRT = np.empty(0, dtype=_IRT_DTYPES)
_CURRENT_IRT_DATA = pd.DataFrame(_CURRENT_IRT)


START_TIME = datetime.now()

# callback whenever IP connection re-established
def cb_connected(connect_reason):
    if connect_reason == IPConnection.CONNECT_REASON_REQUEST:
        print("Connected by request")
    elif connect_reason == IPConnection.CONNECT_REASON_AUTO_RECONNECT:
        print("Auto-Reconnect")


def cb_object_temperature(temperature):
    try:
        _CURRENT_IRT_DATA ['OBJ_TEMP'].append(temperature/10)
    except:
        print("[IR Temp Sensor] - Could not retrieve object temperature from sensor!")


def cb_ambient_temperature(temperature):
    # print('AMB T: {}'.format(temperature))
    try:
        CURRENT_IRT_DATA['AMB_TEMP'].append(temperature/10)
    except:
