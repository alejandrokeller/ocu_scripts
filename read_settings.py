#!/usr/bin/env python

import argparse      # for argument parsing
import os, sys
import datetime
import configparser

import time
import serial
import serial.tools.list_ports

base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
sys.path.append(base_path + '/extras/')
from instrument import instrument

def create_status_file( path = "logs/status/", name = "ocu_status.txt" ): 
    #This function creates a new datafile name
    prefix = time.strftime("%Y%m%d-%H%M%S-")
    newname = path + prefix + name
    return newname

if __name__ == "__main__":

    description_text = """Reads settings of fatcat device.
        Datastreaming is stopped temporary."""

    parser = argparse.ArgumentParser(description=description_text)
    
    # READ ini file
    config_file = base_path + '/config.ini'
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        
        logs_path = eval(config['GENERAL_SETTINGS']['LOGS_PATH']) + '/'
    else:
        print("Could not find the configuration file: {}".format(config_file), file=sys.stderr)
        exit()

    device = instrument(config_file = config_file)
    device.open_port()
    device.start_datastream()
    time.sleep(1)
    device.stop_datastream()
    status_str = ""

    for q in device.queries:
        status_str += device.query_status(q)

    device.start_datastream()
    device.close_port()

    print(status_str, file=sys.stderr)

    newname = create_status_file(path=logs_path)
    print("Writing to Datafile: " + newname, file=sys.stderr)
    fo = open(newname, "a")
    fo.write(status_str)
    fo.close()

    print("bye...", file=sys.stderr)
