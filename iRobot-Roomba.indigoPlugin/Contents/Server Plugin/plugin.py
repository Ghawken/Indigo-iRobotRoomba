#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

# UPDATE FOR ROOMBA - FOR USE WITH MQTT
# BASED ON ROOMBA980-PYTHON (ROOMBA.PY) FILE
# AND EARLIER INDIGO PLUGIN BY FLYING DIVER

#VERSION 0.0.2
#PROOF OF CONCEPT.


import sys
import os.path
import time
import requests
import json
import logging
#import OpenSSL
#rom base64 import b64encode
from roomba import Roomba
from roomba import password
from roomba import irobotAPI_Maps
#import paho.mqtt.client as mqtt
import threading
import datetime

import locale

#from requests.auth import HTTPBasicAuth
#from requests.utils import quote

#@from ghpu import GitHubPluginUpdater

kCurDevVersCount = 1        # current version of plugin devices

################################################################################
class Plugin(indigo.PluginBase):

    ########################################
    # Main Plugin methods
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        MAChome     = os.path.expanduser("~")+"/"
        self.mainfolderLocation = MAChome+"Documents/Indigo-iRobotRoomba/"

        #self.mappingfile = self.mainfolderLocation + str(address)+"-mapping-data.json"

        self.logger.info(u"")
        self.logger.info(u"{0:=^130}".format(" Initializing New Plugin Session "))
        self.logger.info(u"{0:<30} {1}".format("Plugin name:", pluginDisplayName))
        self.logger.info(u"{0:<30} {1}".format("Plugin version:", pluginVersion))
        self.logger.info(u"{0:<30} {1}".format("Plugin ID:", pluginId))
        self.logger.info(u"{0:<30} {1}".format("Indigo version:", indigo.server.version))
        self.logger.info(u"{0:<30} {1}".format("Python version:", sys.version.replace('\n', '')))
        self.logger.info(u"{0:<30} {1}".format("Python Directory:", sys.prefix.replace('\n', '')))
        #self.logger.info(u"{0:<30} {1}".format("Major Problem equals: ", MajorProblem))
        self.logger.info(u"{0:=^130}".format(""))

        self.allMappingData = {}

        try:
            self.logLevel = int(self.pluginPrefs[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))
        self.debugTrue = self.pluginPrefs.get('debugTrue', '')
        self.debugOther = self.pluginPrefs.get('debugOther', True)
        self.newiroombaData = {}

        ## Load json database of errors
        try:
            with open('errormsg.json') as json_file:
                self.iroombaData = json.load(json_file)

            self.logger.debug("Reading iRoomba Strings as JSON Data From File")
            self.iroombaData = self.iroombaData['resources']['string']
          #  for strings in self.iroombaData:
               # self.logger.debug( unicode(strings) )

            self.newiroombaData = { d['_name'] : d['__text']  for d in self.iroombaData}
            self.iroombaData = None

            self.logger.debug("Done reading new json Data file")
        except:
            self.logger.debug("Exception in Json database")
            pass

        #self.logger.debug(json.dumps(self.iroombaData, sort_keys=True, indent=4))
        #self.logger.error(self.iroombaData['resources']['abc_capital_on'])


    def pluginStore(self):
        self.logger.info(u'Opening Plugin Store.')
        iurl = 'http://www.indigodomo.com/pluginstore/132/'
        self.browserOpen(iurl)

    def startup(self):
        self.logger.info(u"Starting Roomba")
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
            "54": "Blades stuck",
            "55": "Left blades stuck",
            "56":"Right blades stuck",
            "57":"Cutting deck stuck",
            "58":"Navigation problem",
            "59":"Tilt detected",
            "53": "Software update required",
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

        except self.stopThread:
            pass

    def deviceStartComm(self, device):
        self.logger.debug(u"deviceStartComm called for " + device.name)
        #if self.debugOther:
         #   self.logger.debug(unicode(device))

        device.stateListOrDisplayStateIdChanged()   # update  from device.xml info if changed
        device.updateStateOnServer(key="IP",value=str(device.pluginProps['address']))

        if device.states['IP'] != "":
            self.updateVar(device.states['IP'], True)

        #device.type = indigo.kDevicerelay
        # readd this later
        #device.subType = indigo.kRelayDeviceSubType.Switch

        #device.replaceOnServer()
        #self.logger.error(unicode(device))

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
        MAChome     = os.path.expanduser("~")+"/"
        folderLocation = MAChome+"Documents/Indigo-iRobotRoomba/"
        roombaIP = str(device.states['IP'])
        filename =  str(roombaIP)+"-mapping-data.json"
        file = folderLocation + filename

        if self.checkMapFile(device, file)== False:
            self.logger.debug(u'Mapping Data File Does Not Exist.')
            self.logger.info("No Cloud Mapping Data found for this device.  Please setup in Device Config if needed.")
        else:
            self.logger.debug(u'Mapping Data File Exists - using it')
            with open(file) as data_file:
                self.allMappingData[roombaIP] = json.load(data_file)

        self.logger.debug(unicode(self.allMappingData))

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
                            self.logger.debug(unicode(regions))
                            myArray.append( (regions['id'],regions['name'] ))
                    if 'zones' in items['active_pmapv_details']:
                        for zones in items['active_pmapv_details']['zones']:
                            self.logger.debug(unicode(zones))
                            myArray.append((zones['id']+str("Z"), zones['name']))
        else:
            self.logger.info("No room data available.  Please update or may not be possible with this model.")

        self.logger.debug(unicode(myArray))
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
        self.logger.debug("actionControlDevice Called: action:"+unicode(action)+" for device :"+unicode(device.name))
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
                self.logger.debug("Unsupport Command sent:  Command Sent:"+unicode(command))
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
                self.logLevel = int(valuesDict[u"logLevel"])
            except:
                self.logLevel = logging.INFO
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"logLevel = " + str(self.logLevel))
            self.datetimeFormat = valuesDict.get('datetimeFormat', '%c')
            self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
            self.logger.debug(u"updateFrequency = " + str(self.updateFrequency))
            self.next_update_check = time.time()
            self.debugTrue = self.pluginPrefs.get('debugTrue', '')
            self.debugOther = self.pluginPrefs.get('debugOther', True)
    ########################################
    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        self.logger.debug(u'closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):')
        self.logger.debug(
            u'     (' + unicode(valuesDict) + u', ' + unicode(userCancelled) + ', ' + unicode(typeId) + u', ' + unicode(
                devId) + u')')




    def validateDeviceConfigUi(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"validateDeviceConfigUi called")
        errorDict = indigo.Dict()
        address = valuesDict['address']
        if address == None or address <= 0:
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
        MAChome     = os.path.expanduser("~")+"/"
        folderLocation = MAChome+"Documents/Indigo-iRobotRoomba/"
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
        self.logger.debug(u"update Roomba Mapping Info: "+unicode(deviceId))

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


    def getRoombaPassword(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"getRoombaPassword called: "+unicode(deviceId))
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
        # #self.logger.error(unicode(result))
        # if self.softwareVersion != '':
        #     self.logger.debug('Software Version of Roomba Found:'+unicode(self.softwareVersion))
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
            self.logger.debug(u'Checking Number of Active Threads:' + unicode(threading.activeCount() ) )
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
            self.logger.debug("Caught Exception refreshThreadData:"+unicode(ex))


    def threadgetPassword(self, roombaIP,filename,forceSSL, device, softwareversion, useCloud, cloudLogin, cloudPassword, blid):
        try:
            self.passwordReturned = "reset"
            self.logger.debug(u'Thread:Get Password called.' + u' & Number of Active Threads:' + unicode(threading.activeCount() ) )
            result = password(self, address=roombaIP, file=filename, useCloud=useCloud, cloudLogin=cloudLogin, cloudPassword=cloudPassword, forceSSL=forceSSL)
            self.logger.debug("Password Returned:"+unicode(self.passwordReturned))
            for property, value in vars(result).items():
                self.logger.debug(unicode(property) + ":" + unicode( value))
                if property=="iRoombaMAC":
                    if value:
                        device.updateStateOnServer('MAC', value=str(value))
                if property == "iRoombaName":
                    if value:
                        device.updateStateOnServer('Name', value=str(value))
                if property == 'iRoombaSWver':
                    if value:
                        self.logger.debug('Software Version of Roomba Found:' + unicode(value))
                        device.updateStateOnServer('softwareVer', value=str(value))
                if property =="blid":
                    if value != "":
                        self.logger.debug("Blid of iRoomba Found:"+unicode(value))
                        device.updateStateOnServer('blid', value=str(value))
                        blid = str(value)
            #self.logger.debug("Returning Result:"+unicode(result))
            time.sleep(3)
            self.logger.info("Checking for updated Map Info")
            result = irobotAPI_Maps(self, address=roombaIP, useCloud=useCloud, cloudLogin=cloudLogin, cloudPassword=cloudPassword, blid=blid)
            time.sleep(5)
            self.checkAllRoombas()
            return result
        except Exception as e:
            self.logger.exception("Caught Exception:"+unicode(e))
            return False

    def logAllRoombas(self):
        self.logger.debug(u"{0:=^130}".format(""))
        self.logger.debug(u'log All Roomba Info Menu Item Called:')
        self.logger.debug(u"{0:=^130}".format(""))
        for myroomba in self.roomba_list:
            self.logger.debug(u"{0:=^130}".format(""))
            for property, value in vars(myroomba).items():
                self.logger.debug(unicode(property) + ":" + unicode(value))


    def getRoombaInfoAction(self, pluginAction, roombaDevice):
        self.logger.debug(u"getRoombaInfoAction for %s" % roombaDevice.name)
        self.updateMasterStates()

    def connectRoomba(self,device):
        if self.debugOther:
            self.logger.debug("connectRoomba Called self.roomba_list = "+unicode(self.roomba_list))

        deviceroombaName = str(device.states['Name'])
        if self.debugOther:
            self.logger.debug("Device Name  = "+unicode(deviceroombaName))

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
                self.logger.debug(u'connecting Roomba Device: '+unicode(device.name))
            roombaIP = device.pluginProps.get('address', 0).encode('utf-8')
            softwareVersion = device.states['softwareVer']
            forceSSL = device.pluginProps.get('forceSSL',False)
            if roombaIP == 0:
                device.updateStateOnServer(key="deviceStatus", value="Communications Error")
                self.updateVar(device.states['IP'], False)
                device.updateStateOnServer(key="onOffState", value=False, uiValue="Communications Error")
                device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                self.logger.error(u"getDeviceStatus: Roomba IP address not configured.")
                return
            filename = str(roombaIP)+"-config.ini"
            MAChome = os.path.expanduser("~")+"/"
            folderLocation = MAChome+"Documents/Indigo-iRobotRoomba/"
            file = folderLocation + filename
            if self.debugOther:
                self.logger.debug(u'Using config file: ' + file)
            if os.path.isfile(file):
                myroomba = Roomba( self, address=roombaIP, file=filename, softwareversion=softwareVersion, forceSSL=forceSSL, roombaName=deviceroombaName)
                myroomba.set_options(raw=False, indent=0, pretty_print=False)
                myroomba.connect()

                if myroomba not in self.roomba_list:  ## not convinced this will work correctly; is checked above anyhow...
                    self.logger.debug("Adding myroomba to self.roomba_list..")
                    self.roomba_list.append(myroomba)
                    self.logger.debug("self.roomba_list:"+unicode(self.roomba_list))
                return True
            else:
                self.logger.error(u'Config file for device does not exist - check Device settings')
                return False
        #self.logger.error(unicode(self.myroomba.master_state))

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
            self.logger.debug(u"check on_message called by on_message iroomba function: For Device:"+unicode(roombaipaddress))
            #self.logger.debug(unicode(masterState))
            #self.logger.debug(unicode(roombaipaddress))

        # when message received, master_state already updated.
        # Just recall save for all states - some unchanged.. but unlikely much benefit of multiple if/choices

        for dev in indigo.devices.iter("self"):
            for myroomba in self.roomba_list:
                if str(roombaipaddress) == str(dev.states['IP']):
                    self.logger.debug(u"Found Device: "+unicode(roombaipaddress)+' Matching device IP'+unicode(dev.states['IP']))
                    if (dev.deviceTypeId == "roombaDevice") and myroomba.master_state != None:
                        self.saveMasterStateDevice(masterState, dev, current_state, fromonmessage=True)

        return

    def saveMasterStateDevice(self, masterState, device, currentstate, fromonmessage=False):
        if self.debugOther:
            self.logger.debug(u'saveMasterStateDevice called.  FromonMessage:'+unicode(fromonmessage)+" and currentstate:"+unicode(currentstate))

        if masterState != None:
            if self.debugOther:
              #  if fromonmessage==False o:
                self.logger.debug(u'Writing Master State Device:' +unicode(device.id) +":"+unicode(json.dumps(masterState)))
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
                        #self.logger.error(u'MasterState state/reported :' + unicode(masterState['state']['reported']) )
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
                            #self.logger.debug(u'MasterState Bin Full :'+ unicode(masterState['state']['reported']['bin']['full']))
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

                    if errorCode == '0' and notReady == '0':
                        device.updateStateOnServer(key="deviceStatus", value=unicode(state))
                        device.updateStateOnServer(key="errornotReady_Statement", value="")
                        self.updateVar(device.states['IP'], True)
                        device.updateStateOnServer(key="onOffState", value=True, uiValue=unicode(state))
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                    elif errorCode != '0':
                        device.updateStateOnServer(key="deviceStatus", value=errorText)
                        device.updateStateOnServer(key="errornotReady_Statement",value=self.geterrorNotreadySentence(device, errorCode=errorCode, notReadyCode=notReady) )
                        self.updateVar(device.states['IP'], False)
                        device.updateStateOnServer(key="onOffState", value=False, uiValue=unicode(errorText))
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                    elif notReady != '0':
                        device.updateStateOnServer(key="deviceStatus", value=notReadyText)
                        device.updateStateOnServer(key="errornotReady_Statement", value=self.geterrorNotreadySentence(device, errorCode=errorCode, notReadyCode=notReady) )
                        self.updateVar(device.states['IP'], False)
                        device.updateStateOnServer(key="onOffState", value=False, uiValue=unicode(notReadyText))
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

                    if statement !="":
                        device.updateStateOnServer('currentState_Statement', value=unicode(statement))
                    else:
                        device.updateStateOnServer('currentState_Statement', value=unicode(state))

        return
          #  self.logger.debug(unicode(masterState))100

      #  masterjson = json.dumps(masterState)

      #  with open(file, 'w') as cfgfile:
      #      json.dump(masterjson, cfgfile, ensure_ascii=False)
      #      self.logger.debug(u'Saved Master State')
      #      cfgfile.close()

    def geterrorNotreadySentence(self,device, errorCode="0", notReadyCode="0"):
        try:
            self.logger.debug("geterrorNotreadySentence (phew) run, with errorCode:"+unicode(errorCode)+" and notReadyCode:"+unicode(notReadyCode))

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
                    self.logger.debug("error_"+str(errorCode)+" exists and is "+unicode(valuetouse) )
                    return valuetousereplace

            if notReadyCode != "0":
                self.logger.debug("Checking for notification_start_refuse_"+str(notReadyCode) )
                keytouse = str("notification_start_refuse_"+str(notReadyCode))
                if keytouse in self.newiroombaData:
                    valuetouse = str(self.newiroombaData[keytouse])
                    valuetousereplace = valuetouse.replace('%s', str(iroombaName))
                    self.logger.debug("NotreadyCode "+str(notReadyCode)+" exists and is "+unicode(valuetouse) )
                    return valuetousereplace

            return ""

        except:
            self.logger.debug("Exception in get sentence")
            return ""

    def disconnectRoomba(self,device):
        self.logger.debug(u'disconnecting Roomba Device: '+unicode(device.name))
        for myroomba in self.roomba_list:
            if str(myroomba.address) == str(device.states['IP']):
                self.logger.debug("disconnectRoomba Matching iroomba found")
                if myroomba.master_state != None:
                    self.saveMasterStateDevice(myroomba.master_state, device, "", fromonmessage=False)
                    self.logger.debug(unicode(myroomba.master_state))
                myroomba.disconnect()
                self.roomba_list.remove(myroomba)
                self.logger.debug("Self.Roomba_list:"+unicode(self.roomba_list))
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
            self.logger.debug(u"No connected iRoombas found now for "+unicode(self.KILLcount)+" times...")
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
            #self.logger.debug(u'self.connected equals:'+unicode(self.connected)+"& self.continuous equals:"+unicode(self.continuous))
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

        self.logger.debug(u'Current State is:' + unicode(Cycle))

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
        self.RoombaAction(pluginAction, roombaDevice, 'pause')
        self.sleep(1)
        self.RoombaAction(pluginAction, roombaDevice, 'dock')

    def evacRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'evac')

    def getLastCommand(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"getLastCommand called: "+unicode(deviceId))
        self.logger.debug(u"getLastCommand valuesDict: " + unicode(valuesDict))
        self.logger.debug(u"getLastCommand typeId: " + unicode(typeId))
        try:
            roombaDeviceID = int(valuesDict.get("roombatoUse",0))
            if roombaDeviceID == 0:
                self.logger.info("Please select a roomba to use")
                return
            roombaDevice = indigo.devices[roombaDeviceID]
            iroombaName = str(roombaDevice.states['Name'])
            iroombaIP = str(roombaDevice.states['IP'])
            self.logger.debug("Roomba Name:" + unicode(iroombaName))
            self.logger.debug("Roomba IP:" + unicode(iroombaIP))
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
                                self.logger.info(unicode(json.dumps(lastcommand)))
                                valuesDict['commandToSend']=json.dumps(lastcommand)
                                self.logger.debug(unicode(valuesDict))
                                return valuesDict
                            else:
                                self.logger.info("No Last Command found please try again")
                                return

        except Exception as ex:
            self.logger.exception("Exception ")

    def sendSpecificRoomCommand(self, pluginAction, roombaDevice):
        self.logger.debug("send Specific Room Clean called to run")
        self.logger.debug("pluginAction "+unicode(pluginAction))
        self.logger.debug("roombaDevice IP:" + unicode(roombaDevice.states['IP']))

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
        self.logger.debug(unicode(actionRooms))

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
            self.logger.debug("Roomba Name:"+unicode(iroombaName))
            self.logger.debug("Roomba IP:" + unicode(iroombaIP))
            #self.logger.debug("Connected Roomba Name:"+unicode(self.connectedtoName))

            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(iroombaIP):
                    if myroomba.roomba_connected == False:
                        self.logger.debug(u"Not connected to iRoomba:"+unicode(iroombaName)+" & IP:"+unicode(iroombaIP)+u" -- Should be --- Attempting to reconnect.")
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
                        self.logger.debug("Sending Command to myroomba:"+unicode(myroomba.roombaName)+" and action:"+str(json.dumps(action)))
                        myroomba.send_command_special(json.dumps(action))

            return

        except Exception as e:
            self.logger.exception(u'Caught Error within RoombaAction:'+unicode(e))

    def lastCommandRoombaAction(self, pluginAction, roombaDevice):
        self.logger.debug("lastcommandRoombaAction")
        self.logger.debug("pluginAction "+unicode(pluginAction))

        action = []
        commandtosend = ""
        if "commandToSend" in pluginAction.props:
            commandtosend = pluginAction.props.get("commandToSend")
            self.logger.debug(unicode(commandtosend))

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
            self.logger.debug("Roomba Name:"+unicode(iroombaName))
            self.logger.debug("Roomba IP:" + unicode(iroombaIP))
            #self.logger.debug("Connected Roomba Name:"+unicode(self.connectedtoName))

            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(iroombaIP):
                    if myroomba.roomba_connected == False:
                        self.logger.debug(u"Not connected to iRoomba:"+unicode(iroombaName)+" & IP:"+unicode(iroombaIP)+u" -- Should be --- Attempting to reconnect.")
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
                        self.logger.debug("Sending Command to myroomba:"+unicode(myroomba.roombaName)+" and action:"+str(json.dumps(action)))
                        myroomba.send_command_special(json.dumps(action))

            return

        except Exception as e:
            self.logger.exception(u'Caught Error within RoombaAction:'+unicode(e))

    def RoombaAction(self, pluginAction, roombaDevice, action):
        self.logger.debug(u"startRoombaAction for "+unicode(roombaDevice.name)+": Action : "+str(action))
        # Add a try except loop to catch nicely any errors.
        try:
            iroombaName = str(roombaDevice.states['Name'])
            iroombaIP = str(roombaDevice.states['IP'])
            self.logger.debug("Roomba Name:"+unicode(iroombaName))
            self.logger.debug("Roomba IP:" + unicode(iroombaIP))
            #self.logger.debug("Connected Roomba Name:"+unicode(self.connectedtoName))

            for myroomba in self.roomba_list:
                if str(myroomba.address) == str(iroombaIP):
                    if myroomba.roomba_connected == False:
                        self.logger.debug(u"Not connected to iRoomba:"+unicode(iroombaName)+" & IP:"+unicode(iroombaIP)+u" -- Should be --- Attempting to reconnect.")
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
                        self.logger.debug("Sending Command to myroomba:"+unicode(myroomba.roombaName)+" and action:"+str(action))
                        myroomba.send_command(str(action))

            return


        except Exception as e:
            self.logger.debug(u'Caught Error within RoombaAction:'+unicode(e))