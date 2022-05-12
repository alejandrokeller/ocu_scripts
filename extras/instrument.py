import time, datetime
import serial
import serial.tools.list_ports
import os, sys, configparser
from datetime import timedelta

class instrument(object):
    def __init__(self, config_file):

        self.port = "n/a"
        self.query_timeout = 2 # timout in seconds

        # Read the name of the serial port
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file)
            self.serial_port_description  = eval(config['SERIAL_SETTINGS']['SERIAL_PORT_DESCRIPTION'])
            self.serial_port_description2 = eval(config['SERIAL_SETTINGS']['SERIAL_PORT_DESCRIPTION2'])
            self.serial_baudrate          = eval(config['SERIAL_SETTINGS']['SERIAL_BAUDRATE'])
            self.serial_parity            = eval(config['SERIAL_SETTINGS']['SERIAL_PARITY'])
            self.serial_stopbits          = eval(config['SERIAL_SETTINGS']['SERIAL_STOPBITS'])
            self.serial_bytesize          = eval(config['SERIAL_SETTINGS']['SERIAL_BYTESIZE'])
            self.serial_timeout           = eval(config['SERIAL_SETTINGS']['SERIAL_TIMEOUT'])
            self.uv_constant              = eval(config['CALIBRATION']['UV_CONSTANT'])
            self.model                    = eval(config['GENERAL_SETTINGS']['MODEL'])
            if not self.model:
                # try to figure out the instrument's model based on the serial port info
                self.port = self.serial_ports()
        else:
            self.log_message("INSTRUMENT", "Could not find the configuration file: " + config_file)
            exit()

        self.stop_str      = 'X0!'
        self.start_str     = 'X1!'
        self.zeroPID_str   = 'Z1100!'
        self.tube_off_str  = 'q0000!'
        self.tube_on_str   = 'q1000!'
        self.voc1_off_str  = 'C1000!'
        self.voc1_on_str   = 'C1100!'
        self.voc2_off_str  = 'C2000!'
        self.voc2_on_str   = 'C2100!'
        self.pump1_off_str = 'E1000!'
        self.pump1_on_str  = 'E1100!'
        self.pump2_off_str = 'E2000!'
        self.pump2_on_str  = 'E2100!'
        self.rH_off_str    = 'r0000!'
        self.rH_on_str     = 'r1000!'
        self.tec1_off_str  = 'G10!'
        self.tec1_on_str   = 'G11!'
        self.tec2_off_str  = 'G20!'
        self.tec2_on_str   = 'G21!'
        self.tecF1_off_str = 'H10!'
        self.tecF1_on_str  = 'H11!'
        self.tecF2_off_str = 'H20!'
        self.tecF2_on_str  = 'H21!'
        
        self.queries = [
            "a?", # Response: "p values: P1=x; P2=5; BATH:0; Set: px000 to px999" controls pump and humidification
            "b?", # Response: "i values: P1=x; P2=5; BATH:0; Set: ix000 to ix999" controls pump and humidification
            "C?", # Response: "PID1=[value in mv], PID2=[value in mv], to Control PIDx: <ON> = Cx100 or <OFF> = Cx000"
            "E?", # Response: "Status PUMP1=__, PUMP2=__, to Control PUMPx: <ON> = Ex100 or <OFF> = Ex000"
            "F?", # Response: "SetPoint PUMP1=__ PUMP2=__ [%]"
            "l?", # Response: "Control LAMPS 1 to 5: Lx000 (x= uint8 bitwise 0x00054321)"
            "M?", # Response: "SET MassFlowController 2 = __ [ml], Set:M0000 to M0100"
            "N?", # Response: "Serial Number=____"
            "p?", # Response: "p val of VOC1 control loop = __ ; Set with: p0000 to p0999"
            "i?", # Response: "i val of VOC1 control loop = __ ; Set with: i0001 to i0999"
            "P?", # Response: "VOC1 SETPOINT=____ [mV]; Set with: P0000 to P2500"
            "Q?", # Response: "Tubeheater SETPOINT=__[C]; Set temp with: Q0001 to Q080"
            "R?", # Response: "RH SETPOINT=___%; Set percentage with: R0000 to R0100"
#            "T?", # Response: "time and date"; // TODO! Not ready yet because of missing battery;
#            "X?" # Response:"Control DATASTREAM: <ON> = X1000 or <OFF> = X0000 \r\n"
            ]

        self.queries2 = [
            "B?", # Response: SetPoint BOTTLE[1]=0 BOTTLE[2]=0 [C], SET: Bx000! to Bx999!
            "g?", # Response: P:TEC[1]=300,180;TEC[2]=300,180; Set:gxYYY!
            "h?", # Response: i:TEC[1]=10,10;TEC[2]=10,10; Set:hxYYY!
            "u?", # Response: i2:TEC[1]=2,5; TEC[2]=2,5; Set:uYYY!
            "v?", # Response: D:TEC[1]=0,0; TEC[2]=0,0; Set:vxYYY!
            "w?", # Response: LOOP_SPEED: TEC[1]=20; TEC[2]=20; Set:wx001! to wx300!
            "G?", # Response: Status TEC1=0, TEC2=0, <ON>=Gx1!  <OFF>=Gx0!
            "H?", # Response: Status TEC1FAN=0, TEC2FAN=0, <ON>=Hx1!  <OFF>=Hx0!
            "Y?", # Response: TEC1:(1) TEC2:(1)  cool = Yn1! or heat = Yn2!
            "W?"  # Response: REF_RES PT1=3998, PT2=3994, [Ohms]=Wnxxxx!
            ]

        if self.model == 2:
            self.queries.extend(self.queries2)

    def serial_ports(self):
        # produce a list of all serial ports. The list contains a tuple with the port number,
        # description and hardware address
        #
        ports = list(serial.tools.list_ports.comports())

        # return the port if self.serial_port_description is in the description
        for port in ports:
