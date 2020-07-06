import time
import numpy as np
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
UID_AQ = "JvC" # UID of Air Quality Bricklet
UID_HM = "Lmp" # UID of Humidity sensor
UID_IT = "Ls8" # UID of IR temperature sensor

WRITE_KEY = 'IRU3WSAU1W85X8LJ' # PUT CHANNEL ID HERE
BASE_URL = 'https://api.thingspeak.com/update?api_key={}'.format(WRITE_KEY)

CALLBACK_PERIOD = 500 # sensor callback function time in milliseconds
SAMPLE_TIME = 20 # number of seconds for collecting measurements for one timestamp

# for each sensor, store data in dictionary with lists
CURRENT_SENSOR_DATA = dict(TSTAMP=[], AVG_TEMP=[], AVG_RH=[], SP=[], OBJ_TEMP=[], AMB_TEMP=[], IAQIDX=[], IAQ_ACC=[])
CURRENT_AQ_DATA = dict(TEMP=[], RH=[], SP=[], IAQIDX=[], IAQ_ACC=[])
CURRENT_HUM_DATA = dict(TEMP=[], RH=[])
CURRENT_IRT_DATA = dict(OBJ_TEMP=[], AMB_TEMP=[])

START_TIME = datetime.now()

# callback whenever IP connection re-established
def cb_connected(connect_reason):
    if connect_reason == IPConnection.CONNECT_REASON_REQUEST:
        print("Connected by request")
    elif connect_reason == IPConnection.CONNECT_REASON_AUTO_RECONNECT:
        print("Auto-Reconnect")

# Callback function for all values callback
def cb_all_values_AQ(iaq_index, iaq_index_accuracy, temperature, humidity, air_pressure):
    try:
        # collect measurements
        CURRENT_AQ_DATA['TEMP'].append(temperature/100.0)   # °C
        CURRENT_AQ_DATA['RH'].append(humidity/100.0)    # %RH
        CURRENT_AQ_DATA['SP'].append(air_pressure/100.0)    # hPa
        CURRENT_AQ_DATA['IAQIDX'].append(iaq_index)
        CURRENT_AQ_DATA['IAQ_ACC'].append(iaq_index_accuracy)
    except:
        print("[Air Quality Sensor] - Could not retrieve data from sensor!")


def cb_object_temperature(temperature):
    # print('OBJ T: {}'.format(temperature))
    try:
        CURRENT_IRT_DATA['OBJ_TEMP'].append(temperature/10)
    except:
        print("[IR Temp Sensor] - Could not retrieve object temperature from sensor!")


def cb_ambient_temperature(temperature):
    # print('AMB T: {}'.format(temperature))
    try:
        CURRENT_IRT_DATA['AMB_TEMP'].append(temperature/10)
    except:
        print("[IR Temp Sensor] - Could not retrieve ambient temperature from sensor!")


def cb_humidity_rhumidity(humidity):
    # print('HUM RH: {}'.format(humidity))
    try:
        CURRENT_HUM_DATA['RH'].append(humidity/100)
    except:
        print("[Humidity Sensor] - Could not retrieve humidity from sensor!")


def cb_humidity_temperature(temperature):
    # print('HUM T: {}'.format(temperature))
    try:
        CURRENT_HUM_DATA['TEMP'].append(temperature/100)
    except:
        print("[Humidity Sensor] - Could not retrieve temperature from sensor!")


def getWindowedMean(window_data):
    mean_data = {}
    for key in window_data:
        if len(window_data[key]) > 1 and isinstance(window_data[key][0], (float, int)):
            mean_data[key] = float(np.format_float_positional( stats.mean(window_data[key]), precision=4, unique=False, fractional=False, trim='k') )
        else:
            mean_data[key] = window_data[key][-1]

    return mean_data


def writeToCloud(data_to_write):
    sensor_data_str = '&field1={}&field2={}&field3={}&field4={}&field5={}&field6={}&field7={}&field8={}'.format(
                        data_to_write['TSTAMP'], data_to_write['AVG_TEMP'], data_to_write['AVG_RH'], data_to_write['SP'],
                        data_to_write['OBJ_TEMP'], data_to_write['AMB_TEMP'], data_to_write['IAQIDX'], data_to_write['IAQ_ACC'])
    print('Posting: [{} : {} : {} : {} : {} : {} : {} : {}]'.format(data_to_write['TSTAMP'], 
                                                                    data_to_write['AVG_TEMP'], 
                                                                    data_to_write['AVG_RH'], 
                                                                    data_to_write['SP'], 
                                                                    data_to_write['OBJ_TEMP'], 
                                                                    data_to_write['AMB_TEMP'], 
                                                                    data_to_write['IAQIDX'], 
                                                                    data_to_write['IAQ_ACC'] ))
    r = req.get(BASE_URL + sensor_data_str)
    try:
        r.raise_for_status()
    except req.exceptions.HTTPError as e:
        print('Could not write at baseURL: [{}]'.format(BASE_URL + sensor_data_str))

 

