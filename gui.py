#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# listens to a TCP broadcast and displays data using Ppyqt widgets
# provides also a buttons interface for interacting with the 
# measurement instrument

#from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from PyQt5 import  QtGui, QtCore, QtWidgets
import pyqtgraph as pg
import socket
import sys, os
import ast # for datastring parsing
import numpy as np
import configparser
from functools import partial # function mapping
from collections import namedtuple

import pandas as pd

import time
import serial
import serial.tools.list_ports

base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
sys.path.append(base_path + '/extras/')
from instrument import instrument

def hex2bin(s):
    hex_table = ['0000', '0001', '0010', '0011',
                 '0100', '0101', '0110', '0111',
                 '1000', '1001', '1010', '1011',
                 '1100', '1101', '1110', '1111']
    bits = ''
    for i in range(len(s)):
        bits += hex_table[int(s[i], base=16)]
    return bits

### map function for propper parameter convertion
def apply(f,a):
    return f(a)

def send_string(line, server_address, sock = 0):
    # Sends a string to through a TCP socket

    # Send data
    try:
        if not sock:
            # Create a TCP/IP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

##            print >>sys.stderr, 'Sending data to %s port %s' % server_address
            sock.connect(server_address)
            
        sock.sendall(line)
    except socket.error:
##        print >>sys.stderr, "nobody listening"
        sock.close()
##        print >>sys.stderr, 'closing socket'
        sock = 0

    return sock

class Visualizer(object):
    def __init__(self, host_name='localhost', host_port=10000, config_file='config.ini'):

        # init socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a TCP/IP socket
        self.server_address = (host_name, host_port)
        print('starting up on {}'.format(self.server_address), file=sys.stderr)
        self.sock.bind(self.server_address) # Bind the socket to the port
        self.sock.listen(1) # Listen for incoming connections
        print('waiting for a connection', file=sys.stderr)
        self.connection, self.client_address = self.sock.accept() # Wait for a connection
        print('connection from {}'.format(self.client_address), file=sys.stderr)

        self.device = instrument(config_file = config_file)

        # init pyqt
        self.app = QtWidgets.QApplication([])
        pg.setConfigOptions(antialias=False)
        pg.setConfigOption('foreground', 'w')

        #init data structure
        self.__dataStructure()

        # setup plots
        self.pen = pg.mkPen('y', width=1)
        self.t = np.linspace(-self.graphLength, 0, self.numSamples)
        self.pen1  = pen=pg.mkPen('y', width=1)
        self.pen1s = pen=pg.mkPen(color='y', width=1, style=QtCore.Qt.DashLine)
        self.pen1b = pen=pg.mkPen('y', width=1, style=QtCore.Qt.DotLine)
        self.pen2  = pen=pg.mkPen('r', width=1)
        self.pen2s = pen=pg.mkPen('r', width=1, style=QtCore.Qt.DashLine)
        self.pen2b = pen=pg.mkPen('r', width=1, style=QtCore.Qt.DotLine)
        
        self.__PIDplots()
        self.__Fplots()
        self.__RHplots()
        self.__Tplots()
        self.__OFRplots()
        self.__PUMPplots()
        if self.device.model == 2:
            self.__TECplots()