#            print port[2]
            if self.serial_port_description in port[2]:
                self.model = 1
                return port[0]
            if self.serial_port_description2 in port[2]:
                self.model = 2
                return port[0]
        return "n/a"

    def open_port(self):
        # searches for an available port and opens the serial connection
        # Waits 2 seconds before trying again if no port found
        # and doubles time each try with maximum 32 second waiting time
        # until success or KeyboardInterrupt
        wait = 2

        try:
            while self.port == "n/a":
                self.log_message("SERIAL", "no instrument found, waiting " + str(wait) + " seconds to retry...")
                time.sleep(wait)
                if wait < 32:
                    wait = wait*2
                self.port = self.serial_ports()
        except KeyboardInterrupt:
           self.log_message("SERIAL", "aborted by user!... bye...")
           raise

        self.log_message("SERIAL", "Serial port {} found: OCU Model {}".format(self.port, self.model))

        self.ser = serial.Serial(
            port = self.port,
            baudrate = self.serial_baudrate,
            parity = self.serial_parity,
            stopbits = self.serial_stopbits,
            bytesize = self.serial_bytesize,
            timeout = self.serial_timeout
        )

    def close_port(self):
        self.ser.close()

    def send_commands(self, commands, open_port = False):
        if open_port:
            self.open_port()
        for c in commands:
            # check that the command is terminated as a question (?) or an action (!)
            if c[-1] != '?' and c[-1] != '!':
                # terminate it as action with a char '!' if needed
                c += '!'