if __name__ == "__main__":
    try:
        # Create IP connection
        ipcon = IPConnection() 

        # Don't use device before ipcon is connected
        ipcon.connect(HOST, PORT) # Connect to brickd

        # allow auto-reconnect if IP conn disconnects for whatever reason
        ipcon.set_auto_reconnect(True)
        ipcon.register_callback(ipcon.CALLBACK_CONNECTED, cb_connected)

        # create sensor device object
        aq = BrickletAirQuality(UID_AQ, ipcon)
        hm = BrickletHumidityV2(UID_HM, ipcon)
        it = BrickletTemperatureIRV2(UID_IT, ipcon)


        aq.register_callback(aq.CALLBACK_ALL_VALUES, cb_all_values_AQ)
        aq.set_all_values_callback_configuration(CALLBACK_PERIOD, False)

        # callback for humidity sensor
        hm.register_callback(hm.CALLBACK_HUMIDITY, cb_humidity_rhumidity)
        hm.register_callback(hm.CALLBACK_TEMPERATURE, cb_humidity_temperature) 

        # Configuration for humidity sensor callbacks
        hm.set_humidity_callback_configuration(CALLBACK_PERIOD, False, 'x', 0, 0)
        hm.set_temperature_callback_configuration(CALLBACK_PERIOD, False, 'x', 0, 0)

        # Register object temperature callback to function for object and ambient temperatures
        it.register_callback(it.CALLBACK_OBJECT_TEMPERATURE, cb_object_temperature)
        it.register_callback(it.CALLBACK_AMBIENT_TEMPERATURE, cb_ambient_temperature)
        
        it.set_object_temperature_callback_configuration(CALLBACK_PERIOD, False, 'x', 0, 0)
        it.set_ambient_temperature_callback_configuration(CALLBACK_PERIOD, False, 'x', 0, 0)


        START_TIME = datetime.now()


        while True:
            time.sleep(1)
            timespent = datetime.now() - START_TIME
            if (timespent.seconds % SAMPLE_TIME) == 0:
                timestamp = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

                # average measurements for current window 
                aq_mean = getWindowedMean(CURRENT_AQ_DATA)
                hm_mean = getWindowedMean(CURRENT_HUM_DATA)
                it_mean = getWindowedMean(CURRENT_IRT_DATA)
                
                # aggregate for current timestamp
                data_for_upload = dict( TSTAMP=timestamp, 
                                        AVG_TEMP=float(np.format_float_positional( stats.mean( [aq_mean['TEMP'], hm_mean['TEMP']] ), 
                                                        precision=4, unique=False, fractional=False, trim='k') ), 
                                        AVG_RH=float(np.format_float_positional( stats.mean( [aq_mean['RH'], hm_mean['RH']] ), 
                                                        precision=4, unique=False, fractional=False, trim='k') ),
                                        SP=aq_mean['SP'], 
                                        OBJ_TEMP=it_mean['OBJ_TEMP'], 
                                        AMB_TEMP=it_mean['AMB_TEMP'], 
                                        IAQIDX=aq_mean['IAQIDX'], 
                                        IAQ_ACC=aq_mean['IAQ_ACC'])

                # create upload URI and push to thingspeak
                writeToCloud(data_for_upload)

                # reset data containers
                CURRENT_AQ_DATA = dict(TEMP=[], RH=[], SP=[], IAQIDX=[], IAQ_ACC=[])
                CURRENT_HUM_DATA = dict(TEMP=[], RH=[])
                CURRENT_IRT_DATA = dict(OBJ_TEMP=[], AMB_TEMP=[])

        # input("Press key to exit\n") # Use raw_input() in Python 2
        ipcon.disconnect()
    except:
        print("Something went wrong. Sleeping for 15 secs to restart . . . \n")
        time.sleep(15)


