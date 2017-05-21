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
from base64 import b64encode
from roomba import Roomba
from roomba import password
#import paho.mqtt.client as mqtt

#from requests.auth import HTTPBasicAuth
#from requests.utils import quote

from ghpu import GitHubPluginUpdater

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

        try:
            self.logLevel = int(self.pluginPrefs[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))
        self.folderLocation = self.pluginPrefs.get('folderLocation', '')
        self.debugTrue = self.pluginPrefs.get('debugTrue', '')

    def startup(self):
        indigo.server.log(u"Starting Roomba")

        self.triggers = { }
        self.masterState = None
        self.updater = GitHubPluginUpdater(self)
        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
        self.logger.debug(u"updateFrequency = " + str(self.updateFrequency))
        self.next_update_check = time.time()

        self.statusFrequency = float(self.pluginPrefs.get('statusFrequency', "10")) * 60.0
        self.logger.debug(u"statusFrequency = " + str(self.statusFrequency))
        self.next_status_check = time.time()
        self.myroomba = None

        self.errorStrings = {
            '0' : 'No Error',
            '1' : 'Place Roomba on a flat surface then press CLEAN to restart.',
            '2' : 'Clear Roombas debris extractors, then press CLEAN to restart.',
            '5' : 'Left/Right. Clear Roombas wheel, then press CLEAN to restart.',
            '6' : 'Move Roomba to a new location then press CLEAN to restart. The cliff sensors are dirty, it is hanging over a drop, or it is stuck on a dark surface.',
            '8' : 'The fan is stuck or its filter is clogged.',
            '9' : 'Tap Roombas bumper, then press CLEAN to restart.',
            '10': 'The left or right wheel is not moving.',
            '11': 'Roomba has an internal error.',
            '14': 'Re-install Roomba’s bin then press CLEAN to restart. The bin has a bad connection to the robot.',
            '15': 'Press CLEAN to restart. Roomba has an internal error',
            '16': 'Place Roomba on a flat surface then press CLEAN to restart. Roomba has started while moving or at an angle, or was bumped while running.',
            '17': 'The cleaning job is incomplete.',
            '18': 'Roomba cannot return to the Home Base or starting position.',
        }

        self.notReadyStrings = {
            '0' : 'Ready',
            '7' : 'Bin Missing',
            '15': 'Battery Low',
            '16': 'Bin Full',
        }

    def shutdown(self):
        indigo.server.log(u"Shutting down Roomba")

    def runConcurrentThread(self):

        try:
            while True:

                if self.updateFrequency > 0:
                    if time.time() > self.next_update_check:
                        self.updater.checkForUpdate()
                        self.next_update_check = time.time() + self.updateFrequency

                if self.statusFrequency > 0:
                    if time.time() > self.next_status_check:
                        self.logger.debug(u'checking all Roombas now....')
                        self.checkAllRoombas()
                        self.next_status_check = time.time() + self.statusFrequency

                self.sleep(60.0)

        except self.stopThread:
            pass

    def deviceStartComm(self, device):
        self.logger.debug(u"deviceStartComm called for " + device.name)


        #self.getRoombaInfo(device)
        #self.getRoombaStatus(device)
        #self.getRoombaTime(device)


    def triggerStartProcessing(self, trigger):
        self.logger.debug("Adding Trigger %s (%d) - %s" % (trigger.name, trigger.id, trigger.pluginTypeId))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.logger.debug("Removing Trigger %s (%d)" % (trigger.name, trigger.id))
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

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

    def checkForUpdates(self):
        self.updater.checkForUpdate()

    def updatePlugin(self):
        self.updater.update()

    def forceUpdate(self):
        self.updater.update(currentVersion='0.0.0')

    ########################################
    # ConfigUI methods
    ########################################

    def validatePrefsConfigUi(self, valuesDict):
        self.logger.debug(u"validatePrefsConfigUi called")
        errorDict = indigo.Dict()

        updateFrequency = int(valuesDict['updateFrequency'])
        if (updateFrequency < 0) or (updateFrequency > 24):
            errorDict['updateFrequency'] = u"Update frequency is invalid - enter a valid number (between 0 and 24)"

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

            self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
            self.logger.debug(u"updateFrequency = " + str(self.updateFrequency))
            self.next_update_check = time.time()

    ########################################

    def validateDeviceConfigUi(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"validateDeviceConfigUi called")
        errorDict = indigo.Dict()

        return (True, valuesDict)


    ########################################

    def getRoombaPassword(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"getRoombaPassword called: "+unicode(deviceId))
        roombaIP = valuesDict.get('address', 0)
        #Roomba.connect()
        filename = str(deviceId)+"-config.ini"
        result = password(self, address=roombaIP, file=filename)
        #self.logger.error(unicode(result))
        if result == True:
            valuesDict['password'] = 'OK'
            self.logger.info(u'Password Saved. Click Ok.')
        return valuesDict


    def getRoombaInfoAction(self, pluginAction, roombaDevice):
        self.logger.debug(u"getRoombaInfoAction for %s" % roombaDevice.name)
        #self.getRoombaInfo(roombaDevice)

    def connectRoomba(self,device):
        self.logger.debug(u'connecting Roomba Device: '+unicode(device.name))
        roombaIP = device.pluginProps.get('address', 0).encode('utf-8')
        if roombaIP == 0:
            device.updateStateOnServer(key="deviceStatus", value="Communications Error")
            device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            self.logger.error(u"getDeviceStatus: Roomba IP address not configured.")
            return

        filename = str(device.id)+"-config.ini"
        MAChome = os.path.expanduser("~")+"/"
        folderLocation = MAChome+"Documents/Indigo-iRobotRoomba/"

        file = folderLocation + filename
        self.logger.debug(u'Using config file: ' + file)
        if os.path.isfile(file):

            self.myroomba = Roomba( self, address=roombaIP, file=filename)
            self.myroomba.set_options(raw=False, indent=0, pretty_print=False)
            self.myroomba.connect()

            return True
        else:
            self.logger.error(u'Config file for device does not exist - check Device settings')
            return False
        #self.logger.error(unicode(self.myroomba.master_state))

    def saveMasterStateDevice(self, masterState, device):
        filename = str(device.id)+"-masterstate.json"
        MAChome = os.path.expanduser("~")+"/"
        folderLocation = MAChome+"Documents/Indigo-iRobotRoomba/"

        file = folderLocation + filename

       # if not os.path.isdir(self.folderLocation):
       #     try:
        #        ret = os.makedirs(self.folderLocation)
        #    except:
        #        self.logger.error(u"Error Creating " + unicode(self.folderLocation))
        #        pass

        if masterState != None:
            self.logger.debug(u'Writing Master State Device:' +unicode(device.id) +":"+unicode(masterState))
            if masterState['state'] != None:
                self.logger.debug(u'MasterState Name :'+ masterState['state']['reported']['name'])
                self.logger.debug(u'MasterState Bat Pct :'+ unicode(masterState['state']['reported']['batPct']))
                self.logger.debug(u'MasterState Bat cycle :'+ masterState['state']['reported']['cleanMissionStatus']['cycle'])
                self.logger.debug(u'MasterState Bat phase :'+ masterState['state']['reported']['cleanMissionStatus']['phase'])

                device.updateStateOnServer('BatPct', value=str(masterState['state']['reported']['batPct']))
                device.updateStateOnServer('Cycle', value=str(masterState['state']['reported']['cleanMissionStatus']['cycle']))
                device.updateStateOnServer('Phase', value=str(masterState['state']['reported']['cleanMissionStatus']['phase']))
                device.updateStateOnServer('ErrorCode', value=str(masterState['state']['reported']['cleanMissionStatus']['error']))
                device.updateStateOnServer('NotReady', value=str(masterState['state']['reported']['cleanMissionStatus']['notReady']))

                errorCode = str(masterState['state']['reported']['cleanMissionStatus']['error'])
                try:
                    errorText = self.errorStrings[errorCode]
                except:
                    errorText = "Undocumented Error Code (%s)" % errorCode

                notReady = str(masterState['state']['reported']['cleanMissionStatus']['notReady'])
                try:
                    notReadyText = self.notReadyStrings[notReady]
                except:
                    notReadyText = "Undocumented Not Ready Value (%s)" % notReady


                device.updateStateOnServer('ErrorText', value=errorText)
                device.updateStateOnServer('NotReadyText', value=notReadyText)

                if errorCode == '0' and notReady == '0':
                    device.updateStateOnServer(key="deviceStatus", value="Roomba OK - "+str(masterState['state']['reported']['cleanMissionStatus']['phase']))
                    device.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                elif errorCode != '0':
                    device.updateStateOnServer(key="deviceStatus", value=errorText)
                    device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                elif notReady != '0':
                    device.updateStateOnServer(key="deviceStatus", value=notReadyText)
                    device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

          #  self.logger.debug(unicode(masterState))

      #  masterjson = json.dumps(masterState)

      #  with open(file, 'w') as cfgfile:
      #      json.dump(masterjson, cfgfile, ensure_ascii=False)
      #      self.logger.debug(u'Saved Master State')
      #      cfgfile.close()



    def disconnectRoomba(self,device):
        self.logger.debug(u'disconnecting Roomba Device: '+unicode(device.name))

        if self.myroomba.master_state != None:
            self.saveMasterStateDevice(self.myroomba.master_state, device)
            self.logger.debug(unicode(self.myroomba.master_state))

        self.myroomba.disconnect()
        self.myroomba = None


    def getRoombaInfo(self, device):
        self.logger.debug(u"getRoombaInfo for %s" % device.name)
        if self.connectRoomba(device):
            time.sleep(15)
            self.disconnectRoomba(device)
        return

    def updateMasterStates(self, device):
        return



    def getRoombaStatusAction(self, pluginAction, roombaDevice):
        self.logger.debug(u"getRoombaStatusAction for %s" % roombaDevice.name)
        #self.getRoombaInfo(roombaDevice)

    def getRoombaStatus(self, device):
        self.logger.debug(u"getRoombaStatus for %s" % device.name)

        self.triggerCheck(device)


    def checkAllRoombas(self):
        for dev in indigo.devices.iter("self"):
            if (dev.deviceTypeId == "roombaDevice"):
                self.logger.debug(u'getRoomba Info Running..')
                self.getRoombaInfo(dev)
                time.sleep(60)

                #self.getRoombaStatus(dev)
                #self.getRoombaTime(dev)


    def startRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'start')

    def stopRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'stop')

    def pauseRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'pause')

    def resumeRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'resume')

    def dockRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'dock')

    def RoombaAction(self, pluginAction, roombaDevice, action):
        self.logger.debug(u"startRoombaAction for "+unicode(roombaDevice.name)+": Action : "+str(action))
        self.connectRoomba(roombaDevice)
        time.sleep(5)
        self.myroomba.send_command(str(action))
        time.sleep(5)
        self.disconnectRoomba(roombaDevice)