#####################################################################

        ## Define a top level widget to hold the controls
        self.widgets = QtWidgets.QWidget()
        self.widgets.setWindowTitle("OCU: Organics Coating Unit")
        self.widgets.showFullScreen()

        ## Create infotext widgets to be placed inside
        self.lblLamp      = QtWidgets.QLabel("Lamps")
        self.lblVOCTctr   = QtWidgets.QLabel("VOC heater")
        self.lblBath      = QtWidgets.QLabel("rH:")
        self.lblBathrH    = QtWidgets.QLabel("")
        self.lblTubeT     = QtWidgets.QLabel("VOC: XX degC")
        self.lblVOC1      = QtWidgets.QLabel("VOC1 ()")
        self.lblVOC2      = QtWidgets.QLabel("VOC2 ()")
        self.lblPump1     = QtWidgets.QLabel("Pump1")
        self.lblPump2     = QtWidgets.QLabel("Pump2")
        self.lblLampsData = QtWidgets.QLabel("ORF: XX degC, XXXX uA")
        self.lblInletData = QtWidgets.QLabel("Inlet: XX degC, XX% rH")
        
        self.lblCD        = QtWidgets.QLabel("0")

        ## Create button widgets for actions
        self.button_size  = 27
        self.btnLamp      = QtWidgets.QPushButton("")            # Turn lamps on or off
        self.btnLamp.setFixedWidth(self.button_size)
        self.btnLamp.setFixedHeight(self.button_size)
        self.btnVOCTctr   = QtWidgets.QPushButton("")            # Turn VOC heater on or off
        self.btnVOCTctr.setFixedHeight(self.button_size)
        self.btnVOCTctr.setFixedWidth(self.button_size)
        self.btnBath      = QtWidgets.QPushButton("")            # Turn rH control on/off
        self.btnBath.setFixedWidth(self.button_size)
        self.btnBath.setFixedHeight(self.button_size)
        self.btnTube      = QtWidgets.QPushButton("")             # Turn Tube Heating on/off
        self.btnTube.setFixedWidth(self.button_size)
        self.btnTube.setFixedHeight(self.button_size)
        self.btnVOC1      = QtWidgets.QPushButton("")             # TURN VOC1 control on/off
        self.btnVOC1.setFixedWidth(self.button_size)
        self.btnVOC1.setFixedHeight(self.button_size)
        self.btnVOC2      = QtWidgets.QPushButton("")            # TURN VOC2 control on/off
        self.btnVOC2.setFixedWidth(self.button_size)
        self.btnVOC2.setFixedHeight(self.button_size)
        self.btnPump1     = QtWidgets.QPushButton("")            # Turn pump 1 on/off
        self.btnPump1.setFixedWidth(self.button_size)
        self.btnPump1.setFixedHeight(self.button_size)
        self.btnPump2     = QtWidgets.QPushButton("")            # Turn pump 2 on/off
        self.btnPump2.setFixedWidth(self.button_size)
        self.btnPump2.setFixedHeight(self.button_size)

        self.btnLamp.clicked.connect(self.toggleAllLamps)
        self.btnVOCTctr.clicked.connect(self.toggleVOCHeater)
        self.btnVOC1.clicked.connect(self.toggleVOC1)
        self.btnVOC2.clicked.connect(self.toggleVOC2)
        self.btnPump1.clicked.connect(self.togglePump1)
        self.btnPump2.clicked.connect(self.togglePump2)
        self.btnBath.clicked.connect(self.togglerH)

        ## Create widgets for controlling MFC2
        self.btnMFC2      = QtWidgets.QPushButton(">>")  # Sends new MFC2 flow
        self.btnMFC2.setFixedWidth(self.button_size)
        self.btnMFC2.setFixedHeight(self.button_size)
        self.btnMFC2.clicked.connect(self.setMFC2)
        self.lblMFC2      = QtWidgets.QLabel("MFC2 (mlpm):")
        self.spMFC2       = QtWidgets.QSpinBox()
        self.spMFC2.setRange(0,100)

        ## Create widgets for controlling VOC1
        self.btnSVOC1      = QtWidgets.QPushButton(">>")  # Sends new MFC2 flow
        self.btnSVOC1.setFixedWidth(self.button_size)
        self.btnSVOC1.setFixedHeight(self.button_size)
        self.btnSVOC1.clicked.connect(self.setSVOC1)
        self.lblSVOC1      = QtWidgets.QLabel("VOC1 (mV):")
        self.spSVOC1       = QtWidgets.QSpinBox()
        self.spSVOC1.setRange(0,2500)

        ## Create widgets for controlling VOC Heater
        self.btnVOCT       = QtWidgets.QPushButton(">>")  # Sends new MFC2 flow
        self.btnVOCT.setFixedWidth(self.button_size)
        self.btnVOCT.setFixedHeight(self.button_size)
        self.btnVOCT.clicked.connect(self.setVOCT)
        self.lblVOCT       = QtWidgets.QLabel("VOC (degC):")
        self.spVOCT        = QtWidgets.QSpinBox()
        self.spVOCT.setRange(0,80)
        
        ## Create widgets for controlling rH
        self.btnRH         = QtWidgets.QPushButton(">>")  # Sends new MFC2 flow
        self.btnRH.setFixedWidth(self.button_size)
        self.btnRH.setFixedHeight(self.button_size)
        self.btnRH.clicked.connect(self.setRH)
        self.lblRH       = QtWidgets.QLabel("rH (%):")
        self.spRH        = QtWidgets.QSpinBox()
        self.spRH.setRange(0,95)
        self.lblBathT    = QtWidgets.QLabel("Bath (degC):") # tbath container

        ## Create widgets for serial commands
        self.btnSERIAL     = QtWidgets.QPushButton(">>")  # Sends new MFC2 flow
        self.btnSERIAL.setFixedWidth(self.button_size)
        self.btnSERIAL.setFixedHeight(self.button_size)
        self.btnSERIAL.clicked.connect(self.sendSerialCMD)
        self.lblSERIAL     = QtWidgets.QLabel("Command:")
        self.lineSERIAL    = QtWidgets.QLineEdit()
        validator = QtGui.QRegExpValidator(QtCore.QRegExp("[abFpirRXzZ][0-9]{4}"))
        if self.device.model == 2:
            validator = QtGui.QRegExpValidator(QtCore.QRegExp("[abFgHhuDpirRXzZ][0-9]{4}"))
        self.lineSERIAL.setValidator(validator)

        ## Create widgets for TEC commands
        if self.device.model == 2:
            self.__TECwidgets()

            ## Info of current TEC Modes and temperatures
            self.lblTEC1mode   = QtWidgets.QLabel("TEC1 (mode)")
            self.lblTEC2mode   = QtWidgets.QLabel("TEC2 (mode)")

            ## Temporary label with TEC Status
            self.lblTECStatus   = QtWidgets.QLabel("TEC Status: - STATUS TEXT -")
            self.lblTECStatus.setWordWrap(True)
            

        ## Create a grid layout to manage the controls size and position
        self.controlsLayout = QtWidgets.QGridLayout()
        self.encloserLayout = QtWidgets.QVBoxLayout()
        self.lampsButtonsLayout = QtWidgets.QHBoxLayout()
        self.mfcLayout = QtWidgets.QGridLayout()
        self.encloserLayout.addLayout(self.controlsLayout)
        self.encloserLayout.addLayout(self.lampsButtonsLayout)
        self.encloserLayout.addLayout(self.mfcLayout)
        if self.device.model == 2:
            if self.lblTECStatus:
                self.encloserLayout.addWidget(self.lblTECStatus)
        self.encloserLayout.addStretch(1)

        ## Create individual lamp buttons
        self.lamps = []
        for i in range(5):
            self.lamps.append(i)
            self.lamps[i] = QtWidgets.QPushButton("L{}".format(i))
            self.lamps[i].setFixedWidth(int(1.2*self.button_size))
            self.lamps[i].setFixedHeight(self.button_size)
            self.lamps[i].clicked.connect(partial(self.toggleLamp,i))
            self.lampsButtonsLayout.addWidget(self.lamps[i])

        ## Add widgets to the layout in their proper positions
        self.controlsLayout.addWidget(self.lblLamp,      0, 1)
        if self.device.model == 1:
            self.controlsLayout.addWidget(self.lblVOCTctr,   1, 1)
        self.controlsLayout.addWidget(self.lblVOC1,      2, 1)
        self.controlsLayout.addWidget(self.lblVOC2,      3, 1)
        self.controlsLayout.addWidget(self.lblPump1,     4, 1)
        self.controlsLayout.addWidget(self.lblPump2,     5, 1)
        self.controlsLayout.addWidget(self.lblBathrH,    6, 1)
        self.controlsLayout.addWidget(self.lblBathT,     7, 1)

