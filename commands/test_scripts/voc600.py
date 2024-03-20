#!/usr/bin/env python
import sys, os

base_path = os.path.abspath(os.path.dirname(sys.argv[0]) + '/../..')
sys.path.append(base_path + '/extras/')
import instrument

config_file = os.path.abspath(base_path + '/config.ini')
device = instrument.instrument(config_file = config_file)

device.log_message("COMMANDS", "Setting voc=600")
device.set_voc1(600, open_port = True)
device.send_commands([device.pump1_on_str,device.voc1_on_str], open_port = True)
device.send_commands([device.pump2_on_str,device.voc2_on_str], open_port = True)

