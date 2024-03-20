#!/usr/bin/env python
import sys, os, time

base_path = os.path.abspath(os.path.dirname(sys.argv[0]) + '/../..')
sys.path.append(base_path + '/extras/')
import instrument

config_file = os.path.abspath(base_path + '/config.ini')
device = instrument.instrument(config_file = config_file)

device.log_message("COMMANDS", "Sending commands without sleep delay")
device.send_commands([device.tec1_off_str, device.tec1_on_str], open_port = True)
#device.send_commands([device.tec1_off_str], open_port = True)
#device.send_commands([device.tec2_off_str], open_port = True)
#device.set_TECMode(1, 0, open_port = True)
#device.set_TECMode(2, 0, open_port = True)
#device.send_commands([device.tec1_on_str], open_port = True)
#device.send_commands([device.tec2_on_str], open_port = True)
#device.send_commands([device.tec1_off_str], open_port = True)
#device.send_commands([device.tec2_off_str], open_port = True)
