import time
import os, sys
import csv
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

RECORD_DATA = False
CALLBACK_PERIOD = 500 # sensor callback function time in milliseconds
SAMPLE_TIME = 20
LEAF_COUNT = 0

_CURRENT_IRT_DATA = dict(OBJ_TEMP=[], AMB_TEMP=[])
_LEAF_TEMP_DATA = [] #dict()#LEAF_ID=[], TIME=[], LEAF_TEMP=[], AMB_LEAF_TEMP=[])

START_TIME = datetime.now()

# callback whenever IP connection re-established
def cb_connected(connect_reason):
    if connect_reason == IPConnection.CONNECT_REASON_REQUEST:
        print("Connected by request")
    elif connect_reason == IPConnection.CONNECT_REASON_AUTO_RECONNECT:
        print("Auto-Reconnect")


def cb_object_temperature(temperature):
    if RECORD_DATA:
        _CURRENT_IRT_DATA['OBJ_TEMP'].append(temperature/10)


def cb_ambient_temperature(temperature):
    if RECORD_DATA:
        _CURRENT_IRT_DATA['AMB_TEMP'].append(temperature/10)


def insertToLeafDF(data_to_insert, _LEAF_TEMP_DATA=_LEAF_TEMP_DATA):
    _LEAF_TEMP_DATA.append({
        'TIME': datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'), 
        'LEAF_ID': str(LEAF_COUNT),
        'LEAF_TEMP': data_to_insert['OBJ_TEMP'], 
        'AMB_LEAF_TEMP': data_to_insert['AMB_TEMP']
        })
    
    # reset data containers
    _CURRENT_IRT_DATA = dict(OBJ_TEMP=[], AMB_TEMP=[])


def getLeafWindowedMeanTemp(window_data):
    mean_data = {}
    # calculate mean only for numeric keys. Take last element for others.
    for key in window_data:
        if len(window_data[key]) > 1 and isinstance(window_data[key][0], (float, int)):
            mean_data[key] = float(np.format_float_positional( stats.mean(window_data[key]), precision=4, unique=False, fractional=False, trim='k') )
        else:
            mean_data[key] = window_data[key][-1]

    return mean_data


def saveData(data_to_save):
    # save all collected data for current script run as a csv file with the timestamp
    file_name = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') + '_leaf_temperatures.csv'
    file_name = file_name.replace(' ', '_')
    script_dir = '/'.join(os.path.realpath(__file__).split('/')[:-1])
    file_path = os.path.join(script_dir, 'leaf_data', file_name)

    # create file if not existing to prevent accidental overwrite
    try:
        with open(file_path, 'w') as f:
            w = csv.DictWriter(f, fieldnames=data_to_save[0].keys())
            w.writeheader()
            for leaf_data in data_to_save:
                w.writerow(leaf_data)
        print('Saving data for [{}] leafs in file: {}. Exiting.'.format(len(_LEAF_TEMP_DATA), file_name))
    except IOError:
        print('Unknown IO Error. Could not save file: {}.'.format(file_name))


if __name__ == "__main__":
    # Create IP connection
    ipcon = IPConnection() 

    # Don't use device before ipcon is connected
    ipcon.connect(HOST, PORT)

    # allow auto-reconnect if IP conn disconnects for whatever reason
    ipcon.set_auto_reconnect(True)
    ipcon.register_callback(ipcon.CALLBACK_CONNECTED, cb_connected)

    # create sensor device object
    it = BrickletTemperatureIRV2(UID_IT, ipcon)

    # Register object temperature callback to function for object and ambient temperatures
    it.register_callback(it.CALLBACK_OBJECT_TEMPERATURE, cb_object_temperature)
    it.register_callback(it.CALLBACK_AMBIENT_TEMPERATURE, cb_ambient_temperature)

    user_in_old = 'init'
    while True:
        print('current leaf: {}'.format(LEAF_COUNT))

        user_in_new = input("Enter any of the below choices: \n\t 1. [Y] to record temp for leaf {}. \n\t 3. [L]eaf for next leaf (will save data for leaf: {}). \n\t 3. [N]o to exit code.\n".format(LEAF_COUNT, LEAF_COUNT))
        
        # check input and continue accordingly. Exit only when user specifies.
        if 'Y' == user_in_new.upper() and LEAF_COUNT == 0:
            LEAF_COUNT += 1
            # set flag to start collecting data
            RECORD_DATA = True
            print('\n\tSensor is recording data for leaf: [{}] . . .'.format(LEAF_COUNT))
        elif 'L' in user_in_new.upper():
            # reset flag for next leaf
            RECORD_DATA = False 

            # average all temp measurements and add to leaf DF
            if len(_CURRENT_IRT_DATA) != 0:
                avg_measurements = getLeafWindowedMeanTemp(_CURRENT_IRT_DATA)
                insertToLeafDF(avg_measurements)
            else:
                print('No data collected for leaf: {}. Nothing to save.'.format(LEAF_COUNT))
            
            # start collecting data for next leaf
            RECORD_DATA = True
            LEAF_COUNT += 1
            print('\n\tSensor is recording data for leaf: [{}] . . .'.format(LEAF_COUNT))
        elif 'N' == user_in_new.upper():
            RECORD_DATA = False

            # check if any buffered data needs to be saved.
            if len(_CURRENT_IRT_DATA) != 0:
                # average measurements for current window 
                avg_measurements = getLeafWindowedMeanTemp(_CURRENT_IRT_DATA)
                insertToLeafDF(avg_measurements)
                saveData(_LEAF_TEMP_DATA)
                break   
            else:
                print('No data to save. Exiting.')
                break
        elif 'Y' == user_in_new.upper() and LEAF_COUNT > 0:
            print("Wrong choice. Already started recording data. Enter only: [N,n,L, or l].\n\n")
        else:
            print("Wrong choice. Enter only: [Y,y,N,n,L, or l].\n\n")
        
        user_in_old = user_in_new

    ipcon.disconnect()
    print("Main script.")

