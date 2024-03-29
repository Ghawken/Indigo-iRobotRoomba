#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import logging
try:
    import indigo
except:
    pass

import sys
import os.path
import time
import requests
import json
import logging
#import OpenSSL
#rom base64 import b64encode
import traceback
from roomba import Roomba
import platform
from roomba import password
from roomba import irobotAPI_Maps
#import paho.mqtt.client as mqtt
import threading
import datetime
from builtins import str as text
import locale
import shutil
from os import path

try:
    import indigo
except:
    pass

kCurDevVersCount = 1        # current version of plugin devices
################################################################################
# New Indigo Log Handler - display more useful info when debug logging
# update to python3 changes
################################################################################
class IndigoLogHandler(logging.Handler):
    def __init__(self, display_name, level=logging.NOTSET):
        super().__init__(level)
        self.displayName = display_name

    def emit(self, record):
        """ not used by this class; must be called independently by indigo """
        logmessage = ""
        try:
            levelno = int(record.levelno)
            is_error = False
            is_exception = False
            if self.level <= levelno:  ## should display this..
                if record.exc_info !=None:
                    is_exception = True
                if levelno == 5:	# 5
                    logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
                elif levelno == logging.DEBUG:	# 10
                    logmessage = '({}:{}:{}): {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
                elif levelno == logging.INFO:		# 20
                    logmessage = record.getMessage()
                elif levelno == logging.WARNING:	# 30
                    logmessage = record.getMessage()
                elif levelno == logging.ERROR:		# 40
                    logmessage = '({}: Function: {}  line: {}):    Error :  Message : {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
                    is_error = True
                if is_exception:
                    logmessage = '({}: Function: {}  line: {}):    Exception :  Message : {}'.format(path.basename(record.pathname), record.funcName, record.lineno, record.getMessage())
                    indigo.server.log(message=logmessage, type=self.displayName, isError=is_error, level=levelno)
                    if record.exc_info !=None:
                        etype,value,tb = record.exc_info
                        tb_string = "".join(traceback.format_tb(tb))
                        indigo.server.log(f"Traceback:\n{tb_string}", type=self.displayName, isError=is_error, level=levelno)
                        indigo.server.log(f"Error in plugin execution:\n\n{traceback.format_exc(30)}", type=self.displayName, isError=is_error, level=levelno)
                    indigo.server.log(f"\nExc_info: {record.exc_info} \nExc_Text: {record.exc_text} \nStack_info: {record.stack_info}",type=self.displayName, isError=is_error, level=levelno)
                    return
                indigo.server.log(message=logmessage, type=self.displayName, isError=is_error, level=levelno)
        except Exception as ex:
            indigo.server.log(f"Error in Logging: {ex}",type=self.displayName, isError=is_error, level=levelno)