##        self.controlsLayout.addWidget(self.lblCD,    9, 0, 1, 2) # example of two spaces horizontal (one vertical)

        self.controlsLayout.addWidget(self.btnLamp,     0, 0)
        if self.device.model == 1:
            self.controlsLayout.addWidget(self.btnVOCTctr,  1, 0)
        self.controlsLayout.addWidget(self.btnVOC1,     2, 0)
        self.controlsLayout.addWidget(self.btnVOC2,     3, 0)
        self.controlsLayout.addWidget(self.btnPump1,    4, 0)
        self.controlsLayout.addWidget(self.btnPump2,    5, 0)
        self.controlsLayout.addWidget(self.btnBath,     6, 0)

        ## Add Widgets to the MFCLayout
        self.mfcLayout.addWidget(self.lblSVOC1,    0, 0)
        self.mfcLayout.addWidget(self.spSVOC1,     0, 1)
        self.mfcLayout.addWidget(self.btnSVOC1,    0, 2)
        if self.device.model == 1:
            self.mfcLayout.addWidget(self.lblVOCT,     1, 0)
            self.mfcLayout.addWidget(self.spVOCT,      1, 1)
            self.mfcLayout.addWidget(self.btnVOCT,     1, 2)
        self.mfcLayout.addWidget(self.lblMFC2,     2, 0)
        self.mfcLayout.addWidget(self.spMFC2,      2, 1)
        self.mfcLayout.addWidget(self.btnMFC2,     2, 2)
        self.mfcLayout.addWidget(self.lblRH,       3, 0)
        self.mfcLayout.addWidget(self.spRH,        3, 1)
        self.mfcLayout.addWidget(self.btnRH,       3, 2)
        self.mfcLayout.addWidget(self.lblSERIAL,   4, 0)
        self.mfcLayout.addWidget(self.lineSERIAL,  4, 1)
        self.mfcLayout.addWidget(self.btnSERIAL,   4, 2)
        
        ## Create a QVBox layout to manage the Info and plots
        self.infoLayout = QtWidgets.QVBoxLayout()

        ## Create a QHBox for the text info
        self.textLayout = QtWidgets.QHBoxLayout()
        self.textLayout.addWidget(self.lblLampsData)
        self.textLayout.addItem(QtWidgets.QSpacerItem(30, 0))
        self.textLayout.addWidget(self.lblInletData)
        self.textLayout.addItem(QtWidgets.QSpacerItem(30, 0))
        if self.device.model == 1:
            self.textLayout.addWidget(self.lblTubeT)
        elif self.device.model == 2:
            self.textLayout.addWidget(self.lblTEC1mode)
            self.textLayout.addWidget(self.lblTEC2mode)

        ## First line of the pidLayout has the status text (temps at.s.o.)
        self.infoLayout.addLayout(self.textLayout)
        
        ## Now the plots
        self.pidLayout = QtWidgets.QVBoxLayout()
        self.pidLayout.addWidget(self.PIDplot)
        self.pidLayout.addWidget(self.Fplot)

        self.rhLayout = QtWidgets.QVBoxLayout()
        self.rhLayout.addWidget(self.RHplot)
        self.rhLayout.addWidget(self.Tplot)

        self.ofrLayout = QtWidgets.QVBoxLayout()
        self.ofrLayout.addWidget(self.OFRUVplot)
        self.ofrLayout.addWidget(self.OFRTplot)

        self.pumpLayout = QtWidgets.QVBoxLayout()
        self.__PUMPwidgets()
        self.pumpLayout.addLayout(self.pumpControlLayout)
        self.pumpLayout.addWidget(self.PUMPplot)

        ## Prepare tabs and add plots
        self.dataTab = QtWidgets.QTabWidget()
        ## TabPID for PID and Flow plots
        self.dataTab.tabPID = QtWidgets.QWidget()
        self.dataTab.addTab(self.dataTab.tabPID,"VOC / Flow")
        self.dataTab.tabPID.setLayout(self.pidLayout)

        if self.device.model == 2:
            self.tecLayout = QtWidgets.QVBoxLayout()
            self.tecLayout.addLayout(self.tecControlLayout)
            self.tecLayout.addWidget(self.TECplot)
            
            ## Prepare tabs
            self.dataTab.tabTEC = QtWidgets.QWidget()
            self.dataTab.addTab(self.dataTab.tabTEC,"TEC")
            self.dataTab.tabTEC.setLayout(self.tecLayout)
        self.infoLayout.addWidget(self.dataTab)

        ## TabRH for rH and Temp plots
        self.dataTab.tabRH = QtWidgets.QWidget()
        self.dataTab.addTab(self.dataTab.tabRH,"rH / Temp")
        self.dataTab.tabRH.setLayout(self.rhLayout)
        ## TabOFR for OFR plots
        self.dataTab.tabOFR = QtWidgets.QWidget()
        self.dataTab.addTab(self.dataTab.tabOFR,"OFR")
        self.dataTab.tabOFR.setLayout(self.ofrLayout)
        ## TabPUMP for PID flow
        self.dataTab.tabPUMP = QtWidgets.QWidget()
        self.dataTab.addTab(self.dataTab.tabPUMP,"PID pump")
        self.dataTab.tabPUMP.setLayout(self.pumpLayout)

        ## Create a QHBox layout to manage the plots
        self.centralLayout = QtWidgets.QHBoxLayout()

        self.centralLayout.addLayout(self.encloserLayout)
        self.centralLayout.addLayout(self.infoLayout)

        ## Display the widget as a new window
        self.widgets.setLayout(self.centralLayout)
        self.widgets.show()

    def __dataStructure(self):
        #init data structure
        self.datastring = ""
        self.graphLength = 600 # seconds
        self.deltaT = 0.5 # s, sampling time
        self.numSamples = int(self.graphLength/self.deltaT)
        self.photodiode_constant = 0.04545 # nA/mV
        # set status to new application
        self.firstLoop = True

        self.keys = [
            "runtime",
            "svoc1",
            "voc1",
            "base1", # 20.9.2019 baseline VOC1
            "svoc2",
            "voc2",
            "base2", # 20.9.2019 baseline VOC1
            "mfc1",
            "mfc2",
            "flow1",
            "flow2",
            "tuv",
            "iuv",
            "inrH", # 20.9.2019 baseline VOC1
            "inT", # 20.9.2019 baseline VOC1
            "stvoc",
            "tvoc",
            "sinrH",
            "tbath",
            "status",
            "lamps"
            ]
        self.keys2 = [ # additional columns of version 2
            "sb1",
            "sb2",
            "b1",
            "b2",
            "tec1",
            "tec2",
            "tecbyte"
            ]
        self.functions = [
            float,  # runtime
            float,    # svoc1
            float,  # voc1
            float,  # base1
            float,    # svoc2
            float,  # voc2
            float,  # base2
            float,  # mfc1
            float,  # mfc2
            float,  # flow1
            float,  # flow2
            float,  # tuv
            float,  # iuv
            float,  # inrH
            float,  # inT
            float,     # stvoc
            float,   # tvoc
            float,     # sinrH
            float,   # tbath
            hex2bin, # status
            hex2bin  # lamps
            ]
        self.functions2 = [ # additional columns of version 2
            float,        # sb1
            float,        # sb2
            float,      # b1
            float,      # b2
            float,      # tec1
            float,      # tec2
            hex2bin     # tecbyte
            ]
        
        self.units = [
            's',    # runtime
            'mV',   # svoc1
            'mV',   # voc1
            'mV',   # base1
            'mV',   # svoc2
            'mV',   # voc2
            'mV',   # base2
            'ml',   # mfc1
            'ml',   # mfc2
            'slpm', # flow1
            'slpm', # flow2
            'degC', # tuv
            'mv',   # iuv
            '%',    # inrH
            'degC', # inT
            'degC', # stvoc
            'degC', # tvoc
            'degC', # sinrH
            'degC', # tbath
            '-',    # status
            '-'     # lamps
            ]
        self.units2 = [ # additional columns of version 2
            'degC', # sb1
            'degC', # sb2
            'degC', # b1
            'degC', # b2
            'degC', # tec1
            'degC', # tec2
            '-'     # tecbyte
            ]

        if self.device.model == 2:
            self.keys.extend(self.keys2)
            self.functions.extend(self.functions2)
            self.units.extend(self.units2)

        self.unitsDict = dict(zip(self.keys, self.units))
        self.df = pd.DataFrame(columns=self.keys)
        zeroDict = dict(zip(self.keys,
                       map(partial(apply, a="0"), self.functions)
                       ))
        self.df = pd.concat([self.df, pd.DataFrame([zeroDict]*self.numSamples)],ignore_index=True)
            
        self.statusKeys = [
            "tec2",
            "tec1",
            "rH",
            "tube_heat",
            "voc2",
            "voc1",
            "pump2",
            "pump1"]

        self.lampKeys = [
            "run_flag",
            "reslamp1",
            "reslamp2",
            "lamp4",
            "lamp3",
            "lamp2",
            "lamp1",
            "lamp0"
            ]

        self.tecKeys = [
            "K2 Short GND",
            "K2 Short VCC",
            "K2 Open",
            "Pt1000B General Error",
            "Pt1000B Open",
            "Pt1000B Short",
            "TEC over temperature",
            "TEC over current",
            "K1 GND",
            "K1 VCC",
            "K1 Open",
            "Pt1000A General Error",
            "tec2mode",
            "tec1mode",
            "tec2",
            "tec1"
            ]

        self.lampString = '00000'
        
        self.statusDict = {}
        for k in self.statusKeys:
            self.statusDict[k] = 0

        self.lampDict = {}
        for k in self.lampKeys:
            self.lampDict[k] = 0

        self.tecDict = {}
        for k in self.tecKeys:
            self.tecDict[k] = 0

    def __PIDplots(self):
        self.PIDcurves = dict()
        self.PIDplot = pg.PlotWidget()
        self.PIDplot.addLegend()
        self.PIDplot.setLabel('left', "PID voltage", units='mV')
        self.PIDplot.setLabel('bottom', "t", units='s')
        self.PIDplot.showGrid(False, True)
        self.PIDcurves[0] = self.PIDplot.plot(self.t, self.df['svoc1'], pen=self.pen1s)
        self.PIDcurves[1] = self.PIDplot.plot(self.t, self.df['voc1'], pen=self.pen1, name='PID1')
        self.PIDcurves[2] = self.PIDplot.plot(self.t, self.df['svoc2'], pen=self.pen2s)
        self.PIDcurves[3] = self.PIDplot.plot(self.t, self.df['voc2'], pen=self.pen2, name='PID2')
        
    def __Fplots(self):
        self.Fcurves = dict()
        self.Fplot = pg.PlotWidget()
        self.Fplot.addLegend()
        self.Fplot.setRange(yRange=[-0.005, 0.105])
        self.Fplot.setLabel('left', "VOC Flow", units='lpm')
        self.Fplot.setLabel('bottom', "t", units='s')
        self.Fplot.showGrid(False, True)
        self.Fcurves[0] = self.Fplot.plot(self.t, self.df['mfc1'], pen=self.pen1, name='MFC1')
        self.Fcurves[1] = self.Fplot.plot(self.t, self.df['mfc2'], pen=self.pen2, name='MFC2')
        # currently the set variable does not exists
        #self.Fcurves[3] = self.Fplot.plot(self.t, self.df['smfc2'], pen=self.pen2s)

    def __RHplots(self):
        self.RHcurves = dict()
        self.RHplot = pg.PlotWidget()
        self.RHplot.addLegend()
        self.RHplot.setLabel('left', "Inlet rH", units='%')
        self.RHplot.setLabel('bottom', "t", units='s')
        self.RHplot.showGrid(False, True)
        self.RHcurves[0] = self.RHplot.plot(self.t, self.df['sinrH'], pen=self.pen1s)
        self.RHcurves[1] = self.RHplot.plot(self.t, self.df['inrH'], pen=self.pen1)

    def __Tplots(self):
        self.Tcurves = dict()
        self.Tplot = pg.PlotWidget()
        self.Tplot.addLegend()
        self.Tplot.setLabel('left', "T", units='degC')
        self.Tplot.setLabel('bottom', "t", units='s')
        self.Tplot.showGrid(False, True)
        self.Tcurves[0] = self.Tplot.plot(self.t, self.df['inT'], pen=self.pen1, name='Inlet')
        self.Tcurves[1] = self.Tplot.plot(self.t, self.df['tbath'], pen=self.pen2, name='rH bath')

    def __OFRplots(self):
        self.OFRTcurves = dict()
        self.OFRTplot = pg.PlotWidget()
        self.OFRTplot.addLegend()
        self.OFRTplot.setLabel('left', "T", units='degC')
        self.OFRTplot.setLabel('bottom', "t", units='s')
        self.OFRTplot.showGrid(False, True)
        self.OFRTcurves[0] = self.OFRTplot.plot(self.t, self.df['tuv'], pen=self.pen1)

        self.OFRUVcurves = dict()
        self.OFRUVplot = pg.PlotWidget()
        self.OFRUVplot.addLegend()
        self.OFRUVplot.setLabel('left', "UV sensor", units='A')
        self.OFRUVplot.setLabel('bottom', "t", units='s')
        self.OFRUVplot.showGrid(False, True)
        self.OFRUVcurves[0] = self.OFRUVplot.plot(self.t, self.df['iuv'], pen=self.pen1)
        
    def __TECplots(self):
        self.TECcurves = dict()

        self.TECplot = pg.PlotWidget()
        self.TECplot.addLegend()
        self.TECplot.setLabel('left', "TEC Temp", units='degC')
        self.TECplot.setLabel('bottom', "t", units='s')
        self.TECplot.showGrid(False, True)
        self.TECcurves[0] = self.TECplot.plot(self.t, self.df['sb1'],  name='SP TEC 1', pen=self.pen1b)
        self.TECcurves[1] = self.TECplot.plot(self.t, self.df['sb2'],  name='SP TEC 2', pen=self.pen2b)
        self.TECcurves[2] = self.TECplot.plot(self.t, self.df['tec1'], name='TEC 1',    pen=self.pen1s)
        self.TECcurves[3] = self.TECplot.plot(self.t, self.df['tec2'], name='TEC 2',    pen=self.pen2s)
        self.TECcurves[4] = self.TECplot.plot(self.t, self.df['b1'],   name='Bottle 1', pen=self.pen1)
        self.TECcurves[5] = self.TECplot.plot(self.t, self.df['b2'],   name='Bottle 2', pen=self.pen2)



    def __TECwidgets(self):
        ## Create widgets for TEC commands
        button_size = self.button_size*3 
        self.btnTEC1heat   = QtWidgets.QPushButton("heat")        # Turn TEC1 heat on or off
        self.btnTEC1heat.setFixedWidth(button_size)
        self.btnTEC1heat.clicked.connect(self.toggleTEC1heat)
        self.btnTEC1cool   = QtWidgets.QPushButton("cool")        # Turn TEC1 cool on or off
        self.btnTEC1cool.setFixedWidth(button_size)
        self.btnTEC1cool.clicked.connect(self.toggleTEC1cool)
        self.btnTEC1set    = QtWidgets.QPushButton(">>")          # Sends new TEC1 setpoint
        self.btnTEC1set.setFixedWidth(self.button_size)
        self.btnTEC1set.setFixedHeight(self.button_size)
        self.btnTEC1set.clicked.connect(self.setTEC1)
        self.lblTEC1       = QtWidgets.QLabel("TEC1 (degC):")
        self.spTEC1        = QtWidgets.QSpinBox()
        self.spTEC1.setRange(0,95)
        self.spTEC1.lineEdit().returnPressed.connect(self.setTEC1)

        self.btnTEC2heat   = QtWidgets.QPushButton("heat")        # Turn TEC1 heat on or off
        self.btnTEC2heat.setFixedWidth(button_size)
        self.btnTEC2heat.clicked.connect(self.toggleTEC2heat)
        self.btnTEC2cool   = QtWidgets.QPushButton("cool")        # Turn TEC1 cool on or off
        self.btnTEC2cool.setFixedWidth(button_size)
        self.btnTEC2cool.clicked.connect(self.toggleTEC2cool)
        self.btnTEC2set    = QtWidgets.QPushButton(">>")         # Sends new TEC2 setpoint
        self.btnTEC2set.setFixedWidth(self.button_size)
        self.btnTEC2set.setFixedHeight(self.button_size)
        self.btnTEC2set.clicked.connect(self.setTEC2)
        self.lblTEC2       = QtWidgets.QLabel("TEC2 (degC):")
        self.spTEC2        = QtWidgets.QSpinBox()
        self.spTEC2.setRange(0,95)

        ## Create a grid layout to manage the TEC controls size and position
        self.tecControlLayout = QtWidgets.QGridLayout()

        self.tecControlLayout.addWidget(self.btnTEC1heat,  0, 0)
        self.tecControlLayout.addWidget(self.btnTEC1cool,  0, 1)
        self.tecControlLayout.addWidget(self.lblTEC1,      0, 2)
        self.tecControlLayout.addWidget(self.spTEC1,       0, 3)
        self.tecControlLayout.addWidget(self.btnTEC1set,   0, 4)

        self.tecControlLayout.addWidget(self.btnTEC2heat,  1, 0)
        self.tecControlLayout.addWidget(self.btnTEC2cool,  1, 1)
        self.tecControlLayout.addWidget(self.lblTEC2,      1, 2)
        self.tecControlLayout.addWidget(self.spTEC2,       1, 3)
        self.tecControlLayout.addWidget(self.btnTEC2set,   1, 4)

    def __PUMPplots(self):
        self.PUMPcurves = dict()

        self.PUMPplot = pg.PlotWidget()
        self.PUMPplot.addLegend()
        self.PUMPplot.setLabel('left', "PID Flow", units='lpm')
        self.PUMPplot.setLabel('bottom', "t", units='s')
        self.PUMPplot.showGrid(False, True)
        self.PUMPcurves[0] = self.PUMPplot.plot(self.t, self.df['flow1'], pen=self.pen1, name='PID1')
        self.PUMPcurves[1] = self.PUMPplot.plot(self.t, self.df['flow2'], pen=self.pen2, name='PID2')

    def __PUMPwidgets(self):
        ## Create widgets for TEC commands
        button_size = self.button_size*3 
        self.btnPUMP1set    = QtWidgets.QPushButton(">>")          # Sends new PUMP1 setpoint
        self.btnPUMP1set.setFixedWidth(self.button_size)
        self.btnPUMP1set.setFixedHeight(self.button_size)
        self.btnPUMP1set.clicked.connect(self.setPUMP1)
        self.lblPUMP1       = QtWidgets.QLabel("PID1 (mlpm):")
        self.spPUMP1        = QtWidgets.QSpinBox()
        self.spPUMP1.setRange(150,500)

        self.btnPUMP2set    = QtWidgets.QPushButton(">>")          # Sends new PUMP2 setpoint
        self.btnPUMP2set.setFixedWidth(self.button_size)
        self.btnPUMP2set.setFixedHeight(self.button_size)
        self.btnPUMP2set.clicked.connect(self.setPUMP2)
        self.lblPUMP2       = QtWidgets.QLabel("PID2 (mlpm):")
        self.spPUMP2        = QtWidgets.QSpinBox()
        self.spPUMP2.setRange(150,500)        

        ## Create a grid layout to manage the TEC controls size and position
        self.pumpControlLayout = QtWidgets.QGridLayout()

        self.pumpControlLayout.addWidget(self.lblPUMP1,      0, 0)
        self.pumpControlLayout.addWidget(self.spPUMP1,       0, 1)
        self.pumpControlLayout.addWidget(self.btnPUMP1set,   0, 2)

        self.pumpControlLayout.addWidget(self.lblPUMP2,      1, 0)
        self.pumpControlLayout.addWidget(self.spPUMP2,       1, 1)
        self.pumpControlLayout.addWidget(self.btnPUMP2set,   1, 2)

    def update(self):

        try: 
            self.datastring = self.connection.recv(1024).decode('UTF-8')
            #print(self.datastring)

            if self.datastring:
                ####### syntax changed for the status byte... ignore
                ####### additional variables at the end
                
                ###### DATAFRAME version
                #Eliminate first element
                self.df = self.df[1:self.numSamples]
                values = self.datastring.split( )
                newData = self.df.iloc[[-1]].to_dict('records')[0]
                for k, f, v in zip(self.keys, self.functions, values):
                    try:
                        newData[k] = f(v)
                        #print("{}: Apply funtion {} to {} type={}".format(k, f, v, type(newData[k])))
                    except:
                        print("could not apply funtion", str(f),"to",str(v))

                self.df = pd.concat([self.df,pd.DataFrame([newData])],ignore_index=True)

                statusbyte = newData['status']
                for k, j in zip(self.statusKeys, range(len(self.statusKeys))):
                    self.statusDict[k] = int(statusbyte[j])

                statusbyte = newData['lamps']
                self.lampString = ''
                for k, j in zip(self.lampKeys, range(len(self.lampKeys))):
                    self.lampDict[k] = int(statusbyte[j])
                    if j > 2:
                        ## LampString has the most significant bit to the left
                        self.lampString = self.lampString + statusbyte[j]
                
                if self.device.model == 2:
                    statusbyte = newData['tecbyte']
                    for k, j in zip(self.tecKeys, range(len(self.tecKeys))):
                        self.tecDict[k] = int(statusbyte[j])

                #if self.statusDict['voc1']:
                #    self.PIDcurves[0].setData(self.t, self.df['svoc1'])
                #    self.PIDcurves[1].setData(self.t, self.df['voc1'])
                #else:
                #    self.PIDcurves[0].clear()
                #    self.PIDcurves[1].clear()
                #
                #if self.statusDict['voc2']:
                #    self.PIDcurves[2].clear()
                #    #self.PIDcurves[2].setData(self.t, self.df['svoc2'])
                #    self.PIDcurves[3].setData(self.t, self.df['voc2'])
                #else:
                #    self.PIDcurves[2].clear()
                #    self.PIDcurves[3].clear()
                # 2024.03.20 VOC Curves always on. A. Keller
                self.PIDcurves[2].clear()
                self.PIDcurves[0].setData(self.t, self.df['svoc1'])
                self.PIDcurves[1].setData(self.t, self.df['voc1'])
                self.PIDcurves[3].setData(self.t, self.df['voc2'])

                # Data is received in mlpm. Dividing through 1000 to use pyqugraph autolabeling
                self.Fcurves[0].setData(self.t, self.df['mfc1']/1000)
                self.Fcurves[1].setData(self.t, self.df['mfc2']/1000)

                self.RHcurves[0].setData(self.t, self.df['sinrH'])
                self.RHcurves[1].setData(self.t, self.df['inrH'])
                self.Tcurves[0].setData(self.t, self.df['inT'])
                self.Tcurves[1].setData(self.t, self.df['tbath'])
                self.OFRTcurves[0].setData(self.t, self.df['tuv'])
                # Data is received in mV. Convert using calibration constant
                self.OFRUVcurves[0].setData(self.t, self.df['iuv']*self.device.uv_constant/1000/1000000)
                self.PUMPcurves[0].setData(self.t, self.df['flow1'])
                self.PUMPcurves[1].setData(self.t, self.df['flow2'])
                
                if self.device.model == 2:
                    self.TECcurves[0].setData(self.t, self.df['sb1'])
                    self.TECcurves[1].setData(self.t, self.df['sb2'])
                    self.TECcurves[2].setData(self.t, self.df['tec1'])
                    self.TECcurves[3].setData(self.t, self.df['tec2'])
                    self.TECcurves[4].setData(self.t, self.df['b1'])
                    self.TECcurves[5].setData(self.t, self.df['b2'])
                    ## 2024.02.02 This was wrongly displaying the tec2 temperature!
                    #self.TECcurves[3].setData(self.t, self.df['tec2'])

