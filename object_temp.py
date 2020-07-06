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
SAMPLE_TIME = 20 # number of seconds for collecting measurements for one timestamp

# for each sensor, store data in dictionary with lists
_CURRENT_IRT_DATA = dict(02_OBJ_TEMP=[], 03_AMB_TEMP=[])

_CURRENT_IRT_DTYPES = np.dtype([('00_TIME', str),
                                ('01_LEAF_COUNT', int),
                                ('02_OBJ_TEMP', float),
                                ('03_AMB_TEMP', float),
                                ])
_CURRENT_IRT= np.empty(0, dtype=_CURRENT_IRT_DTYPES)
_CURRENT_IRT_DATA = pandas.DataFrame(_CURRENT_IRT)
LEAF_COUNT = 0

START_TIME = datetime.now()

# callback whenever IP connection re-established
def cb_connected(connect_reason):
    if connect_reason == IPConnection.CONNECT_REASON_REQUEST:
        print("Connected by request")
    elif connect_reason == IPConnection.CONNECT_REASON_AUTO_RECONNECT:
        print("Auto-Reconnect")

def cb_object_temperature(temperature):
    # print('OBJ T: {}'.format(temperature))
    timestamp = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    try:
        if RECORD_DATA:
            # add meta-data
            mean_data['00_TIME'] = timestamp;
            mean_data['01_LEAF_COUNT'] = LEAF_COUNT

            CURRENT_IRT_DATA['02_OBJ_TEMP'].append(temperature/10)
        else:
            pass
    except:
        print("[IR Temp Sensor] - Could not retrieve object temperature from sensor!")


def cb_ambient_temperature(temperature):
    # print('AMB T: {}'.format(temperature))
    try:
        if RECORD_DATA:
            CURRENT_IRT_DATA['03_AMB_TEMP'].append(temperature/10)
        else:
            pass
    except:
        print("[IR Temp Sensor] - Could not retrieve ambient temperature from sensor!")


def getLeafWindowedMeanTemp(window_data):
    mean_data = {}
    for key in window_data:
        if len(window_data[key]) > 1 and isinstance(window_data[key][0], (float, int)):
            mean_data[key] = float(np.format_float_positional( stats.mean(window_data[key]), precision=4, unique=False, fractional=False, trim='k') )
        else:
            mean_data[key] = window_data[key][-1]

    return mean_data


def saveData(data_to_save):
    it_mean = getLeafWindowedMeanTemp(data_to_save)

    file_name = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') + 'leaf_temperatures.csv'
    file_path = os.path.join(os.path.realpath(__file__), 'leaf_data', file_name)

    # create file if not existing to prevent accidental overwrite
    with open(file_path, 'wb') as f:
        w = csv.DictWriter(f, it_mean.keys())
        w.writeheader()
        w.writerow(it_mean)

    # reset data containers
    _CURRENT_IRT= np.empty(0, dtype=_CURRENT_IRT_DTYPES)
    _CURRENT_IRT_DATA = pandas.DataFrame(_CURRENT_IRT)


if __name__ == "__main__":
    # Create IP connection
    ipcon = IPConnection() 

    # Don't use device before ipcon is connected
    ipcon.connect(HOST, PORT) # Connect to brickd

    # allow auto-reconnect if IP conn disconnects for whatever reason
    ipcon.set_auto_reconnect(True)
    ipcon.register_callback(ipcon.CALLBACK_CONNECTED, cb_connected)

    # create sensor device object
    it = BrickletTemperatureIRV2(UID_IT, ipcon)

    # Register object temperature callback to function for object and ambient temperatures
    it.register_callback(it.CALLBACK_OBJECT_TEMPERATURE, cb_object_temperature)
    it.register_callback(it.CALLBACK_AMBIENT_TEMPERATURE, cb_ambient_temperature)
    
    it.set_object_temperature_callback_configuration(CALLBACK_PERIOD, False, 'x', 0, 0)
    it.set_ambient_temperature_callback_configuration(CALLBACK_PERIOD, False, 'x', 0, 0)
    
    codeRun = True
    while codeRun:
        LEAF_COUNT += 1

        print('current leaf: {}'.format(LEAF_COUNT))
        user_in = input("Enter any of the below choices: \n\t 1. [Y] to record temp for leaf {}. \n\t 3. [L]eaf for next leaf (will save data for leaf: {}). \n\t 3. [N]o to exit code.  \n".format(LEAF_COUNT, LEAF_COUNT))
        
        # check input and continue accordingly. Exit only when user specifies.
        if 'Y' == user_in.upper():
            RECORD_DATA = True
        elif 'L' in user_in.upper():
            RECORD_DATA = False 
            LEAF_COUNT += 1
        elif 'N' == user_in.upper():
            # average measurements for current window 
            it_mean = getWindowedMean(CURRENT_IRT_DATA)
        else:
            print('Enter [Y]es to records for leaf {} or [N]o to save already recorded data and exit.'


    input("Press key to exit\n") 
    ipcon.disconnect()
    