#            self.log_message("SERIAL", "Sending command: '" + c + "'")
            self.ser.write(c)
        if open_port:
            self.close_port()

    def set_pump(self, pump, flow, open_port = False):
        c = 'L{0}{1:03d}!'.format(pump,flow)
        if flow >= 0 and flow <= 100 and ( pump == 1 or pump == 2):
            self.send_commands([c], open_port = open_port)
        else:
            self.log_message("SERIAL", "Pump setting invalid: '" + c + "'")

    def set_mfc2(self, flow, open_port = False): # flow must be in ml
        c = 'M{0:04d}!'.format(flow)
        if flow >= 0 and flow <= 100:
            self.send_commands([c], open_port = open_port)
        else:
            self.log_message("SERIAL", "MFC setting invalid: '" + c + "'")

    def set_lamps(self, binary_pattern, open_port = False): # i.e. '11111' for all lamps on
        lamps = int(binary_pattern, 2)
        offset = int('01000000',2)
        chr_nr = (lamps ^ offset)
        c = "".join(['L', chr(chr_nr), '000!'])
        print "sending command: " + c + " chr_nr: " + str(chr_nr)
        if len(c) == 6 and 64 <= chr_nr <= 95:
            self.send_commands([c], open_port = open_port)
        else:
            self.log_message("SERIAL", "Lamp pattern invalid: '" + c + "'")

    def set_voc1(self, mv, open_port = False): # set point in milivolts
        c = 'P{0:04d}!'.format(mv)
        if mv >= 0 and mv <= 2500:
            self.send_commands([c], open_port = open_port)
        else:
            self.log_message("SERIAL", "VOC1 setting invalid: '" + c + "'")

    def set_tubeT(self, temperature, open_port = False): # in degC
        c = 'Q{0:04d}!'.format(temperature)
        if temperature > 0 and temperature <= 80:
            self.send_commands([c], open_port = open_port)
        else:
            self.log_message("SERIAL", "Tube temperature setting invalid: '" + c + "'")

    def set_rH(self, rH, open_port = False): # in %rH
        c = 'R{0:04d}!'.format(rH)
        if rH > 0 and rH <= 100:
            self.send_commands([c], open_port = open_port)
        else:
            self.log_message("SERIAL", "Relative humidity setting invalid: '" + c + "'")    

    def set_TEC(self, tec, temp, open_port = False): # in degC
        c = 'B{0}{1:03d}!'.format(tec,temp)
        if temp >= 0 and temp <= 80 and ( tec == 1 or tec == 2):
            self.send_commands([c], open_port = open_port)
        else:
            self.log_message("SERIAL", "TEC setting invalid: '" + c + "'")

    def set_TECMode(self, tec, mode, open_port = False): # in degC
        c = 'Y{0}{1}!'.format(tec,mode + 1)
        if ( mode == 1 or mode == 0) and ( tec == 1 or tec == 2):
            self.send_commands([c], open_port = open_port)
        else:
            self.log_message("SERIAL", "TEC setting invalid: '" + c + "'")

    def stop_datastream(self, open_port = False):
        # This function sends the stop datastream command (X0000) and
        # waits until there is no furter answer
        self.log_message("SERIAL", "Stopping datastream.")
        if open_port:
            self.open_port()
        self.send_commands([self.stop_str], open_port = False)
        #self.ser.write(self.stop_str)
        while len(self.ser.readline()):
            pass
        if open_port:
            self.close_port()

    def start_datastream(self, open_port = False):
        # This function sends the start datastream command (X1000)
        self.log_message("SERIAL", "Starting datastream.")
        self.send_commands([self.start_str], open_port = open_port)
        #self.ser.write(self.start_str)

    def zero_PID(self, open_port = False):
        # This function sends the start datastream command (X1000)
        self.log_message("SERIAL", "Setting VOC Zeropoint (at current reading).")
        #self.ser.write(self.zeroPID_str)
        self.send_commands([self.zeroPID_str], open_port = open_port)

    def query_status(self, query, open_port = False):
        # This function sends a query to port 'ser' and returns the instrument response
        self.log_message("SERIAL", "Sending command '" + query + "'")
        if open_port:
            self.open_port()
        self.send_commands([query], open_port = False)
        #self.ser.write(query)
        answer = ""
        wait_until = datetime.datetime.now() + timedelta(seconds=self.query_timeout)
        while not answer.endswith("\n"):
            answer=self.ser.readline()
            if wait_until < datetime.datetime.now():
                answer+="timeout while waiting for responde to query " + query + "\n"
                break
        if open_port:
            self.close_port()
        return answer

    def readline(self):
        return self.ser.readline()

    def log_message(self, module, msg):
        """
        Logs a message with standard format
        """
        timestamp = time.strftime("%Y.%m.%d-%H:%M:%S ")
        log_message = "- [{0}] :: {1}"
        log_message = timestamp + log_message.format(module,msg)
        print >>sys.stderr,log_message