# Modified to avoid rounding error: A. Keller 14.3.2024
                    self.lblTEC1.setText("  B: {:.1f}, TEC: {:.1f}, SP: {:.0f} degC     ".format(
                        newData['b1'],newData['tec1'],newData['sb1']))
# Modified to avoid rounding error: A. Keller 14.3.2024
                    self.lblTEC2.setText("  B: {:.1f}, TEC: {:.1f}, SP: {:.0f} degC     ".format(
                        newData['b2'],newData['tec2'],newData['sb2']))
                
####################################################################

#                self.lblBathrH.setText("".join((str(int(newData['inrH'])), "/",
# Modified to avoid rounding error: A. Keller 14.3.2024
                self.lblBathrH.setText("".join(("{:.1f}".format(newData['inrH']), "/",
                                               str(newData['sinrH']), " %rH")))
                self.lblBathT.setText("".join(("Bath T:",
                                               str(newData['tbath']), " degC")))
                self.lblTubeT.setText("".join(("VOC: ", str(int(newData['tvoc'])), "/",
                                               str(newData['stvoc']), " degC")))
# Modified to avoid rounding error: A. Keller 14.3.2024
#                self.lblLampsData.setText("".join(("ORF: ",str(int(newData['tuv'])), " degC, ",
                self.lblLampsData.setText("".join(("ORF: ","{:.1f}".format(newData['tuv']), " degC, ",
                                                   str(int(newData['iuv']*self.device.uv_constant/1000)), " uA" )))
