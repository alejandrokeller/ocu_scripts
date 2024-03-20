#!/usr/bin/env python
import sys, os

base_path = os.path.abspath(os.path.dirname(sys.argv[0]) + '/../..')
sys.path.append(base_path + '/extras/')
import instrument

config_file = os.path.abspath(base_path + '/config.ini')
device = instrument.instrument(config_file = config_file)

device.log_message("COMMANDS", "Setting rH=95%")
device.set_rH(95, open_port = True)
device.send_commands([device.rH_on_str], open_port = True)

