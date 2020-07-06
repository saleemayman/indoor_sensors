import time
import numpy as np
from datetime import datetime

import statistics as stats
import thingspeak
import requests as req
from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_air_quality import BrickletAirQuality

HOST = "localhost"
PORT = 4223
UID = "JvC" # Change XYZ to the UID of your Air Quality Bricklet

WRITE_KEY = 'IRU3WSAU1W85X8LJ' # PUT CHANNEL ID HERE
BASE_URL = 'https://api.thingspeak.com/update?api_key={}'.format(WRITE_KEY)

CALL_BACK_PERIOD = 500 # sensor callback function time in milliseconds
SAMPLE_TIME = 20 # number of seconds for collecting measurements for one timestamp
CURRENT_SENSOR_DATA = dict(TSTAMP=[], TEMP=[], RH=[], SP=[], IAQIDX=[], IAQ_ACC=[])
START_TIME = datetime.now()


# Callback function for all values callback
def cb_all_values(iaq_index, iaq_index_accuracy, temperature, humidity, air_pressure):
    timestamp = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

    #CURRENT_SENSOR_DATA = dict(TSTAMP=[], TEMP=[], RH=[], SP=[], IAQIDX=[], IAQ_ACC=[])

    timespent = datetime.now() - START_TIME
    if (timespent.seconds % SAMPLE_TIME) == 0 and len(CURRENT_SENSOR_DATA['TSTAMP']) > 1:
        # upload to cloud
        #getWindowedMean(window_data)
        writeToCloud(getWindowedMean(CURRENT_SENSOR_DATA))
    
        time.sleep(2)

        CURRENT_SENSOR_DATA['TSTAMP'].clear()
        CURRENT_SENSOR_DATA['TEMP'].clear()
        CURRENT_SENSOR_DATA['RH'].clear()
        CURRENT_SENSOR_DATA['SP'].clear()
        CURRENT_SENSOR_DATA['IAQIDX'].clear()
        CURRENT_SENSOR_DATA['IAQ_ACC'].clear()
    else:
        try:
            # collect measurements
            CURRENT_SENSOR_DATA['TSTAMP'].append(timestamp)
            CURRENT_SENSOR_DATA['TEMP'].append(temperature/100.0)   # °C
            CURRENT_SENSOR_DATA['RH'].append(humidity/100.0)    # %RH
            CURRENT_SENSOR_DATA['SP'].append(air_pressure/100.0)    # hPa
            CURRENT_SENSOR_DATA['IAQIDX'].append(iaq_index)
            CURRENT_SENSOR_DATA['IAQ_ACC'].append(iaq_index_accuracy)
        except:
            CURRENT_SENSOR_DATA['TSTAMP'].append(timestamp)
            CURRENT_SENSOR_DATA['TEMP'].append(-999)   # °C
            CURRENT_SENSOR_DATA['RH'].append(-999)    # %RH
            CURRENT_SENSOR_DATA['SP'].append(-999)    # hPa
            CURRENT_SENSOR_DATA['IAQIDX'].append(-999)
            CURRENT_SENSOR_DATA['IAQ_ACC'].append(-999)

            print("[{}] - Could not retrieve data from sensor!".format(timestamp))



def getWindowedMean(window_data):
    mean_data = dict(TSTAMP=max(window_data['TSTAMP']), 
                        TEMP=float(np.format_float_positional( stats.mean(window_data['TEMP']), precision=3, unique=False, fractional=False, trim='k') ),
                        RH=float(np.format_float_positional( stats.mean(window_data['RH']), precision=3, unique=False, fractional=False, trim='k') ),
                        SP=float(np.format_float_positional( stats.mean(window_data['SP']), precision=4, unique=False, fractional=False, trim='k') ),
                        IAQIDX=float(np.format_float_positional( stats.mean(window_data['IAQIDX']), precision=3, unique=False, fractional=False, trim='k') ),
                        IAQ_ACC=float(np.format_float_positional( stats.mean(window_data['IAQ_ACC']), precision=2, unique=False, fractional=False, trim='k') )
                    )
    return mean_data


def writeToCloud(data_to_write):
    sensor_data_str = '&field1={}&field2={}&field3={}&field4={}&field5={}&field6={}'.format(
                        data_to_write['TSTAMP'], data_to_write['TEMP'], data_to_write['RH'], data_to_write['SP'],
                        data_to_write['IAQIDX'], data_to_write['IAQ_ACC'])
    print('Posting: [{} : {} : {} : {} : {} : {}]'.format(  data_to_write['TSTAMP'], 
                                                            data_to_write['TEMP'], 
                                                            data_to_write['RH'], 
                                                            data_to_write['SP'], 
                                                            data_to_write['IAQIDX'], 
                                                            data_to_write['IAQ_ACC'] ))
    r = req.get(BASE_URL + sensor_data_str)
    try:
        r.raise_for_status()
    except req.exceptions.HTTPError as e:
        print('Could not write at baseURL: [{}]'.format(BASE_URL + sensor_data_str))

 

if __name__ == "__main__":
    
    ipcon = IPConnection() # Create IP connection
    aq = BrickletAirQuality(UID, ipcon) # Create device object

    ipcon.connect(HOST, PORT) # Connect to brickd
    # Don't use device before ipcon is connected

    START_TIME = datetime.now()
    while True:
        # Register all values callback to function cb_all_values
        aq.register_callback(aq.CALLBACK_ALL_VALUES, cb_all_values)

        # Set period for all values callback to 1s (1000ms)
        aq.set_all_values_callback_configuration(CALL_BACK_PERIOD, False)

        #print('Averaging measurements for 15 sec . . . .')
        

    input("Press key to exit\n") # Use raw_input() in Python 2
    ipcon.disconnect()
    