# Modified to avoid rounding error: A. Keller 14.3.2024
#                self.lblInletData.setText("".join(("Inlet: ",str(int(newData['inT'])), " degC, ",
                self.lblInletData.setText("".join(("Inlet: ","{:.1f}".format(newData['inT']), " degC, ",
# Modified to avoid rounding error: A. Keller 14.3.2024
#                                                   str(int(newData['inrH'])), "% rH" )))
                                                   "{:.1f}".format(newData['inrH']), "% rH" )))
                self.lblPump1.setText("".join(("Pump1 (", "{:.2f}".format(newData['flow1']), " slpm)")))
                self.lblPump2.setText("".join(("Pump2 (", "{:.2f}".format(newData['flow2']), " slpm)")))
                self.lblVOC1.setText("".join(("VOC1: ",str(int(newData['voc1'])), "/",
                                               str(newData['svoc1']), " mV")))
                self.lblVOC2.setText("".join(("VOC2: ",str(int(newData['voc2'])), " mV")))
                #self.lblMFC2.setText("".join(("MFC2: ",str(int(newData['mfc2'])), " mlpm")))

                # Initialize some indicators
                if self.firstLoop:
                    self.firstLoop = False
                    self.spMFC2.setValue(int(newData['mfc2']))
                    self.spSVOC1.setValue(int(newData['svoc1']))
                    self.spVOCT.setValue(int(newData['stvoc']))
                    self.spRH.setValue(int(newData['sinrH']))
                    self.spPUMP1.setValue(int(newData['flow1']*1000))
                    self.spPUMP2.setValue(int(newData['flow2']*1000))
                    if self.device.model == 2:
                        self.spTEC1.setValue(int(newData['sb1']))
                        self.spTEC2.setValue(int(newData['sb2']))
                
                if (self.lampDict['lamp0'] or self.lampDict['lamp1'] or self.lampDict['lamp2'] or
                    self.lampDict['lamp3'] or self.lampDict['lamp4']):
                    self.lblLamp.setStyleSheet('color: green')
                    self.lamps_status = True
                else:
                    self.lblLamp.setStyleSheet('color: red')
                    self.lamps_status = False

                for status, btn in zip(self.lampString[::-1], self.lamps):
                    if int(status) > 0:
                        #btn.setStyleSheet("background-color: green")
                        btn.setStyleSheet("color: green")
                    else:
                        #btn.setStyleSheet("background-color: red")
                        btn.setStyleSheet("color: red")

                if self.statusDict['voc1']:
                    self.lblVOC1.setStyleSheet('color: green')
                else:
                    self.lblVOC1.setStyleSheet('color: red')

                if self.statusDict['voc2']:
                    self.lblVOC2.setStyleSheet('color: green')
                else:
                    self.lblVOC2.setStyleSheet('color: red')

                if self.statusDict['tube_heat']:
                    self.lblVOCTctr.setStyleSheet('color: green')
                else:
                    self.lblVOCTctr.setStyleSheet('color: red')

                if self.statusDict['pump1']:
                    self.lblPump1.setStyleSheet('color: green')
                else:
                    self.lblPump1.setStyleSheet('color: red')

                if self.statusDict['pump2']:
                    self.lblPump2.setStyleSheet('color: green')
                else:
                    self.lblPump2.setStyleSheet('color: red')

                if self.statusDict['rH']:
                    self.lblBathrH.setStyleSheet('color: green')
                else:
                    self.lblBathrH.setStyleSheet('color: red')

                if self.device.model == 2:
                    txtStatus = "TEC Status: "
                    hasStatus = 0
                    newDict = self.tecDict.copy()
                    newDict.pop('tec1', None)
                    newDict.pop('tec2', None)
                    newDict.pop('tec1mode', None)
                    newDict.pop('tec2mode', None)

                    ### check if tec response corresponds with status
                    if not (self.statusDict['tec1'] == self.tecDict['tec1']):
                        txtStatus = txtStatus + "waiting for TEC1"
                        hasStatus = 1
                    if not (self.statusDict['tec2'] == self.tecDict['tec2']):
                        if hasStatus:
                            txtStatus = txtStatus + ", "
                        txtStatus = txtStatus + "waiting for TEC2"
                        hasStatus = 1

                   ### check other possible error codes 
                    for key, status in newDict.items():
                        if status:
                            if hasStatus:
                                txtStatus = txtStatus + ", "
                            txtStatus = txtStatus + key
                            hasStatus = 1

                    ### Display error if hasStatus flag exists
                    if hasStatus:
                        self.lblTECStatus.setText(txtStatus)
                        self.lblTECStatus.setStyleSheet("background-color: yellow; border: 1px solid black;")
                    else:
                        self.lblTECStatus.setText("TEC Status: OK")
                        self.lblTECStatus.setStyleSheet("background-color: lightgreen;  border: 0px;")

                    ### Check TEC1 status and mode
                    if self.tecDict['tec1']:
                        if self.tecDict['tec1mode']: # Heating = 1, Cooling or OFF = 0
                            self.lblTEC1mode.setStyleSheet('color: red')
                            self.lblTEC1.setStyleSheet('color: red')
                            mode = "heat"
                            self.btnTEC1cool.setEnabled(False)
                            self.btnTEC1heat.setText("off")
                        else:
                            self.lblTEC1mode.setStyleSheet('color: blue')
                            self.lblTEC1.setStyleSheet('color: blue')
                            mode = "cool"
                            self.btnTEC1heat.setEnabled(False)
                            self.btnTEC1cool.setText("off")
                        self.lblTEC1mode.setText("".join(("TEC1: ", mode)))
                    else:
                        self.lblTEC1mode.setStyleSheet('color: black')
                        self.lblTEC1.setStyleSheet('color: black')
                        self.lblTEC1mode.setText("TEC: off")
                        self.btnTEC1heat.setEnabled(True)
                        self.btnTEC1heat.setText("heat")
                        self.btnTEC1cool.setEnabled(True)
                        self.btnTEC1cool.setText("cool")
                        
                    if self.tecDict['tec2']:
                        if self.tecDict['tec2mode']: # Heating = 1, Cooling or OFF = 0
                            self.lblTEC2mode.setStyleSheet('color: red')
                            self.lblTEC2.setStyleSheet('color: red')
                            self.btnTEC2cool.setEnabled(False)
                            self.btnTEC2heat.setText("off")
                            mode = "heat"
                        else:
                            self.lblTEC2mode.setStyleSheet('color: blue')
                            self.lblTEC2.setStyleSheet('color: blue')
                            mode = "cool"
                            self.btnTEC2heat.setEnabled(False)
                            self.btnTEC2cool.setText("off")
                        self.lblTEC2mode.setText("".join(("TEC2: ", mode)))
                    else:
                        self.lblTEC2mode.setStyleSheet('color: black')
                        self.lblTEC2.setStyleSheet('color: black')
                        self.lblTEC2mode.setText("TEC2: off")
                        self.btnTEC2heat.setEnabled(True)
                        self.btnTEC2heat.setText("heat")
                        self.btnTEC2cool.setEnabled(True)
                        self.btnTEC2cool.setText("cool")
                                    
        except Exception as e:
            print(e, file=sys.stderr)