################################################################################
class Plugin(indigo.PluginBase):

    ########################################
    # Main Plugin methods
    ########################################
    def __init__(self, plugin_id, plugin_display_name, plugin_version, pluginPrefs):
        indigo.PluginBase.__init__(self, plugin_id, plugin_display_name, plugin_version, pluginPrefs)
        ################################################################################
        # Setup Logging
        ################################################################################
        try:
            self.logLevel = int(self.pluginPrefs["showDebugLevel"])
            self.fileloglevel = int(self.pluginPrefs["showDebugFileLevel"])
        except:
            self.logLevel = logging.INFO
            self.fileloglevel = logging.DEBUG

        self.logger.removeHandler(self.indigo_log_handler)

        self.indigo_log_handler = IndigoLogHandler(plugin_display_name, logging.INFO)
        ifmt = logging.Formatter("%(message)s")
        self.indigo_log_handler.setFormatter(ifmt)
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.addHandler(self.indigo_log_handler)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)s\t%(name)s.%(funcName)s:\t%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)
        self.plugin_file_handler.setLevel(self.fileloglevel)

        MAChome     = os.path.expanduser("~")+"/"
        self.mainfolderLocation = MAChome+"Documents/Indigo-iRobotRoomba/"

        #self.mappingfile = self.mainfolderLocation + str(address)+"-mapping-data.json"
        system_version, product_version, longer_name = self.get_macos_version()
        self.logger.info("{0:=^130}".format(f" Initializing New Plugin Session for Plugin: {plugin_display_name} "))
        self.logger.info("{0:<30} {1}".format("Plugin name:", plugin_display_name))
        self.logger.info("{0:<30} {1}".format("Plugin version:", plugin_version))
        self.logger.info("{0:<30} {1}".format("Plugin ID:", plugin_id))
        self.logger.info("{0:<30} {1}".format("Indigo version:", indigo.server.version) )
        self.logger.info("{0:<30} {1}".format("System version:", f"{system_version} {longer_name}" ))
        self.logger.info("{0:<30} {1}".format("Product version:", product_version))
        self.logger.info("{0:<30} {1}".format("Silicon version:", str(platform.machine()) ))
        self.logger.info("{0:<30} {1}".format("Python version:", sys.version.replace('\n', '')))
        self.logger.info("{0:<30} {1}".format("Python Directory:", sys.prefix.replace('\n', '')))

        self.allMappingData = {}
        self.allFavouritesData = {}

        self.pluginprefDirectory = '{}/Preferences/Plugins/com.GlennNZ.indigoplugin.irobot/'.format(indigo.server.getInstallFolderPath())

        self.logger.debug(u"logLevel = " + str(self.logLevel))
        self.debugTrue = self.pluginPrefs.get('debugTrue', '')
        self.debugOther = self.pluginPrefs.get('debugOther', True)
        self.newiroombaData = {}

        ## Load json database of errors
        try:
            with open('errormsg.json', 'r', encoding='utf-8') as json_file:
                self.iroombaData = json.load(json_file)

            self.logger.debug("Reading iRoomba Strings as JSON Data From File")
            self.iroombaData = self.iroombaData['resources']['string']
          #  for strings in self.iroombaData:
               # self.logger.debug( text(strings) )

            self.newiroombaData = { d['_name'].encode("utf-8") : d['__text'].encode('utf-8')  for d in self.iroombaData}
            self.iroombaData = None

            self.logger.debug("Done reading new json Data file")
        except:
            self.logger.debug("Exception in Json database", exc_info=True)
            pass

        self.logger.info("{0:=^130}".format(f" End Initializing Plugin Session for Plugin: {plugin_display_name} "))
        if self.debugOther:
            self.logger.debug(f"{self.newiroombaData=}")
        #self.logger.debug(json.dumps(self.iroombaData, sort_keys=True, indent=4))
        #self.logger.error(self.iroombaData['resources']['abc_capital_on'])

    def get_macos_version(self):
        try:
            version, _, _ = platform.mac_ver()
            longer_version = platform.platform()
            self.logger.info(f"{version}")
            longer_name = self.get_macos_marketing_name(version)
            return version, longer_version, longer_name
        except:
            self.logger.debug("Exception:",exc_info=True)
            return "","",""

    def get_macos_marketing_name(self, version: str) -> str:
        """Return the marketing name for a given macOS version number."""
        versions = {
            "10.0": "Cheetah",
            "10.1": "Puma",
            "10.2": "Jaguar",
            "10.3": "Panther",
            "10.4": "Tiger",
            "10.5": "Leopard",
            "10.6": "Snow Leopard",
            "10.7": "Lion",
            "10.8": "Mountain Lion",
            "10.9": "Mavericks",
            "10.10": "Yosemite",
            "10.11": "El Capitan",
            "10.12": "Sierra",
            "10.13": "High Sierra",
            "10.14": "Mojave",
            "10.15": "Catalina",
            "11": "Big Sur",  # Just use the major version number for macOS 11+
            "12": "Monterey",
            "13": "Ventura",
            "14": "Sonoma",
        }
        major_version_parts = version.split(".")
        # If the version is "11" or later, use only the first number as the key
        if int(major_version_parts[0]) >= 11:
            major_version = major_version_parts[0]
        # For macOS "10.x" versions, use the first two numbers as the key
        else:
            major_version = ".".join(major_version_parts[:2])
        self.logger.debug(f"Major Version== {major_version}")
        return versions.get(major_version, f"Unknown macOS version for {version}")

    def pluginStore(self):
        self.logger.info(u'Opening Plugin Store.')
        iurl = 'http://www.indigodomo.com/pluginstore/132/'
        self.browserOpen(iurl)

    def startup(self):
        #self.logger.info(u"Starting Roomba")
        self.triggers = { }
        self.masterState = None
        self.currentstate = ""
        #self.updater = GitHubPluginUpdater(self)
        self.KILLcount = 0
        self.restarted = 0
        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
        self.passwordReturned = "not set yet"
        self.logger.debug(u"updateFrequency = " + str(self.updateFrequency))
        self.next_update_check = time.time()

        if not os.path.exists(self.pluginprefDirectory):
            os.makedirs(self.pluginprefDirectory)

        ## Check old config files and move them all.
        try:
            file_names = os.listdir(self.mainfolderLocation)
            source_dir = self.mainfolderLocation
            target_dir = self.pluginprefDirectory
            for file_name in file_names:
                shutil.move(os.path.join(source_dir, file_name), target_dir)
        except:
            self.logger.debug("Error trying to move files.  Skippping.", exc_info=False)

        self.continuous = self.pluginPrefs.get('continuous', False)

        #automatically disconnect reconnect even in continuous after elapsed time - 12 hours
        self.reconnectFreq = 12*60*60
        # Testing only below
        #self.reconnectFreq = 2*60
        self.datetimeFormat = self.pluginPrefs.get('datetimeFormat', '%c')
        self.connectTime = self.reconnectFreq +time.time()

      #  self.statusFrequency = float(self.pluginPrefs.get('statusFrequency', "10")) * 60.0
        self.statusFrequency = 60
        self.logger.debug(u"statusFrequency = " + str(self.statusFrequency))
        self.next_status_check = time.time()
       # self.myroomba = None
        #self.connected = False

        #self.connectedtoName = "none"
        self.roomba_list = []
        self.errorStrings = {
            "0": "None",
            "1": "Left wheel off floor",
            "2": "Main brushes stuck",
            "3": "Right wheel off floor",
            "4": "Left wheel stuck",
            "5": "Right wheel stuck",
            "6": "Stuck near a cliff",
            "7": "Left wheel error",
            "8": "Bin error",
            "9": "Bumper stuck",
            "10": "Right wheel error",
            "11": "Bin error",
            "12": "Cliff sensor issue",
            "13": "Both wheels off floor",
            "14": "Bin missing",
            "15": "Reboot required",
            "16": "Bumped unexpectedly",
            "17": "Path blocked",
            "18": "Docking issue",
            "19": "Undocking issue",
            "20": "Docking issue",
            "21": "Navigation problem",
            "22": "Navigation problem",
            "23": "Battery issue",
            "24": "Navigation problem",
            "25": "Reboot required",
            "26": "Vacuum problem",
            "27": "Vacuum problem",
            "28": "Error",
            "29": "Software update needed",
            "30": "Vacuum problem",
            "31": "Reboot required",
            "32": "Smart map problem",
            "33": "Path blocked",
            "34": "Reboot required",
            "35": "Unrecognised cleaning pad",
            "36": "Bin full",
            "37": "Tank needed refilling",
            "38": "Vacuum problem",
            "39": "Reboot required",
            "40": "Navigation problem",
            "41": "Timed out",
            "42": "Localization problem",
            "43": "Navigation problem",
            "44": "Pump issue",
            "45": "Lid open",
            "46": "Low battery",
            "47": "Reboot required",
            "48": "Path blocked",
            "52": "Pad required attention",
            "53": "Software update required",
            "54": "Blades stuck",
            "55": "Left blades stuck",
            "56":"Right blades stuck",
            "57":"Cutting deck stuck",
            "58":"Navigation problem",
            "59":"Tilt detected",
            "60":"Rolled over",
            "62":"Stopped button pressed",
            "63":"Hardware Error",
            "65": "Hardware problem detected",
            "66": "Low memory",
            "67": "Handle lifted",
            "68": "Dead camera",
            "70":"Problem sensing beacons",
            "73": "Pad type changed",
            "74": "Max area reached",
            "75": "Navigation problem",
            "76": "Hardware problem detected",
            "78":"Left wheel error",
            "79":"Right wheel error",
            "85":"Path to charging station blocked",
            "86": "Path to charging station blocked",
            "88": "Navigation problem",
            "89": "Mission runtime too long",
            "101": "Battery isn't connected",
            "102": "Charging error",
            "103": "Charging error",
            "104": "No charge current",
            "105": "Charging current too low",
            "106": "Battery too warm",
            "107": "Battery temperature incorrect",
            "108": "Battery communication failure",
            "109": "Battery error",
            "110": "Battery cell imbalance",
            "111": "Battery communication failure",
            "112": "Invalid charging load",
            "114": "Internal battery failure",
            "115": "Cell failure during charging",
            "116": "Charging error of Home Base",
            "118": "Battery communication failure",
            "119": "Charging timeout",
            "120": "Battery not initialized",
            "121": "Clean the Charging contacts",
            "122": "Charging system error",
            "123": "Battery not initialized",
            "216": "Charging base bag full",
            "224": "Smart Map Problem"
        }
        # self.errorStrings = {
        #     '0': 'No Error',
        #     '1': 'Place Roomba on a flat surface then press CLEAN to restart.',
        #     '2': 'Clear Roombas debris extractors, then press CLEAN to restart.',
        #     '5': 'Left/Right. Clear Roombas wheel, then press CLEAN to restart.',
        #     '6': 'Move Roomba to a new location then press CLEAN to restart. The cliff sensors are dirty, it is hanging over a drop, or it is stuck on a dark surface.',
        #     '8': 'The fan is stuck or its filter is clogged.',
        #     '9': 'Tap Roombas bumper, then press CLEAN to restart.',
        #     '10': 'The left or right wheel is not moving.',
        #     '11': 'Roomba has an internal error.',
        #     '14': 'Re-install Roomba’s bin then press CLEAN to restart. The bin has a bad connection to the robot.',
        #     '15': 'Press CLEAN to restart. Roomba has an internal error',
        #     '16': 'Place Roomba on a flat surface then press CLEAN to restart. Roomba has started while moving or at an angle, or was bumped while running.',
        #     '17': 'The cleaning job is incomplete.',
        #     '18': 'Roomba cannot return to the Home Base or starting position.',
        # }

        self.notReadyStrings = {
            '0' : 'Ready',
            '1': 'Near a cliff',
            '2': 'Both wheels off floor',
            '3': 'Left wheel dropped',
            '4': 'Right wheel dropped',
            '7' : 'Bin Missing',
            "8": "Reboot needed",
            "9":"Software being updated",
            '11' : "Vacuum problem",
            "14" : "Not ready for that request",
            '15': 'Battery Low',
            '16': 'Bin Full',
            "17": "Navigation problem",
            "18" : "Software upgrade",
            "19" : "Charging error",
            "21" : "Reboot required",
            "22" : "Navigation problem",
            "23":"Battery issue",
            "24":"Smart Map problem",
            "25":"Reboot required",
            "26": "Reboot required",
            "27": "Reboot required",
            "28": "Reboot required",
            "31": "Tank low",
            "32":"Lid open",
            "33":"Bumper stuck",
            "34":"Unrecognised cleaning pad",
            "35":"Unrecognised cleaning pad"  ,
            "36":"Unable to empty bin: Clog",
            "37":"Battery issue",
            "38":"Battery issue",
            "39":"Saving Clean Map",
            "40":"Software update required",
            "51":"Hardware problem detectec",
            "53":"Left wheel error",
            "54":"Right wheel error",
            "55":"Not on charging station",
            "57":"Navigation problem",
            "58":"Workspace path error: Retrain Roomba",
            "59": "Workspace path error: Retrain Roomba",
            "60": "Workspace path error: Retrain Roomba",
            "61":"Wheel motor over temp",
            "62":"Wheel motor under temp",
            "63":"Blade motor over temp",
            "64":"Blade motor under temp",
            "65":"Software error",
            "66":"Cleaning unavailable. Check subscriptions status",
            "67":"Hardware problem Detected",
            '68': 'Saving smart map edits'
        }


    def shutdown(self):
        indigo.server.log(u"Shutting down Roomba")

    def restartPlugin(self):
        indigo.server.log(u"restart Plugin Called.")
        plugin = indigo.server.getPlugin('com.GlennNZ.indigoplugin.irobot')
        plugin.restart()

    def runConcurrentThread(self):

        self.next_status_check = time.time()
        self.checkiRoombaConnectedtime = time.time() + 60*60
        self.checkAllRoombas()
        self.checkConnection = time.time()+ 60*60
        try:
            while True:
                if time.time() > self.next_status_check:
                    if self.debugTrue:
                        self.logger.debug(u'Updating Master States....')
                    self.updateMasterStates()
                    self.next_status_check = time.time() +60  ## 1 minute later update states

                if time.time() > self.checkConnection:
                    if self.debugTrue:
                        self.logger.debug(u'checking all Roombas are still connected now....')
                    self.checkAllRoombas()
                    self.checkConnection = time.time()+ 60 *60 # 60 minutes later

                if time.time() > self.checkiRoombaConnectedtime:
                    if self.debugTrue:
                        self.logger.debug(u'checking any Roombas still connected now....')
                    self.checkanyConnected()  ## and restart if more than 4 checks nothing connected -- 3-4 hours
                    self.checkiRoombaConnectedtime = time.time()+ 60 *60 #

                if time.time() > self.connectTime:
                    # Disconnect and Reconnect Roomba
                    if self.debugTrue:
                        self.logger.debug(u'Up for long enough reconnecting; to avoid MQTT failures.')
                    self.reconnectRoomba()
                    self.connectTime = time.time() + self.reconnectFreq

                self.sleep(20.0)

        except self.StopThread:
            pass

    def deviceStartComm(self, device):
        self.logger.debug(u"deviceStartComm called for " + device.name)
        #if self.debugOther:
         #   self.logger.debug(text(device))

        device.stateListOrDisplayStateIdChanged()   # update  from device.xml info if changed
        device.updateStateOnServer(key="IP",value=str(device.pluginProps['address']))

        if device.states['IP'] != "":
            self.updateVar(device.states['IP'], True)

        #device.type = indigo.kDevicerelay
        # readd this later
        #device.subType = indigo.kRelayDeviceSubType.Switch

        #device.replaceOnServer()
        #self.logger.error(text(device))

        #props = device.pluginProps
        if hasattr(device, 'onState')== False:  ## if custom
            self.logger.debug("onState Not in Props converting device..")
            device = indigo.device.changeDeviceTypeId(device, device.deviceTypeId)
            device.replaceOnServer()

        device = indigo.devices[device.id]
        props = device.pluginProps
        props["SupportsSensorValue"] = True
        props["SupportsOnState"] = True
        props["AllowSensorValueChange"] = False
        props["AllowOnStateChange"] = True
        props["SupportsStatusRequest"] = False
        device.replacePluginPropsOnServer(props)
        device.updateStateOnServer(key="onOffState", value=False, uiValue="Starting Device")

      #  self.checkAllRoombas()
        time.sleep(1)
        #self.getRoombaInfo(device)
        #self.getRoombaStatus(device)
        #self.getRoombaTime(device)
        #MAChome     = os.path.expanduser("~")+"/"

        folderLocation = self.pluginprefDirectory # MAChome+"Documents/Indigo-iRobotRoomba/"

        roombaIP = str(device.states['IP'])
        filename =  str(roombaIP)+"-mapping-data.json"
        file = folderLocation + filename
        favourites_file = folderLocation + str(roombaIP)+ "-favourites-data.json"

        if self.checkMapFile(device, file)== False:
            self.logger.debug(u'Mapping Data File Does Not Exist.')
            self.logger.info("No Cloud Mapping Data found for this device.  Please setup in Device Config if needed.")
        else:
            self.logger.debug(u'Mapping Data File Exists - using it')
            with open(file) as data_file:
                self.allMappingData[roombaIP] = json.load(data_file)

        if self.checkMapFile(device, favourites_file)== False:
            self.logger.debug(u'Favourites Data File Does Not Exist.')
            self.logger.info("No Cloud Favourites Data found for this device.  Please setup in Device Config if needed.")
        else:
            self.logger.debug(u'Favourites Data File Exists - using it')
            with open(favourites_file) as data_file:
                self.allFavouritesData[roombaIP] = json.load(data_file)


        self.logger.debug(text(self.allMappingData))

    def actionReturnRooms(self, filter, valuesDict,typeId, targetId):
        self.logger.debug(u'Generate Rooms from Mapping Data')
        self.logger.debug(targetId)
        myArray = []

        device = indigo.devices[targetId]
        ipaddress = device.states['IP']

        self.logger.debug(ipaddress)

        if str(ipaddress) in self.allMappingData:
            for items in self.allMappingData[str(ipaddress)]:
                if 'active_pmapv_details' in items:
                    if 'regions' in items['active_pmapv_details']:
                        for regions in items['active_pmapv_details']['regions']:
                            self.logger.debug(text(regions))
                            myArray.append( (regions['id'],regions['name'] ))
                    if 'zones' in items['active_pmapv_details']:
                        for zones in items['active_pmapv_details']['zones']:
                            self.logger.debug(text(zones))
                            myArray.append((zones['id']+str("Z"), zones['name']))
        else:
            self.logger.info("No room data available.  Please update or may not be possible with this model.")

        self.logger.debug(text(myArray))
        return myArray
    def actionReturnFavourites(self, filter, valuesDict,typeId, targetId):
        self.logger.debug(u'Generate Favourites from Favourites Data')
        self.logger.debug(targetId)
        myArray = []

        device = indigo.devices[targetId]
        ipaddress = device.states['IP']
        robotid = str(device.states['blid']).lower()
        self.logger.debug(f"{ipaddress=}\n{robotid=}")

        if str(ipaddress) in self.allFavouritesData:
            for items in self.allFavouritesData[str(ipaddress)]:
                if 'commanddefs' in items:
                    if 'robot_id' in items['commanddefs'][0]:
                        self.logger.debug(f"{items['commanddefs'][0]}")
                        if str(items['commanddefs'][0]['robot_id']).lower() == robotid:
                            self.logger.debug("Favourite for matching Robot Found")
                            self.logger.debug(f"{items}")
                            myArray.append((items['favorite_id'], items['name']))
        else:
            self.logger.info("No room data available.  Please update or may not be possible with this model.")

        self.logger.debug(text(myArray))
        return myArray

    def deviceStopComm(self, device):
        self.logger.debug(u"deviceStopComm called for " + device.name)
        self.disconnectRoomba(device)
        device.updateStateOnServer(key="deviceStatus", value="Communications Error")
        self.updateVar(device.states['IP'], False)
        device.updateStateOnServer(key="onOffState", value=False, uiValue="Communications Error")
        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    def updateVar(self, name, value):
        #self.logger.debug(u'updatevar run.')
        name = "iRoomba-"+name
        if not ('iRoombaDevices' in indigo.variables.folders):
            # create folder
            folderId = indigo.variables.folder.create('iRoombaDevices')
            folder = folderId.id
        else:
            folder = indigo.variables.folders.getId('iRoombaDevices')

        if name not in indigo.variables:
            NewVar = indigo.variable.create(name, value=str(value), folder=folder)
        else:
            indigo.variable.updateValue(name, str(value))
        return

    def triggerStartProcessing(self, trigger):
        self.logger.debug("Adding Trigger %s (%d) - %s" % (trigger.name, trigger.id, trigger.pluginTypeId))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.logger.debug("Removing Trigger %s (%d)" % (trigger.name, trigger.id))
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

    def actionControlDevice(self, action, device):
        self.logger.debug("actionControlDevice Called: action:"+text(action)+" for device :"+text(device.name))
        if device.deviceTypeId == "roombaDevice":
            currentOnState = device.states['onOffState']
            command = action.deviceAction
            if command == indigo.kDeviceAction.TurnOn:
                self.logger.debug("Turning On iRoomba Device: Sending Start Command")
                self.startRoombaAction("notUsed",device)
                ##### TURN OFF #####
            elif command == indigo.kDeviceAction.TurnOff:
                self.logger.debug("Turning Off/Docking iRoomba Device: Sending Dock Command")
                self.dockRoombaAction("notUsed",device)
                ##### TOGGLE #####
            elif command == indigo.kDeviceAction.Toggle:
                self.logger.debug("Toggling iRoomba Device")
                self.toggleRoombaAction("Notused",device)
            else:
                self.logger.debug("Unsupport Command sent:  Command Sent:"+text(command))
                return


    def triggerCheck(self, device):

        for triggerId, trigger in sorted(self.triggers.iteritems()):
            self.logger.debug("Checking Trigger %s (%s), Type: %s" % (trigger.name, trigger.id, trigger.pluginTypeId))

            if trigger.pluginProps["deviceID"] != str(device.id):
                self.logger.debug("\t\tSkipping Trigger %s (%s), wrong device: %s" % (trigger.name, trigger.id, device.id))
            else:
                if trigger.pluginTypeId == "notReady":
                    if device.states["NotReady"] != "0":
                        self.logger.debug("\tExecuting Trigger %s (%d)" % (trigger.name, trigger.id))
                        indigo.trigger.execute(trigger)
                elif trigger.pluginTypeId == "hasError":
                    if device.states["ErrorCode"] != "0":
                        self.logger.debug("\tExecuting Trigger %s (%d)" % (trigger.name, trigger.id))
                        indigo.trigger.execute(trigger)
                else:
                    self.logger.debug("\tUnknown Trigger Type %s (%d), %s" % (trigger.name, trigger.id, trigger.pluginTypeId))


    ########################################
    # Menu Methods
    ########################################

    ########################################
    # ConfigUI methods
    ########################################

    def validatePrefsConfigUi(self, valuesDict):
        self.logger.debug(u"validatePrefsConfigUi called")
        errorDict = indigo.Dict()

        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)

        return (True, valuesDict)

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            try:
                self.logLevel = int(valuesDict["showDebugLevel"])
                self.fileloglevel = int(valuesDict["showDebugFileLevel"])
            except:
                self.logger.exception("Error here")
                self.logLevel = logging.INFO
                self.fileloglevel = logging.DEBUG

            self.plugin_file_handler.setLevel(self.fileloglevel)
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"logLevel = " + str(self.logLevel))
            self.datetimeFormat = valuesDict.get('datetimeFormat', '%c')
            #self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
            self.logger.debug(u"updateFrequency = " + str(self.updateFrequency))
            self.next_update_check = time.time()
            self.debugTrue =valuesDict.get('debugTrue', '')
            self.debugOther = valuesDict.get('debugOther', True)
    ########################################
    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        self.logger.debug(u'closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):')
        self.logger.debug(
            u'     (' + text(valuesDict) + u', ' + text(userCancelled) + ', ' + text(typeId) + u', ' + text(
                devId) + u')')




    def validateDeviceConfigUi(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"validateDeviceConfigUi called")
        errorDict = indigo.Dict()
        address = valuesDict['address']
        if address == None:
            errorDict['address'] = u'IP Address can not be blank, please enter valid IP'
            return (False, valuesDict, errorDict)

        if self.checkConfigFile(valuesDict, deviceId)== False:
            self.logger.debug(u'Config File Does Not Exist.')
            errorDict['address'] = u'Configuration File Does Not exist - Please use Get Password button and instructions to create.'
            return (False,valuesDict, errorDict)
        else:
            self.logger.debug(u'Config File Exists - using it')
            valuesDict['password'] = 'OK.  Using Saved Config File.'

        iroombaName = valuesDict['roombaName']
        ipaddress = valuesDict['address']
        dev = indigo.devices[deviceId]
        if iroombaName == None or iroombaName == "":
            self.logger.debug("No name set in Config, using Device State")
            valuesDict['roombaName']= dev.states['Name']
        else:
            dev.updateStateOnServer("Name",iroombaName)
            self.logger.debug("Updated iRoomba Robot Name")

        dev.updateStateOnServer("IP",ipaddress)


        #Roomba.connect()
        return (True, valuesDict)


    ########################################

    def checkConfigFile(self,valuesDict, deviceId):
        #MAChome     = os.path.expanduser("~")+"/"
        folderLocation = self.pluginprefDirectory #+"Documents/Indigo-iRobotRoomba/"
        roombaIP = valuesDict['address']
        filename = str(roombaIP) + "-config.ini"
        file = folderLocation + filename
        self.logger.debug(u'file should equal:' + file)
        if os.path.isfile(file):
            return True
        return False

    def checkMapFile(self, device, file):

        self.logger.debug(u'Mapping File should equal:' + file)
        if os.path.isfile(file):
            return True
        return False

    def getRoombaMaps(self,valuesDict, typeId, deviceId):
        self.logger.debug(u"update Roomba Mapping Info: "+text(deviceId))

        device = indigo.devices[deviceId]
        roombaIP = valuesDict.get('address', 0)
        forceSSL = valuesDict.get('forceSSL',False)
        blid = str(device.states['blid'])
        useCloud = valuesDict.get('useCloud', False)
        cloudLogin = valuesDict.get('cloudLogin', '')
        cloudPassword = valuesDict.get('cloudPassword', '')

        if blid == None:
            self.logger.info("No ID found for iRoomba.  Please press get Password Cloud button to update.")
            self.logger.info("And then try this button again")
            return

        if blid == "":
            self.logger.info("No ID found for iRoomba.  Please press get Password Cloud button to update.")
            self.logger.info("And then try this button again")
            return

        if cloudLogin == "" or cloudPassword=="":
            self.logger.info("Please enter iRobot Cloud login and Password details and try again")
            return

        result = irobotAPI_Maps(self, address=roombaIP,useCloud=useCloud, cloudLogin=cloudLogin, cloudPassword=cloudPassword, blid=blid)

        try:
            self.sleep(1)
            roombaIP = str(device.states['IP'])
            folderLocation = self.pluginprefDirectory  # MAChome+"Documents/Indigo-iRobotRoomba/"
            filename = str(roombaIP) + "-mapping-data.json"
            file = folderLocation + filename
            favourites_file = folderLocation + str(roombaIP) + "-favourites-data.json"

            if self.checkMapFile(device, file) == False:
                self.logger.debug(u'Mapping Data File Does Not Exist.')
                self.logger.info("No Cloud Mapping Data found for this device.  Please setup in Device Config if needed.")
            else:
                self.logger.debug(u'Mapping Data File Exists - using it')
                with open(file) as data_file:
                    self.allMappingData[roombaIP] = json.load(data_file)

            if self.checkMapFile(device, favourites_file) == False:
                self.logger.debug(u'Favourites Data File Does Not Exist.')
                self.logger.info("No Cloud Favourites Data found for this device.  Please setup in Device Config if needed.")
            else:
                self.logger.debug(u'Favourites Data File Exists - using it')
                with open(favourites_file) as data_file:
                    self.allFavouritesData[roombaIP] = json.load(data_file)
        except:
            self.logger.exception("Exception Caughht loading files")


    def getRoombaPassword(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"getRoombaPassword called: "+text(deviceId))
        valuesDict['refreshCallbackMethod'] = 'refreshThreadData'
        device = indigo.devices[deviceId]
        device.updateStateOnServer('softwareVer', value='Unknown')
        roombaIP = valuesDict.get('address', 0)
        forceSSL = valuesDict.get('forceSSL',False)
        blid = str(device.states['blid'])
        useCloud = valuesDict.get('useCloud', False)
        cloudLogin = valuesDict.get('cloudLogin', '')
        cloudPassword = valuesDict.get('cloudPassword', '')

        if roombaIP == 0 or roombaIP == '':
            self.logger.error(u'IP Address cannot be Empty.  Please empty valid IP before using Get Password')
            return False
        #Roomba.connect()
        filename = str(roombaIP)+"-config.ini"
        self.softwareVersion = ''
        self.validatePrefsConfigUi(valuesDict)


        # result = password(self, address=roombaIP, file=filename, forceSSL=forceSSL  )
        # #self.logger.error(text(result))
        # if self.softwareVersion != '':
        #     self.logger.debug('Software Version of Roomba Found:'+text(self.softwareVersion))
        #     device.updateStateOnServer('softwareVer', value=self.softwareVersion)
        # if result == True:
        #     valuesDict['password'] = 'OK'
        #     self.logger.info(u'Password Saved. Click Ok.')

        ## Lets thread it...
        getPasswordThread = threading.Thread(target=self.threadgetPassword,args=[roombaIP, filename, forceSSL, device, self.softwareVersion, useCloud, cloudLogin,cloudPassword, blid])
        getPasswordThread.setDaemon(True)
        getPasswordThread.start()
        return valuesDict

    def refreshThreadData(self, valuesDict, typeId, deviceId):
        try:
            self.logger.debug(u"prefsRefreshCallback called")
            #self.logger.debug(u"valuesDict: {}".format(valuesDict))
            self.logger.debug(u'Checking Number of Active Threads:' + text(threading.activeCount() ) )
            if self.passwordReturned=="OK":
                valuesDict['password'] = 'OK'
                self.logger.info(u'Password Saved. Click Ok.')
                self.passwordReturned = "reset"
                valuesDict['refreshCallbackMethod'] = None
                #time.sleep(1)
                #self.updateMasterStates()
            elif self.passwordReturned == "Failed":
                valuesDict['refreshCallbackMethod'] = None
            return valuesDict

        except Exception as ex:
            self.logger.debug("Caught Exception refreshThreadData:"+text(ex))


    def threadgetPassword(self, roombaIP,filename,forceSSL, device, softwareversion, useCloud, cloudLogin, cloudPassword, blid):
        try:
            self.passwordReturned = "reset"
            self.logger.debug(u'Thread:Get Password called.' + u' & Number of Active Threads:' + text(threading.activeCount() ) )
            result = password(self, address=roombaIP, file=filename, useCloud=useCloud, cloudLogin=cloudLogin, cloudPassword=cloudPassword, forceSSL=forceSSL)
            self.logger.debug("Password Returned:"+text(self.passwordReturned))
            for property, value in vars(result).items():
                self.logger.debug(text(property) + ":" + text( value))
                if property=="iRoombaMAC":
                    if value:
                        device.updateStateOnServer('MAC', value=str(value))
                if property == "iRoombaName":
                    if value:
                        device.updateStateOnServer('Name', value=str(value))
                if property == 'iRoombaSWver':
                    if value:
                        self.logger.debug('Software Version of Roomba Found:' + text(value))
                        device.updateStateOnServer('softwareVer', value=str(value))
                if property =="blid":
                    if value != "":
                        self.logger.debug("Blid of iRoomba Found:"+text(value))
                        device.updateStateOnServer('blid', value=str(value))
                        blid = str(value)
            #self.logger.debug("Returning Result:"+text(result))
            time.sleep(3)
            self.logger.info("Checking for updated Map Info")
            result = irobotAPI_Maps(self, address=roombaIP, useCloud=useCloud, cloudLogin=cloudLogin, cloudPassword=cloudPassword, blid=blid)
            time.sleep(5)
            self.checkAllRoombas()
            return result
        except Exception as e:
            self.logger.exception("Caught Exception:"+text(e))
            return False

    def logAllRoombas(self):
        self.logger.debug(u"{0:=^130}".format(""))
        self.logger.debug(u'log All Roomba Info Menu Item Called:')
        self.logger.debug(u"{0:=^130}".format(""))
        for myroomba in self.roomba_list:
            self.logger.debug(u"{0:=^130}".format(""))
            for property, value in vars(myroomba).items():
                self.logger.debug(text(property) + ":" + text(value))


    def getRoombaInfoAction(self, pluginAction, roombaDevice):
        self.logger.debug(u"getRoombaInfoAction for %s" % roombaDevice.name)
        self.updateMasterStates()

    def connectRoomba(self,device):
        if self.debugOther:
            self.logger.debug("connectRoomba Called self.roomba_list = "+text(self.roomba_list))

        deviceroombaName = str(device.states['Name'])
        if self.debugOther:
            self.logger.debug("Device Name  = "+text(deviceroombaName))

        if any(str(roomba.address) == str(device.states['IP']) for roomba in self.roomba_list):
            if self.debugOther:
                self.logger.debug("connectRoomba Msg: iRoomba IP Already Exists in roomba_list:")
            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(device.states['IP']):
                    if myroomba.roomba_connected == False:
                        if self.debugOther:
                            self.logger.debug("Reconnecting myroomba already exists in self.roomba_list")
                        myroomba.connect()
                        time.sleep(2)
                    else:
                        if self.debugOther:
                            self.logger.debug("connectRoomba:  Already in roomba_list and already connected returning")
                        return True
        else:  ## no matching Roomba in roomba_list
            if self.debugOther:
                self.logger.debug(u'connecting Roomba Device: '+text(device.name))
            roombaIP = device.pluginProps.get('address', 0)
            softwareVersion = device.states['softwareVer']
            forceSSL = device.pluginProps.get('forceSSL',False)
            if roombaIP == 0:
                device.updateStateOnServer(key="deviceStatus", value="Communications Error")
                self.updateVar(device.states['IP'], False)
                device.updateStateOnServer(key="onOffState", value=False, uiValue="Communications Error")
                device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                self.logger.error(u"getDeviceStatus: Roomba IP address not configured.")
                return
            filename = text(roombaIP)+"-config.ini"
            # = os.path.expanduser("~")+"/"
            folderLocation = self.pluginprefDirectory #+"Documents/Indigo-iRobotRoomba/"
            file = folderLocation + filename
            if self.debugOther:
                self.logger.debug(u'Using config file: ' + text(file))
            if os.path.isfile(file):
                myroomba = Roomba( self, address=roombaIP, file=filename, softwareversion=softwareVersion, forceSSL=forceSSL, roombaName=deviceroombaName)
                myroomba.set_options(raw=False, indent=0, pretty_print=False)
                myroomba.connect()

                if myroomba not in self.roomba_list:  ## not convinced this will work correctly; is checked above anyhow...
                    self.logger.debug("Adding myroomba to self.roomba_list..")
                    self.roomba_list.append(myroomba)
                    self.logger.debug("self.roomba_list:"+text(self.roomba_list))
                return True
            else:
                self.logger.error(u'Config file for device does not exist - check Device settings')
                return False
        #self.logger.error(text(self.myroomba.master_state))

    def display_time(self, seconds, granularity=2):
        result = []
        intervals = (
            ('weeks', 604800),  # 60 * 60 * 24 * 7
            ('days', 86400),  # 60 * 60 * 24
            ('hours', 3600),  # 60 * 60
            ('minutes', 60),
            ('seconds', 1),
        )
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append("%s %s" % (value, name))
        return ', '.join(result[:granularity])

    def check_onmessage(self, masterState,current_state, roombaipaddress):
        if self.debugOther:
            self.logger.debug(u"check on_message called by on_message iroomba function: For Device:"+text(roombaipaddress))
            #self.logger.debug(text(masterState))
            #self.logger.debug(text(roombaipaddress))

        # when message received, master_state already updated.
        # Just recall save for all states - some unchanged.. but unlikely much benefit of multiple if/choices

        for dev in indigo.devices.iter("self"):
            for myroomba in self.roomba_list:
                if str(roombaipaddress) == str(dev.states['IP']):
                    self.logger.debug(u"Found Device: "+text(roombaipaddress)+' Matching device IP'+text(dev.states['IP']))
                    if (dev.deviceTypeId == "roombaDevice") and myroomba.master_state != None:
                        self.saveMasterStateDevice(masterState, dev, current_state, fromonmessage=True)

        return

    def saveMasterStateDevice(self, masterState, device, currentstate, fromonmessage=False):
        if self.debugOther:
            self.logger.debug(u'saveMasterStateDevice called.  FromonMessage:'+text(fromonmessage)+" and currentstate:"+text(currentstate))

        if masterState != None:
            if self.debugOther:
              #  if fromonmessage==False o:
                self.logger.debug(u'Writing Master State Device:' +text(device.id) +":"+text(json.dumps(masterState)))
              #  else:
                #self.logger.debug(u'Writing On Message Data only: From On_Message')
            state =""
            cycle=""
            statement = ""
            errorCode ='0'
            notReady = '0'
            rechrgTm = 0
            mssnStrtTm = 0
            rechrgM = 0
            batteryPercent = ""
            phase = ""
            if 'state' in masterState:
                if 'reported' in masterState['state']:
                    if 'name' in masterState['state']['reported']:
                        #self.logger.debug(u'MasterState Name :'+ masterState['state']['reported']['name'])
                        device.updateStateOnServer('Name', value=str(masterState['state']['reported']['name']))

                    if 'pose' in masterState['state']['reported']:
                        if 'point' in masterState['state']['reported']['pose']:
                            if 'x' in masterState['state']['reported']['pose']['point']:
                                device.updateStateOnServer('X', value=str(masterState['state']['reported']['pose']['point']['x']))
                            if 'y' in masterState['state']['reported']['pose']['point']:
                                device.updateStateOnServer('Y', value=str(masterState['state']['reported']['pose']['point']['y']))

                    if 'batPct' in masterState['state']['reported']:
                        batteryPercent =  str(masterState['state']['reported']['batPct'])
                        device.updateStateOnServer('BatPct', value=str(masterState['state']['reported']['batPct']))

                    if 'name' in masterState['state']['reported']:
                        #self.logger.error(u'MasterState state/reported :' + text(masterState['state']['reported']) )
                        if device.states['Name'] != str(masterState['state']['reported']['name']):
                            device.updateStateOnServer('Name', value=str(masterState['state']['reported']['name']))
                            self.logger.error(u"Updated Name")

                    if 'cleanMissionStatus' in masterState['state']['reported']:
                        if 'cycle' in masterState['state']['reported']['cleanMissionStatus']:
                            #self.logger.debug(u'MasterState Bat cycle :'+ masterState['state']['reported']['cleanMissionStatus']['cycle'])
                            cycle = str(masterState['state']['reported']['cleanMissionStatus']['cycle'])
                            device.updateStateOnServer('Cycle',value=str(masterState['state']['reported']['cleanMissionStatus']['cycle']))

                        if 'phase' in masterState['state']['reported']['cleanMissionStatus']:
                            phase = str(masterState['state']['reported']['cleanMissionStatus']['phase'])
                            device.updateStateOnServer('Phase', value=str(masterState['state']['reported']['cleanMissionStatus']['phase']))
                            state = str("Roomba Ok - ") + str(masterState['state']['reported']['cleanMissionStatus']['phase'])


                        if 'notReady' in masterState['state']['reported']['cleanMissionStatus']:
                            device.updateStateOnServer('NotReady', value=str( masterState['state']['reported']['cleanMissionStatus']['notReady']))
                            notReady = str(masterState['state']['reported']['cleanMissionStatus']['notReady'])
                            try:
                                notReadyText = self.notReadyStrings[notReady]
                            except:
                                notReadyText = "Undocumented Not Ready Value (%s)" % notReady
                            device.updateStateOnServer('NotReadyText', value=notReadyText)
                            if notReady != "0":
                                statement = "Not Ready: "+str(notReadyText)

                        if 'error' in masterState['state']['reported']['cleanMissionStatus']:
                            device.updateStateOnServer('ErrorCode', value=str(masterState['state']['reported']['cleanMissionStatus']['error']))
                            errorCode = str(masterState['state']['reported']['cleanMissionStatus']['error'])
                            try:
                                errorText = self.errorStrings[errorCode]
                            except:
                                errorText = "Undocumented Error Code (%s)" % errorCode
                            device.updateStateOnServer('ErrorText', value=errorText)
                            if errorCode !="0":
                                statement = "Error: "+str(errorText)

                        if 'sqft' in masterState['state']['reported']['cleanMissionStatus']:
                            device.updateStateOnServer('SqFt', value=str(
                                masterState['state']['reported']['cleanMissionStatus']['sqft']))

                        if 'rechrgM' in masterState['state']['reported']['cleanMissionStatus']:
                            rechrgM = masterState['state']['reported']['cleanMissionStatus']['rechrgM']
                            device.updateStateOnServer('RechargeM', value=int(masterState['state']['reported']['cleanMissionStatus']['rechrgM']))
                        if 'rechrgTm' in masterState['state']['reported']['cleanMissionStatus']:
                            rechrgTm = masterState['state']['reported']['cleanMissionStatus']['rechrgTm']
                        if 'mssnStrtTm' in masterState['state']['reported']['cleanMissionStatus']:
                            mssnStrtTm = masterState['state']['reported']['cleanMissionStatus']['mssnStrtTm']

                        if mssnStrtTm>0 and cycle !="none":
                            timestampMission = str(datetime.datetime.fromtimestamp(mssnStrtTm).strftime(str(self.datetimeFormat)))
                            device.updateStateOnServer('MissionStarted', value=str(timestampMission))
                            device.updateStateOnServer('lastMission', value=str(timestampMission))
                            startMission = datetime.datetime.fromtimestamp(mssnStrtTm)
                            nowTime = datetime.datetime.fromtimestamp(time.time())
                            if nowTime > startMission:
                                lengthMis = nowTime-startMission
                                totalmins = int(round(lengthMis.total_seconds()/60))
                                device.updateStateOnServer('MissionDuration', value=int(totalmins))
                                if phase == "run":
                                    statement = "Running, Mission "+str(totalmins)+" mins, Bat "+str(batteryPercent)+" %"
                                elif phase == "dockend":
                                    statement = "Docking, Mission completed " + str(totalmins) + " minutes"
                                elif phase == "cancelled":
                                    statement = "Docking, Mission cancelled " + str(totalmins) + " minutes"
                                elif phase == "hmMidMsn":
                                    statement = "Docking, Mid mission " + str(totalmins) + " mins, Bat "+str(batteryPercent)+" %"
                                elif phase == "hmUsrDock":
                                    statement = "User docking, Battery at "+str(batteryPercent)+"%"
                            ## Calculate minutes
                        elif cycle=="none":
                            device.updateStateOnServer('MissionStarted', value=str(""))
                            device.updateStateOnServer('MissionDuration', value="")
                        elif mssnStrtTm==0:
                            device.updateStateOnServer('MissionStarted', value="" )
                            device.updateStateOnServer('MissionDuration', value="" )
                        if rechrgTm>0:
                            ## Time different
                            timedifference = rechrgTm - time.time()
                            if timedifference>0:
                                minutesremaining = timedifference/60
                                device.updateStateOnServer('RechargeM', value=int(minutesremaining))
                            rechargeFinish = str(datetime.datetime.fromtimestamp(rechrgTm).strftime(str(self.datetimeFormat)))
                            device.updateStateOnServer('RechargeFinish', value=str(rechargeFinish))
                            statement = "Recharging, due to restart in "+str(int(minutesremaining))+" mins"
                        else:
                            device.updateStateOnServer('RechargeM', value=int(0))
                            device.updateStateOnServer('RechargeFinish', value=str(""))

                    if 'bin' in masterState['state']['reported']:
                        if 'full' in masterState['state']['reported']['bin']:
                            #self.logger.debug(u'MasterState Bin Full :'+ text(masterState['state']['reported']['bin']['full']))
                            if masterState['state']['reported']['bin']['full'] == True:
                                device.updateStateOnServer('BinFull', value=True)
                            if masterState['state']['reported']['bin']['full'] == False:
                                device.updateStateOnServer('BinFull', value=False)
                    if 'bbrun' in masterState['state']['reported']:
                        Hourtime = 0
                        minutetime = 0
                        if 'hr' in masterState['state']['reported']['bbrun']:
                            Hourtime = int(masterState['state']['reported']['bbrun']['hr'])
                        if 'min' in masterState['state']['reported']['bbrun']:
                            minutetime = int(masterState['state']['reported']['bbrun']['min'])
                        if minutetime !=0 and Hourtime !=0:
                            totalseconds = (Hourtime*60*60)+(minutetime*60)
                            lifetimestring = self.display_time(totalseconds,4)
                            device.updateStateOnServer('LifetimeRuntime', value=lifetimestring)
                        if 'sqft' in masterState['state']['reported']['bbrun']:
                            sqfttotal = int(masterState['state']['reported']['bbrun']['sqft'])*100
                            if sqfttotal !=None and sqfttotal >0:
                                device.updateStateOnServer('LifetimeAreaCleaned_Sqft', value=str('{:,.0f}'.format(sqfttotal) ))
                                msqtotal = float(sqfttotal/10.76391041671)
                                device.updateStateOnServer('LifetimeAreaCleaned_m2', value=str('{:,.0f}'.format(msqtotal) ))
                    if 'bbmssn' in masterState['state']['reported']:
                        if 'nMssn' in masterState['state']['reported']['bbmssn']:
                            Lifetimecleaningjobs = int(masterState['state']['reported']['bbmssn']['nMssn'])
                            if Lifetimecleaningjobs !=None and Lifetimecleaningjobs >0:
                                device.updateStateOnServer('LifetimeCleaningJobs', value=str('{:,}'.format(Lifetimecleaningjobs) ))

                    if phase == "charge":
                        if statement == "":
                            if batteryPercent !="100":
                                statement = "Charging, Battery at "+str(batteryPercent)+"%"
                            elif batteryPercent == "100":
                                statement = "Fully charged. Ready to vacuum."

                    if currentstate != "":
                        state = str(currentstate)

                    if str(errorCode) == str('0') and str(notReady) == str('0'):
                        self.logger.debug("Errorcode and notReady:"+str(notReady)  )
                        device.updateStateOnServer(key="deviceStatus", value=text(state))
                        device.updateStateOnServer(key="errornotReady_Statement", value="")
                        self.updateVar(device.states['IP'], True)
                        device.updateStateOnServer(key="onOffState", value=True, uiValue=text(state))
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                    elif str(errorCode) != str('0'):
                        self.logger.debug("Errorcode not equal to 0:"+str(errorCode))
                        device.updateStateOnServer(key="deviceStatus", value=errorText)
                        device.updateStateOnServer(key="errornotReady_Statement",value=self.geterrorNotreadySentence(device, errorCode=errorCode, notReadyCode=notReady) )
                        self.updateVar(device.states['IP'], False)
                        device.updateStateOnServer(key="onOffState", value=False, uiValue=text(errorText))
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                    elif str(notReady) != str('0'):
                        self.logger.debug("notReady not equal to zero:"+str(notReady))
                        device.updateStateOnServer(key="deviceStatus", value=notReadyText)
                        device.updateStateOnServer(key="errornotReady_Statement", value=self.geterrorNotreadySentence(device, errorCode=errorCode, notReadyCode=notReady) )
                        self.updateVar(device.states['IP'], False)
                        device.updateStateOnServer(key="onOffState", value=False, uiValue=text(notReadyText))
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

                    if statement !="":
                        device.updateStateOnServer('currentState_Statement', value=text(statement))
                    else:
                        device.updateStateOnServer('currentState_Statement', value=text(state))
        else:
            self.logger.debug("MasterState is None.")
        return
          #  self.logger.debug(text(masterState))100

      #  masterjson = json.dumps(masterState)

      #  with open(file, 'w') as cfgfile:
      #      json.dump(masterjson, cfgfile, ensure_ascii=False)
      #      self.logger.debug(u'Saved Master State')
      #      cfgfile.close()

    def geterrorNotreadySentence(self,device, errorCode="0", notReadyCode="0"):
        try:
            self.logger.debug("geterrorNotreadySentence (phew) run, with errorCode:"+text(errorCode)+" and notReadyCode:"+text(notReadyCode))

            if errorCode =="0" and notReadyCode =="0":
                self.logger.debug("No error, error")
                return ""

            iroombaName = device.states['Name']
            if errorCode != "0":
                self.logger.debug("Checking for notification_error_"+str(errorCode) )
                keytouse = str("notification_error_"+str(errorCode))
                if keytouse in self.newiroombaData:
                    valuetouse = str(self.newiroombaData[keytouse])
                    valuetousereplace = valuetouse.replace('%s', str(iroombaName))
                    self.logger.debug("error_"+str(errorCode)+" exists and is "+text(valuetouse) )
                    return valuetousereplace

            if notReadyCode != "0":
                self.logger.debug("Checking for notification_start_refuse_"+str(notReadyCode) )
                keytouse = str("notification_start_refuse_"+str(notReadyCode))
                if keytouse in self.newiroombaData:
                    valuetouse = str(self.newiroombaData[keytouse])
                    valuetousereplace = valuetouse.replace('%s', str(iroombaName))
                    self.logger.debug("NotreadyCode "+str(notReadyCode)+" exists and is "+text(valuetouse) )
                    return valuetousereplace

            return ""

        except:
            self.logger.debug("Exception in get sentence")
            return ""

    def disconnectRoomba(self,device):
        self.logger.debug(u'disconnecting Roomba Device: '+text(device.name))
        for myroomba in self.roomba_list:
            if str(myroomba.address) == str(device.states['IP']):
                self.logger.debug("disconnectRoomba Matching iroomba found")
                if myroomba.master_state != None:
                    self.saveMasterStateDevice(myroomba.master_state, device, "", fromonmessage=False)
                    self.logger.debug(text(myroomba.master_state))
                myroomba.disconnect()
                self.roomba_list.remove(myroomba)
                self.logger.debug("Self.Roomba_list:"+text(self.roomba_list))
        #self.myroomba = None

    def getRoombaInfo(self, device):
        if self.debugTrue:
            self.logger.debug(u"getRoombaInfo for %s" % device.name)
        #self.logger.debug(u'')
        #
        # if above true - connect to one device only (1st one found) and do so with continuous connection - constant updates...

        if self.connectRoomba(device):
            self.logger.debug("Reconnecting device/checked")
        return

    def updateMasterStates(self):
        if self.debugTrue:
            self.logger.debug(u'updateMasterStates called.')
        for dev in indigo.devices.iter("self"):
            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(dev.states['IP']):
                    if (dev.deviceTypeId == "roombaDevice") and myroomba.master_state != None:
                        self.saveMasterStateDevice(myroomba.master_state, dev, myroomba.current_state, fromonmessage=False)
        return

    def reconnectRoomba(self):
        self.logger.debug("Restablish connection for Roomba Run - reconnectRoomba")
        for dev in indigo.devices.iter("self"):
            for myroomba in self.roomba_list:
                if myroomba != None:
                    self.disconnectRoomba(dev)
            time.sleep(5)
            self.connectRoomba(dev)
        return

    def getRoombaStatusAction(self, pluginAction, roombaDevice):
        self.logger.debug(u"getRoombaStatusAction for %s" % roombaDevice.name)
        #self.getRoombaInfo(roombaDevice)

    def getRoombaStatus(self, device):
        self.logger.debug(u"getRoombaStatus for %s" % device.name)

        self.triggerCheck(device)

    def checkallStatesMenu(self):
        if self.debugTrue:
            self.logger.debug(u'checkallStatesMenu called. ')
        for dev in indigo.devices.iter("self"):
            if (dev.deviceTypeId == "roombaDevice"):
                self.getRoombaInfo(dev)
                time.sleep(1)

        self.updateMasterStates()

    def checkanyConnected(self):
        if self.debugOther:
            self.logger.debug(u'checkanyConnected called. ')
        anyConnected = False
        for myroomba in self.roomba_list:
            if myroomba.roomba_connected == True:
                anyConnected = True
                if self.debugOther:
                    self.logger.debug(u'Found connected myroomba.  Returning True ')

        if anyConnected == False:
            self.KILLcount = self.KILLcount +1
            self.logger.debug(u"No connected iRoombas found now for "+text(self.KILLcount)+" times...")
        else:
            self.KILLcount = 0

        if self.KILLcount > 4:
            self.logger.debug(u"No connected iRoomabs found for 5 checks... restarting Plugin to reset MQTT connection")
            self.logger.debug(u"Occasionally after days of continuous connection, error somewhere requiring restart")
            self.restartPlugin()

        return anyConnected

    def checkAllRoombas(self):
        if self.debugOther:
            self.logger.debug(u'checkALlRoombas called. ')
            #self.logger.debug(u'self.connected equals:'+text(self.connected)+"& self.continuous equals:"+text(self.continuous))
        for dev in indigo.devices.iter("self"):
            if (dev.deviceTypeId == "roombaDevice"):
                if dev.enabled:
                    if self.debugOther:
                        self.logger.debug(u'getRoomba Info Running..')
                    self.getRoombaInfo(dev)
                    time.sleep(1)
                #self.getRoombaStatus(dev)
                #self.getRoombaTime(dev)

    def toggleRoombaAction(self, pluginAction, roombaDevice):
        self.logger.debug(u'toggle Roomba Action Call')
        Cycle = roombaDevice.states['Cycle']

        self.logger.debug(u'Current State is:' + text(Cycle))

        if Cycle =='clean':
            self.logger.debug(u'Roomba Cycle clean changing to docking...')
            self.RoombaAction(pluginAction, roombaDevice, 'pause')
            self.sleep(1)
            self.RoombaAction(pluginAction, roombaDevice, 'dock')
        if Cycle == 'charge':
            self.logger.debug(u'Roomba changing to running...')
            self.RoombaAction(pluginAction, roombaDevice, 'start')
        if Cycle == 'run':
            self.logger.debug(u'Roomba changing to docking...')
            self.RoombaAction(pluginAction, roombaDevice, 'pause')
            self.sleep(1)
            self.RoombaAction(pluginAction, roombaDevice, 'dock')
        if Cycle == 'pause':
            self.logger.debug(u'Roomba changing to running...')
            self.RoombaAction(pluginAction, roombaDevice, 'resume')
        if Cycle == 'hmMidMsn':
            self.logger.debug(u'Roomba changing to running...')
            self.RoombaAction(pluginAction, roombaDevice, 'start')
        if Cycle == 'none':
            self.logger.debug(u'Roomba changing to running...')
            self.RoombaAction(pluginAction, roombaDevice, 'start')


    def startRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'start')

    def stopRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'stop')

    def pauseRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'pause')

    def resumeRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'resume')

    def dockRoombaAction(self, pluginAction, roombaDevice):
        ## Check to see if running first.
        Cycle = roombaDevice.states['Cycle']
        Phase = roombaDevice.states['Phase']
        if Phase is None or Cycle is None:
            return
        self.logger.debug(u'Current State is:' + text(Cycle) + " and current Phase:" + text(Phase))
        if Phase == "charge" and Cycle =="none":
            ## charging no mission running skip
            self.logger.info("iRoomba is not active.  Dock action not run.")
            return

        self.RoombaAction(pluginAction, roombaDevice, 'pause')
        self.sleep(1)
        self.RoombaAction(pluginAction, roombaDevice, 'dock')

    def evacRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'evac')

    def getLastCommand(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"getLastCommand called: "+text(deviceId))
        self.logger.debug(u"getLastCommand valuesDict: " + text(valuesDict))
        self.logger.debug(u"getLastCommand typeId: " + text(typeId))
        try:
            roombaDeviceID = int(valuesDict.get("roombatoUse",0))
            if roombaDeviceID == 0:
                self.logger.info("Please select a roomba to use")
                return
            roombaDevice = indigo.devices[roombaDeviceID]
            iroombaName = str(roombaDevice.states['Name'])
            iroombaIP = str(roombaDevice.states['IP'])
            self.logger.debug("Roomba Name:" + text(iroombaName))
            self.logger.debug("Roomba IP:" + text(iroombaIP))
            lastcommand = ""
            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(iroombaIP):
                    if "state" in myroomba.master_state:
                        if "reported" in myroomba.master_state["state"]:
                            if "lastCommand" in myroomba.master_state["state"]["reported"]:
                                self.logger.debug(json.dumps(myroomba.master_state["state"]["reported"]["lastCommand"]))
                                lastcommand = myroomba.master_state["state"]["reported"]["lastCommand"]
                                #lastcommand ='thisisasteing'
                                self.logger.info("Saving this Command:")
                                self.logger.info(text(json.dumps(lastcommand)))
                                valuesDict['commandToSend']=json.dumps(lastcommand)
                                self.logger.debug(text(valuesDict))
                                return valuesDict
                            else:
                                self.logger.info("No Last Command found please try again")
                                return

        except Exception as ex:
            self.logger.exception("Exception ")
    def sendSpecificFavouriteCommand(self, pluginAction, roombaDevice):
        try:
            self.logger.debug("send Specific Favourite Clean called to run")
            self.logger.debug("pluginAction "+text(pluginAction))
            self.logger.debug("roombaDevice IP:" + text(roombaDevice.states['IP']))

            blid = str(roombaDevice.states['blid'])
            ipaddress = str(roombaDevice.states['IP'])
            action = {}
            regions = []
            actionRooms = []
            commandtosend = ""

            if blid is None:
                self.logger.info("Please update iRobot to include Blid data.  Run Get Password via Cloud to update.")
                return
            if blid == "":
                self.logger.info("Please update iRobot to include Blid data.  Run Get Password via Cloud to update.")
                return
            if ipaddress is None:
                self.logger.info("Please update iRobot to include IP Address data.  Run Get Password via Cloud to update.")
                return
            if ipaddress == "":
                self.logger.info("Please update iRobot to include Ip Address data.  Run Get Password via Cloud to update.")
                return


            action['ordered']=1
           # action['regions']=[]

            actionID = pluginAction.props.get("actionID")
            self.logger.debug(text(actionID))
            if len(actionID)<=0:
                self.logger.info("Please select some options in Action Group Config.  No Favourites selected.")
                return
            command_to_run = None
            if str(ipaddress) in self.allFavouritesData:
                for items in self.allFavouritesData[str(ipaddress)]:
                    if str(actionID).lower() == str(items['favorite_id']).lower():
                        self.logger.debug(f"Found Correct Favourite:\n {items['commanddefs'][0]}")
                        favourite_id = str(items['favorite_id']).lower()
                        command_to_run = items["commanddefs"][0]

            self.logger.debug(f"Command to Run: {command_to_run}")
            if command_to_run == None:
                self.logger.error("Command found is empty.  Ending")

            if 'pmap_id' in command_to_run:
                action['pmap_id']= command_to_run['pmap_id']
            if 'user_pmapv_id' in command_to_run:
                action['user_pmapv_id']= command_to_run['user_pmapv_id']
            if 'regions' in command_to_run:
                action['regions']= command_to_run['regions']
            else:
                action['regions'] =[]

            action['favorite_id'] = favourite_id

           # if 'select_all' in command_to_run:
            #    action['select_all'] = command_to_run['select_all']
            if 'command' in command_to_run:
                action['command'] = command_to_run['command']
            else:
                action['command'] = "start"
            if 'params' in command_to_run:
                action['params'] = command_to_run['params']
            if 'ordered' in command_to_run:
                action['ordered'] = command_to_run['ordered']

            #action['robot_id']= blid

            self.logger.debug(json.dumps(action))

            try:
                iroombaName = str(roombaDevice.states['Name'])
                iroombaIP = str(roombaDevice.states['IP'])
                self.logger.debug("Roomba Name:"+text(iroombaName))
                self.logger.debug("Roomba IP:" + text(iroombaIP))
                #self.logger.debug("Connected Roomba Name:"+text(self.connectedtoName))

                for myroomba in self.roomba_list:
                    if str(myroomba.address) == str(iroombaIP):
                        if myroomba.roomba_connected == False:
                            self.logger.debug(u"Not connected to iRoomba:"+text(iroombaName)+" & IP:"+text(iroombaIP)+u" -- Should be --- Attempting to reconnect.")
                            connected = False
                            connected = self.connectRoomba(roombaDevice)
                            time.sleep(5)
                            # Add a connection check - the main library has added a base exception which might be useful to also use.
                            if connected == False:
                                self.logger.info(u'Failed Connected to Roomba within 5 seconds, waiting another 5.')
                                time.sleep(5)
                                if connected == False:
                                    self.logger.info(u'Failed Connected to Roomba within 5 seconds.  Ending attempt.')
                                    return
                            myroomba.send_command_special(json.dumps(action))
                        else:
                            self.logger.debug("Sending Command to myroomba:"+text(myroomba.roombaName)+" and action:"+str(json.dumps(action)))
                            myroomba.send_command_special(json.dumps(action))

                return

            except Exception as e:
                self.logger.exception(u'Caught Error within RoombaAction:'+text(e))
        except:
            self.logger.exception("Exception Sending Favourite Command")

    def sendSpecificRoomCommand(self, pluginAction, roombaDevice):
        self.logger.debug("send Specific Room Clean called to run")
        self.logger.debug("pluginAction "+text(pluginAction))
        self.logger.debug("roombaDevice IP:" + text(roombaDevice.states['IP']))

        blid = str(roombaDevice.states['blid'])
        ipaddress = str(roombaDevice.states['IP'])
        action = {}
        regions = []
        actionRooms = []
        commandtosend = ""

        if blid is None:
            self.logger.info("Please update iRobot to include Blid data.  Run Get Password via Cloud to update.")
            return
        if blid == "":
            self.logger.info("Please update iRobot to include Blid data.  Run Get Password via Cloud to update.")
            return

        if ipaddress is None:
            self.logger.info("Please update iRobot to include IP Address data.  Run Get Password via Cloud to update.")
            return
        if ipaddress == "":
            self.logger.info("Please update iRobot to include Ip Address data.  Run Get Password via Cloud to update.")
            return

        action['command']='start'
        action['ordered']=1
        action['select_all']=False
        action['regions']=[]

        actionRooms = pluginAction.props.get("actionRooms")
        self.logger.debug(text(actionRooms))

        if len(actionRooms)<=0:
            self.logger.info("Please select some options in Action Group Config.  No Rooms / Areas selected.")
            return

        for zone in actionRooms:
            a = {}
            if str(zone)[-1]=="Z":  ## add Z for manual ids and then remove before parsed change the type appropriately
                a['region_id']=str(zone)[:-1]  ##remove the Z
                a['type']= "zid"               ##mark as user zone
                action['regions'].append(a)
            else:
                a['region_id'] = str(zone)
                a['type'] = "rid"               ## Normal Zone
                action['regions'].append(a)

        ## remove initiator and current time - add these back in iroomba
        if "initiator" in action:
            action.pop("initiator", None)
        if "time" in action:
            action.pop("time", None)

        if 'pmap_id' in self.allMappingData[ str(ipaddress) ][0]:
            action['pmap_id']= self.allMappingData[str(ipaddress)][0]['pmap_id']
        else:
            self.logger.debug( self.allMappingData[ ipaddress])

        if 'user_pmapv_id' in self.allMappingData[ str(ipaddress) ][0]:
            action['user_pmapv_id']= self.allMappingData[str(ipaddress)][0]['user_pmapv_id']
        else:
            self.logger.debug( self.allMappingData[ ipaddress])

        action['robot_id']= blid

        self.logger.debug(json.dumps(action))

        try:
            iroombaName = str(roombaDevice.states['Name'])
            iroombaIP = str(roombaDevice.states['IP'])
            self.logger.debug("Roomba Name:"+text(iroombaName))
            self.logger.debug("Roomba IP:" + text(iroombaIP))
            #self.logger.debug("Connected Roomba Name:"+text(self.connectedtoName))

            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(iroombaIP):
                    if myroomba.roomba_connected == False:
                        self.logger.debug(u"Not connected to iRoomba:"+text(iroombaName)+" & IP:"+text(iroombaIP)+u" -- Should be --- Attempting to reconnect.")
                        connected = False
                        connected = self.connectRoomba(roombaDevice)
                        time.sleep(5)
                        # Add a connection check - the main library has added a base exception which might be useful to also use.
                        if connected == False:
                            self.logger.info(u'Failed Connected to Roomba within 5 seconds, waiting another 5.')
                            time.sleep(5)
                            if connected == False:
                                self.logger.info(u'Failed Connected to Roomba within 5 seconds.  Ending attempt.')
                                return
                        myroomba.send_command_special(json.dumps(action))
                    else:
                        self.logger.debug("Sending Command to myroomba:"+text(myroomba.roombaName)+" and action:"+str(json.dumps(action)))
                        myroomba.send_command_special(json.dumps(action))

            return

        except Exception as e:
            self.logger.exception(u'Caught Error within RoombaAction:'+text(e))

    def lastCommandRoombaAction(self, pluginAction, roombaDevice):
        self.logger.debug("lastcommandRoombaAction")
        self.logger.debug("pluginAction "+text(pluginAction))

        action = []
        commandtosend = ""
        if "commandToSend" in pluginAction.props:
            commandtosend = pluginAction.props.get("commandToSend")
            self.logger.debug(text(commandtosend))

        action = json.loads(commandtosend)

        ## remove initiator and current time - add these back in iroomba
        if "initiator" in action:
            action.pop("initiator", None)
        if "time" in action:
            action.pop("time", None)

        self.logger.debug(action)

        try:
            iroombaName = str(roombaDevice.states['Name'])
            iroombaIP = str(roombaDevice.states['IP'])
            self.logger.debug("Roomba Name:"+text(iroombaName))
            self.logger.debug("Roomba IP:" + text(iroombaIP))
            #self.logger.debug("Connected Roomba Name:"+text(self.connectedtoName))

            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(iroombaIP):
                    if myroomba.roomba_connected == False:
                        self.logger.debug(u"Not connected to iRoomba:"+text(iroombaName)+" & IP:"+text(iroombaIP)+u" -- Should be --- Attempting to reconnect.")
                        connected = False
                        connected = self.connectRoomba(roombaDevice)
                        time.sleep(5)
                        # Add a connection check - the main library has added a base exception which might be useful to also use.
                        if connected == False:
                            self.logger.info(u'Failed Connected to Roomba within 5 seconds, waiting another 5.')
                            time.sleep(5)
                            if connected == False:
                                self.logger.info(u'Failed Connected to Roomba within 5 seconds.  Ending attempt.')
                                return
                        myroomba.send_command_special(json.dumps(action))
                    else:
                        self.logger.debug("Sending Command to myroomba:"+text(myroomba.roombaName)+" and action:"+str(json.dumps(action)))
                        myroomba.send_command_special(json.dumps(action))

            return

        except Exception as e:
            self.logger.exception(u'Caught Error within RoombaAction:'+text(e))

    def RoombaAction(self, pluginAction, roombaDevice, action):
        self.logger.debug(u"startRoombaAction for "+text(roombaDevice.name)+": Action : "+str(action))
        # Add a try except loop to catch nicely any errors.
        try:
            iroombaName = str(roombaDevice.states['Name'])
            iroombaIP = str(roombaDevice.states['IP'])
            self.logger.debug("Roomba Name:"+text(iroombaName))
            self.logger.debug("Roomba IP:" + text(iroombaIP))
            #self.logger.debug("Connected Roomba Name:"+text(self.connectedtoName))

            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(iroombaIP):
                    if myroomba.roomba_connected == False:
                        self.logger.debug(u"Not connected to iRoomba:"+text(iroombaName)+" & IP:"+text(iroombaIP)+u" -- Should be --- Attempting to reconnect.")
                        connected = False
                        connected = self.connectRoomba(roombaDevice)
                        time.sleep(5)
                        # Add a connection check - the main library has added a base exception which might be useful to also use.
                        if connected == False:
                            self.logger.info(u'Failed Connected to Roomba within 5 seconds, waiting another 5.')
                            time.sleep(5)
                            if connected == False:
                                self.logger.info(u'Failed Connected to Roomba within 5 seconds.  Ending attempt.')
                                return
                        myroomba.send_command(str(action))
                    else:
                        self.logger.debug("Sending Command to myroomba:"+text(myroomba.roombaName)+" and action:"+str(action))
                        myroomba.send_command(str(action))
                    self.logger.info(f"iRobot {iroombaName} sent command: {action}")

            return


        except Exception as e:
            self.logger.debug(u'Caught Error within RoombaAction:'+text(e))