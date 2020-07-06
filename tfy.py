import sys, os
import time
from subprocess import Popen
from datetime import datetime

file_dir = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(file_dir, 'aq2thingspeak_v2.py')

while True:
    timestamp = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    print("\nStarting [ " + timestamp + " ]: " + filename)
    p = Popen("python3.7 " + filename + " > logs/" + timestamp + ".log", shell=True)
    p.wait()