##            raise

    def sendSerialCMD(self):
        commands = [self.lineSERIAL.text().encode("ascii")]
        print(commands, file=sys.stderr)
        self.device.send_commands(commands, open_port = True)
        self.lineSERIAL.clear()

    def setMFC2(self):
        self.device.set_mfc2(self.spMFC2.value() ,open_port = True)

    def setSVOC1(self):
        self.device.set_voc1(self.spSVOC1.value() ,open_port = True)

    def setVOCT(self):
        self.device.set_tubeT(self.spVOCT.value() ,open_port = True)

    def setTEC1(self):
        self.device.set_TEC(1, self.spTEC1.value() ,open_port = True)
#        self.device.set_TECMode(1, self.cbTEC1.currentIndex() ,open_port = True)

    def setTEC2(self):
        self.device.set_TEC(2, self.spTEC2.value() ,open_port = True)
#        self.device.set_TECMode(2, self.cbTEC2.currentIndex() ,open_port = True)
        
    def setRH(self):
        self.device.set_rH(self.spRH.value() ,open_port = True)

    def setPUMP1(self):
        self.device.set_pump(1, self.spPUMP1.value() ,open_port = True)

    def setPUMP2(self):
        self.device.set_pump(2, self.spPUMP2.value() ,open_port = True)
            
    def toggleAllLamps(self):
        if self.lamps_status:
            self.device.set_lamps('00000', open_port = True)
        else:
            self.device.set_lamps('11111', open_port = True)

    def toggleLamp(self, lamp):
        print("Old Lamp String: " + self.lampString[::-1])
        ## Reverse the string to change lamps according to GUI
        reverseString = self.lampString[::-1]
        new_value = str(int(reverseString[lamp]) ^ 1)
        s = list(reverseString)
        s[lamp] = new_value
        ## Join and reverse new string for compatibility with firmware
        new_string = ("".join(s))[::-1]
        print("New lamp String: " + new_string[::-1])
        self.device.set_lamps(new_string, open_port = True)

    def toggleVOCHeater(self):
        if self.statusDict['tube_heat']:
            commands = [self.device.tube_off_str]
        else:
            commands = [self.device.tube_on_str]
        self.device.send_commands(commands, open_port = True)

    def toggleTEC1(self):
        if self.statusDict['tec1']:
            commands = [self.device.tec1_off_str]
        else:
            commands = [self.device.tec1_on_str]
        self.device.send_commands(commands, open_port = True)

    def toggleTEC1heat(self):
        if self.statusDict['tec1']:
            commands = [self.device.tec1_off_str]
        else:
            commands = [self.device.tec1_on_str]
            self.TEC1Mode(1)
        self.device.send_commands(commands, open_port = True)

    def toggleTEC1cool(self):
        if self.statusDict['tec1']:
            commands = [self.device.tec1_off_str]
        else:
            commands = [self.device.tec1_on_str]
            self.TEC1Mode(0)
        self.device.send_commands(commands, open_port = True)

    def toggleTEC2heat(self):
        if self.statusDict['tec2']:
            commands = [self.device.tec2_off_str]
        else:
            commands = [self.device.tec2_on_str]
            self.TEC2Mode(1)
        self.device.send_commands(commands, open_port = True)

    def toggleTEC2cool(self):
        if self.statusDict['tec2']:
            commands = [self.device.tec2_off_str]
        else:
            commands = [self.device.tec2_on_str]
            self.TEC2Mode(0)
        self.device.send_commands(commands, open_port = True)

    def toggleTEC2(self):
        if self.statusDict['tec2']:
            commands = [self.device.tec2_off_str]
        else:
            commands = [self.device.tec2_on_str]
        self.device.send_commands(commands, open_port = True)

    def TEC1Mode(self, i):
        self.device.set_TECMode(1, i ,open_port = True)

    def TEC2Mode(self, i):
        self.device.set_TECMode(2, i ,open_port = True)
        
    def toggleVOC1(self):
        if self.statusDict['voc1']:
            commands = [self.device.voc1_off_str]
        else:
            commands = [self.device.voc1_on_str]
        self.device.send_commands(commands, open_port = True)

    def toggleVOC2(self):
        if self.statusDict['voc2']:
            commands = [self.device.voc2_off_str]
        else:
            commands = [self.device.voc2_on_str]
        self.device.send_commands(commands, open_port = True)

    def togglePump1(self):
        if self.statusDict['pump1']:
            commands = [self.device.pump1_off_str]
        else:
            commands = [self.device.pump1_on_str]
        self.device.send_commands(commands, open_port = True)

    def togglePump2(self):
        if self.statusDict['pump2']:
            commands = [self.device.pump2_off_str]
        else:
            commands = [self.device.pump2_on_str]
        self.device.send_commands(commands, open_port = True)
        
    def togglerH(self):
        if self.statusDict['rH']:
            commands = [self.device.rH_off_str]
        else:
            commands = [self.device.rH_on_str]
        self.device.send_commands(commands, open_port = True)


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys

    # READ ini file
    config_file = base_path + '/config.ini'
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        host_name = eval(config['TCP_INTERFACE']['HOST_NAME'])
        host_port = eval(config['TCP_INTERFACE']['HOST_PORT'])
    else:
        print("Could not find the configuration file: {}".format(config_file), file=sys.stderr)
        exit()


    vis = Visualizer(host_name=host_name, host_port=host_port, config_file=config_file)

    timer = QtCore.QTimer()
    timer.timeout.connect(vis.update)
    timer.start(int(vis.deltaT*1000))

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()
