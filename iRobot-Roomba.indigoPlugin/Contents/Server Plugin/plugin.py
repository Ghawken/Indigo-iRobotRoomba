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
import OpenSSL
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

        try:
            self.logLevel = int(self.pluginPrefs[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))
        self.debugTrue = self.pluginPrefs.get('debugTrue', '')

    def pluginStore(self):
        self.logger.info(u'Opening Plugin Store.')
        iurl = 'http://www.indigodomo.com/pluginstore/132/'
        self.browserOpen(iurl)


    def startup(self):
        self.logger.info(u"Starting Roomba")

        self.triggers = { }
        self.masterState = None
        self.currentstate = ""
        self.updater = GitHubPluginUpdater(self)
        self.KILL = False
        self.restarted = 0
        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0

        self.logger.debug(u"updateFrequency = " + str(self.updateFrequency))
        self.next_update_check = time.time()

        self.continuous = self.pluginPrefs.get('continuous', False)

        #automatically disconnect reconnect even in continuous after elapsed time - 12 hours
        self.reconnectFreq = 12*60*60
        self.connectTime = self.reconnectFreq +time.time()

        self.statusFrequency = float(self.pluginPrefs.get('statusFrequency', "10")) * 60.0

        self.logger.debug(u"statusFrequency = " + str(self.statusFrequency))

        self.next_status_check = time.time()
        self.myroomba = None
        self.connected = False

        self.connectedtoName = "none"

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

    def restartPlugin(self):
        indigo.server.log(u"restart Plugin Called.")
        plugin = indigo.server.getPlugin('com.GlennNZ.indigoplugin.irobot')
        plugin.restart()

    def runConcurrentThread(self):

        try:
            while True:

                #self.sleep(5)
                self.checkAllRoombas()
                self.sleep(60)

                if self.KILL == True:
                    self.logger.debug('Self.Kill is true,  restarting plugin')
                    self.KILL = False
                    self.restarted = 1
                    self.restartPlugin()

                if self.statusFrequency > 0:
                    if time.time() > self.next_status_check:
                        if self.debugTrue:
                            self.logger.debug(u'checking all Roombas now....')
                        if self.connected == False or (self.continuous == True and self.myroomba == None):
                            self.checkAllRoombas()   # if not using continuous connection check here - at time allowed
                        if (self.continuous == True and self.connected == True) :
                            self.updateMasterStates(self.currentstate)   # if using continuous - should already be connected just update states here
                        self.next_status_check = time.time() + self.statusFrequency

                if time.time() > self.connectTime and self.continuous == True:
                    # Disconnect and Reconnect Roomba
                    if self.debugTrue:
                        self.logger.debug(u'Up for long enough reconnecting..')
                    self.reconnectRoomba()
                    self.connectTime = time.time() + self.reconnectFreq


                self.sleep(60.0)

        except self.stopThread:
            pass

    def deviceStartComm(self, device):
        self.logger.debug(u"deviceStartComm called for " + device.name)
        device.stateListOrDisplayStateIdChanged()

        #self.getRoombaInfo(device)
        #self.getRoombaStatus(device)
        #self.getRoombaTime(device)

    def deviceStopComm(self, device):
        self.logger.debug(u"deviceStopComm called for " + device.name)
        device.updateStateOnServer(key="deviceStatus", value="Communications Error")
        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)


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
            self.debugTrue = self.pluginPrefs.get('debugTrue', '')

    ########################################

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




    def getRoombaPassword(self, valuesDict, typeId, deviceId):
        self.logger.debug(u"getRoombaPassword called: "+unicode(deviceId))
        device = indigo.devices[deviceId]
        device.updateStateOnServer('softwareVer', value='Unknown')
        roombaIP = valuesDict.get('address', 0)
        forceSSL = valuesDict.get('forceSSL',False)

        if roombaIP == 0 or roombaIP == '':
            self.logger.error(u'IP Address cannot be Empty.  Please empty valid IP before using Get Password')
            return False

        #Roomba.connect()
        filename = str(roombaIP)+"-config.ini"
        self.softwareVersion = ''
        result = password(self, address=roombaIP, file=filename, forceSSL=forceSSL  )
        #self.logger.error(unicode(result))
        if self.softwareVersion != '':
            self.logger.debug('Software Version of Roomba Found:'+unicode(self.softwareVersion))
            device.updateStateOnServer('softwareVer', value=self.softwareVersion)
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
        softwareVersion = device.states['softwareVer']
        forceSSL = device.pluginProps.get('forceSSL',False)
        if roombaIP == 0:
            device.updateStateOnServer(key="deviceStatus", value="Communications Error")
            device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
            self.logger.error(u"getDeviceStatus: Roomba IP address not configured.")
            return
        filename = str(roombaIP)+"-config.ini"
        MAChome = os.path.expanduser("~")+"/"
        folderLocation = MAChome+"Documents/Indigo-iRobotRoomba/"
        file = folderLocation + filename
        self.logger.debug(u'Using config file: ' + file)
        if os.path.isfile(file):
            self.myroomba = Roomba( self, address=roombaIP, file=filename, softwareversion=softwareVersion, forceSSL=forceSSL)
            self.myroomba.set_options(raw=False, indent=0, pretty_print=False)
            self.myroomba.connect()
            return True
        else:
            self.logger.error(u'Config file for device does not exist - check Device settings')
            return False
        #self.logger.error(unicode(self.myroomba.master_state))

    def saveMasterStateDevice(self, masterState, device, currentstate):
        if self.debugTrue:
            self.logger.debug(u'saveMasterStateDevice called.')

        if masterState != None:
            if self.debugTrue:
                self.logger.debug(u'Writing Master State Device:' +unicode(device.id) +":"+unicode(masterState))
            state =""
            errorCode ='0'
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
                        #self.logger.debug(u'MasterState Bat Pct :' + unicode(masterState['state']['reported']['batPct']))
                        device.updateStateOnServer('BatPct', value=str(masterState['state']['reported']['batPct']))

                    if 'cleanMissionStatus' in masterState['state']['reported']:
                        if 'cycle' in masterState['state']['reported']['cleanMissionStatus']:
                            #self.logger.debug(u'MasterState Bat cycle :'+ masterState['state']['reported']['cleanMissionStatus']['cycle'])
                            device.updateStateOnServer('Cycle',value=str(masterState['state']['reported']['cleanMissionStatus']['cycle']))

                        if 'phase' in masterState['state']['reported']['cleanMissionStatus']:
                            #self.logger.debug(u'MasterState Bat phase :'+ masterState['state']['reported']['cleanMissionStatus']['phase'])
                            device.updateStateOnServer('Phase', value=str(masterState['state']['reported']['cleanMissionStatus']['phase']))
                            state = str("Roomba Ok - ") + str(masterState['state']['reported']['cleanMissionStatus']['phase'])
                        if 'error' in masterState['state']['reported']['cleanMissionStatus']:
                            device.updateStateOnServer('ErrorCode', value=str(masterState['state']['reported']['cleanMissionStatus']['error']))
                            errorCode = str(masterState['state']['reported']['cleanMissionStatus']['error'])
                            try:
                                errorText = self.errorStrings[errorCode]
                            except:
                                errorText = "Undocumented Error Code (%s)" % errorCode
                            device.updateStateOnServer('ErrorText', value=errorText)

                        if 'notReady' in masterState['state']['reported']['cleanMissionStatus']:
                            device.updateStateOnServer('NotReady', value=str(
                                masterState['state']['reported']['cleanMissionStatus']['notReady']))
                            notReady = str(masterState['state']['reported']['cleanMissionStatus']['notReady'])
                            try:
                                notReadyText = self.notReadyStrings[notReady]
                            except:
                                notReadyText = "Undocumented Not Ready Value (%s)" % notReady
                            device.updateStateOnServer('NotReadyText', value=notReadyText)

                        if 'sqft' in masterState['state']['reported']['cleanMissionStatus']:
                            device.updateStateOnServer('SqFt', value=str(
                                masterState['state']['reported']['cleanMissionStatus']['sqft']))
                        if 'rechrgM' in masterState['state']['reported']['cleanMissionStatus']:
                            device.updateStateOnServer('RechargeM', value=str(
                                masterState['state']['reported']['cleanMissionStatus']['rechrgM']))


                    if 'bin' in masterState['state']['reported']:
                        if 'full' in masterState['state']['reported']['bin']:
                            #self.logger.debug(u'MasterState Bin Full :'+ unicode(masterState['state']['reported']['bin']['full']))
                            if masterState['state']['reported']['bin']['full'] == True:
                                device.updateStateOnServer('BinFull', value=True)
                            if masterState['state']['reported']['bin']['full'] == False:
                                device.updateStateOnServer('BinFull', value=False)


                    if currentstate != "":
                        state = str(currentstate)

                    if errorCode == '0' and notReady == '0':
                        device.updateStateOnServer(key="deviceStatus", value=unicode(state))
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                    elif errorCode != '0':
                        device.updateStateOnServer(key="deviceStatus", value=errorText)
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                    elif notReady != '0':
                        device.updateStateOnServer(key="deviceStatus", value=notReadyText)
                        device.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)


        return
          #  self.logger.debug(unicode(masterState))

      #  masterjson = json.dumps(masterState)

      #  with open(file, 'w') as cfgfile:
      #      json.dump(masterjson, cfgfile, ensure_ascii=False)
      #      self.logger.debug(u'Saved Master State')
      #      cfgfile.close()



    def disconnectRoomba(self,device):
        self.logger.debug(u'disconnecting Roomba Device: '+unicode(device.name))

        if self.myroomba != None:
            if self.myroomba.master_state != None:
                self.saveMasterStateDevice(self.myroomba.master_state, device, "")
                self.logger.debug(unicode(self.myroomba.master_state))
            self.myroomba.disconnect()
            self.myroomba = None

    def removeRoomba(self):
        self.logger.debug(u'removeRoomba run')
        self.myroomba.disconnect()
        self.myroomba = None
        return


    def getRoombaInfo(self, device):
        self.logger.debug(u"getRoombaInfo for %s" % device.name)
        #self.logger.debug(u'')
        #
        # if above true - connect to one device only (1st one found) and do so with continuous connection - constant updates...

        if self.connectRoomba(device):
            time.sleep(15)
            if self.continuous == False:
                self.disconnectRoomba(device)
        return

    def updateMasterStates(self, current_state):
        if self.debugTrue:
            self.logger.debug(u'updateMasterStates called.')
        for dev in indigo.devices.iter("self"):
            if self.myroomba != None:
                if (dev.deviceTypeId == "roombaDevice") and self.myroomba.master_state != None:
                    self.saveMasterStateDevice(self.myroomba.master_state, dev, current_state)
        return

    def reconnectRoomba(self):
        self.logger.debug("Restablish connection for Roomba Run - reconnectRoomba")
        for dev in indigo.devices.iter("self"):
            if self.myroomba != None:
                self.disconnectRoomba(dev)
            time.sleep(15)
            self.connectRoomba(dev)
        return




    def getRoombaStatusAction(self, pluginAction, roombaDevice):
        self.logger.debug(u"getRoombaStatusAction for %s" % roombaDevice.name)
        #self.getRoombaInfo(roombaDevice)

    def getRoombaStatus(self, device):
        self.logger.debug(u"getRoombaStatus for %s" % device.name)

        self.triggerCheck(device)


    def checkAllRoombas(self):
        if self.debugTrue:
            self.logger.debug(u'checkALlRoombas called. ')
            self.logger.debug(u'self.connected equals:'+unicode(self.connected)+"& self.continuous equals:"+unicode(self.continuous))
        for dev in indigo.devices.iter("self"):
            if self.continuous == False:
                if (dev.deviceTypeId == "roombaDevice"):
                    self.logger.debug(u'getRoomba Info Running..')
                    self.getRoombaInfo(dev)
                    time.sleep(60)

            if self.continuous == True and self.connected == False:
                  if (dev.deviceTypeId == "roombaDevice"):
                    self.logger.debug(u'Continuous ON and not connected.. ')
                    self.getRoombaInfo(dev)

                #self.getRoombaStatus(dev)
                #self.getRoombaTime(dev)

    def toggleRoombaAction(self, pluginAction, roombaDevice):
        self.logger.debug(u'toggle Roomba Action Call')

        Cycle = roombaDevice.states['Cycle']

        self.logger.debug(u'Current State is:' + unicode(Cycle))

        if Cycle =='clean':
            self.logger.debug(u'Roomba Cycle clean changing to docking...')
            self.RoombaAction(pluginAction, roombaDevice, 'dock')
        if Cycle == 'charge':
            self.logger.debug(u'Roomba changing to running...')
            self.RoombaAction(pluginAction, roombaDevice, 'start')
        if Cycle == 'run':
            self.logger.debug(u'Roomba changing to docking...')
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
        self.RoombaAction(pluginAction, roombaDevice, 'dock')

    def evacRoombaAction(self, pluginAction, roombaDevice):
        self.RoombaAction(pluginAction, roombaDevice, 'evac')

    def RoombaAction(self, pluginAction, roombaDevice, action):

        self.logger.debug(u"startRoombaAction for "+unicode(roombaDevice.name)+": Action : "+str(action))
        # Add a try except loop to catch nicely any errors.
        try:
            iroombaName = roombaDevice.states['Name']
            self.logger.debug("Roomba Name:"+unicode(iroombaName))
            self.logger.debug("Connected Roomba Name:"+unicode(self.connectedtoName))

            if self.connected == False and self.continuous== False:
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
                self.myroomba.send_command(str(action))
                time.sleep(5)
                self.disconnectRoomba(roombaDevice)
                time.sleep(5)
                return

            if self.connected == True:  ## may be the wrong iroomba that you are already connected to...
                if self.connectedtoName != iroombaName:   ## wrong iroomba connected
                    self.disconnectRoomba(roombaDevice)
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
                    self.myroomba.send_command(str(action))
                    time.sleep(5)
                    if self.continuous == False:
                        self.disconnectRoomba(roombaDevice)
                    return
                else:  ## already connected to correct device.. don't disconnect, make most of it

                #self.connectRoomba(roombaDevice)
                #time.sleep(5)
                    self.myroomba.send_command(str(action))
                    time.sleep(5)
                    if self.continuous == False:
                        self.disconnectRoomba(roombaDevice)
                return

        except Exception as e:
            self.logger.debug(u'Caught Error within RoombaAction:'+unicode(e))