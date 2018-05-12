#!/usr/bin/env python
#
# Decoder for Texecom Connect API/Protocol
#
# Copyright (C) 2018 Joseph Heenan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import socket
import time
import datetime
import os
import sys
import re

import crcmod
import hexdump


class TexecomConnect:
    LENGTH_HEADER = 4
    HEADER_START = 't'
    HEADER_TYPE_COMMAND = 'C'
    HEADER_TYPE_RESPONSE = 'R'
    HEADER_TYPE_MESSAGE = 'M' # unsolicited message
    
    CMD_LOGIN = chr(1)
    CMD_GETZONEDETAILS = chr(3)
    CMD_GETLCDDISPLAY = chr(13)
    CMD_GETLOGPOINTER = chr(15)
    CMD_GETPANELIDENTIFICATION = chr(22)
    CMD_GETDATETIME = chr(23)
    CMD_GETSYSTEMPOWER = chr(25)
    CMD_SETEVENTMESSAGES = chr(37)
    
    ZONETYPE_UNUSED = 0

    CMD_RESPONSE_ACK = '\x06'
    CMD_RESPONSE_NAK = '\x15'
    
    MSG_DEBUG = chr(0)
    MSG_ZONEEVENT = chr(1)
    MSG_AREAEVENT = chr(2)
    MSG_OUTPUTEVENT = chr(3)
    MSG_USEREVENT = chr(4)
    MSG_LOGEVENT = chr(5)

    log_event_types = {}
    log_event_types[1]="Entry/Exit 1"
    log_event_types[2]="Entry/Exit 2"
    log_event_types[3]="Interior"
    log_event_types[4]="Perimeter"
    log_event_types[5]="24hr Audible"
    log_event_types[6]="24hr Silent"
    log_event_types[7]="Audible PA"
    log_event_types[8]="Silent PA"
    log_event_types[9]="Fire Alarm"
    log_event_types[10]="Medical"
    log_event_types[11]="24Hr Gas Alarm"
    log_event_types[12]="Auxiliary Alarm"
    log_event_types[13]="24hr Tamper Alarm"
    log_event_types[14]="Exit Terminator"
    log_event_types[15]="Keyswitch - Momentary"
    log_event_types[16]="Keyswitch - Latching"
    log_event_types[17]="Security Key"
    log_event_types[18]="Omit Key"
    log_event_types[19]="Custom Alarm"
    log_event_types[20]="Confirmed PA Audible"
    log_event_types[21]="Confirmed PA Audible"
    log_event_types[22]="Keypad Medical"
    log_event_types[23]="Keypad Fire"
    log_event_types[24]="Keypad Audible PA"
    log_event_types[25]="Keypad Silent PA"
    log_event_types[26]="Duress Code Alarm"
    log_event_types[27]="Alarm Active"
    log_event_types[28]="Bell Active"
    log_event_types[29]="Re-arm"
    log_event_types[30]="Verified Cross Zone Alarm"
    log_event_types[31]="User Code"
    log_event_types[32]="Exit Started"
    log_event_types[33]="Exit Error (Arming Failed)"
    log_event_types[34]="Entry Started"
    log_event_types[35]="Part Arm Suite"
    log_event_types[36]="Armed with Line Fault"
    log_event_types[37]="Open/Close (Away Armed)"
    log_event_types[38]="Part Armed"
    log_event_types[39]="Auto Open/Close"
    log_event_types[40]="Auto Arm Deferred"
    log_event_types[41]="Open After Alarm (Alarm Abort)"
    log_event_types[42]="Remote Open/Close"
    log_event_types[43]="Quick Arm"
    log_event_types[44]="Recent Closing"
    log_event_types[45]="Reset After Alarm"
    log_event_types[46]="Power O/P Fault"
    log_event_types[47]="AC Fail"
    log_event_types[48]="Low Battery"
    log_event_types[49]="System Power Up"
    log_event_types[50]="Mains Over Voltage"
    log_event_types[51]="Telephone Line Fault"
    log_event_types[52]="Fail to Communicate"
    log_event_types[53]="Download Start"
    log_event_types[54]="Download End"
    log_event_types[55]="Log Capacity Alert (80%)"
    log_event_types[56]="Date Changed"
    log_event_types[57]="Time Changed"
    log_event_types[58]="Installer Programming Start"
    log_event_types[59]="Installer Programming End"
    log_event_types[60]="Panel Box Tamper"
    log_event_types[61]="Bell Tamper"
    log_event_types[62]="Auxiliary Tamper"
    log_event_types[63]="Expander Tamper"
    log_event_types[64]="Keypad Tamper"
    log_event_types[65]="Expander Trouble (Network error)"
    log_event_types[66]="Remote Keypad Trouble (Network error)"
    log_event_types[67]="Fire Zone Tamper"
    log_event_types[68]="Zone Tamper"
    log_event_types[69]="Keypad Lockout"
    log_event_types[70]="Code Tamper Alarm"
    log_event_types[71]="Soak Test Alarm"
    log_event_types[72]="Manual Test Transmission"
    log_event_types[73]="Automatic Test Transmission"
    log_event_types[74]="User Walk Test Start/End"
    log_event_types[75]="NVM Defaults Loaded"
    log_event_types[76]="First Knock"
    log_event_types[77]="Door Access"
    log_event_types[78]="Part Arm 1"
    log_event_types[79]="Part Arm 2"
    log_event_types[80]="Part Arm 3"
    log_event_types[81]="Auto Arming Started"
    log_event_types[82]="Confirmed Alarm"
    log_event_types[83]="Prox Tag"
    log_event_types[84]="Access Code Changed/Deleted"
    log_event_types[85]="Arm Failed"
    log_event_types[86]="Log Cleared"
    log_event_types[87]="iD Loop Shorted"
    log_event_types[88]="Communication Port"
    log_event_types[89]="TAG System Exit (Batt. OK)"
    log_event_types[90]="TAG System Exit (Batt. LOW)"
    log_event_types[91]="TAG System Entry (Batt. OK)"
    log_event_types[92]="TAG System Entry (Batt. LOW)"
    log_event_types[93]="Microphone Activated"
    log_event_types[94]="AV Cleared Down"
    log_event_types[95]="Monitored Alarm"
    log_event_types[96]="Expander Low Voltage"
    log_event_types[97]="Supervision Fault"
    log_event_types[98]="PA from Remote FOB"
    log_event_types[99]="RF Device Low Battery"
    log_event_types[100]="Site Data Changed"
    log_event_types[101]="Radio Jamming"
    log_event_types[102]="Test Call Passed"
    log_event_types[103]="Test Call Failed"
    log_event_types[104]="Zone Fault"
    log_event_types[105]="Zone Masked"
    log_event_types[106]="Faults Overridden"
    log_event_types[107]="PSU AC Fail"
    log_event_types[108]="PSU Battery Fail"
    log_event_types[109]="PSU Low Output Fail"
    log_event_types[110]="PSU Tamper"
    log_event_types[111]="Door Access"
    log_event_types[112]="CIE Reset"
    log_event_types[113]="Remote Command"
    log_event_types[114]="User Added"
    log_event_types[115]="User Deleted"
    log_event_types[116]="Confirmed PA"
    log_event_types[117]="User Acknowledged"
    log_event_types[118]="Power Unit Failure"
    log_event_types[119]="Battery Charger Fault"
    log_event_types[120]="Confirmed Intruder"
    log_event_types[121]="GSM Tamper"
    log_event_types[122]="Radio Config. Failure"

    log_event_group_type = {}
    log_event_group_type[0]="Not Reported"
    log_event_group_type[1]="Priority Alarm"
    log_event_group_type[2]="Priority Alarm Restore"
    log_event_group_type[3]="Alarm"
    log_event_group_type[4]="Restore"
    log_event_group_type[5]="Open"
    log_event_group_type[6]="Close"
    log_event_group_type[7]="Bypassed"
    log_event_group_type[8]="Unbypassed"
    log_event_group_type[9]="Maintenance Alarm"
    log_event_group_type[10]="Maintenance Restore"
    log_event_group_type[11]="Tamper Alarm"
    log_event_group_type[12]="Tamper Restore"
    log_event_group_type[13]="Test Start"
    log_event_group_type[14]="Test End"
    log_event_group_type[15]="Disarmed"
    log_event_group_type[16]="Armed"
    log_event_group_type[17]="Tested"
    log_event_group_type[18]="Started"
    log_event_group_type[19]="Ended"
    log_event_group_type[20]="Fault"
    log_event_group_type[21]="Omitted"
    log_event_group_type[22]="Reinstated"
    log_event_group_type[23]="Stopped"
    log_event_group_type[24]="Start"
    log_event_group_type[25]="Deleted"
    log_event_group_type[26]="Active"
    log_event_group_type[27]="Not Used"
    log_event_group_type[28]="Changed"
    log_event_group_type[29]="Low Battery"
    log_event_group_type[30]="Radio"
    log_event_group_type[31]="Deactivated"
    log_event_group_type[32]="Added"
    log_event_group_type[33]="Bad Action"
    log_event_group_type[34]="PA Timer Reset"
    log_event_group_type[35]="PA Zone Lockout"
    
    def __init__(self, host, port , message_handler_func):
        self.host = host
        self.port = port
        self.crc8_func = crcmod.mkCrcFun(poly=0x185, rev=False, initCrc=0xff)
        self.nextseq = 0
        self.message_handler_func = message_handler_func
        self.print_network_traffic = False
        self.last_command_time = 0
        self.last_received_seq = -1
        self.zone = {}

    def hexstr(self,s):
        return " ".join("{:02x}".format(ord(c)) for c in s)

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 2-3 seconds is mentioned in section 5.5 of protocol specification
        # Increasing this value is not recommended as it will mean if the
        # panel fails to respond to a command (as it sometimes does it it
        # sends an event at the same time we send a command) it will take
        # longer for us to realise and resend the command
        self.s.settimeout(2)
        self.s.connect((self.host, self.port))
        # if we send the login message to fast the panel ignores it; texecom
        # recommend 500ms, see:
        # http://texecom.websitetoolbox.com/post/show_single_post?pid=1303528828&postcount=4&forum=627911
        time.sleep(0.5)
        
    def getnextseq(self):
        if self.nextseq == 256:
            self.nextseq = 0
        next=self.nextseq
        self.nextseq += 1
        return next

    
    def recvresponse(self):
        """Receive a response to a command. Automatically handles any
        messages that arrive first"""
        while True:
            header = self.s.recv(self.LENGTH_HEADER)
            if self.print_network_traffic:
                self.log("Received message header:")
                hexdump.hexdump(header)
            if header == "+++":
                self.log("Panel has forcibly dropped connection, possibly due to inactivity")
                self.s = None
                return None
            msg_start,msg_type,msg_length,msg_sequence = list(header)
            payload = self.s.recv(ord(msg_length) - self.LENGTH_HEADER)
            if self.print_network_traffic:
                self.log("Received message payload:")
                hexdump.hexdump(payload)
            payload, msg_crc = payload[:-1], ord(payload[-1])
            expected_crc = self.crc8_func(header+payload)
            if msg_start != 't':
                self.log("unexpected msg start: "+hex(ord(msg_start)))
                return None
            if msg_crc != expected_crc:
                self.log("crc: expected="+str(expected_crc)+" actual="+str(msg_crc))
                return None
            if msg_type == self.HEADER_TYPE_RESPONSE:
                if msg_sequence != self.last_sequence:
                    self.log("response seq: expected="+str(self.last_sequence)+" actual="+str(msg_sequence))
                    # FIXME: send command again
                    return None
            elif msg_type == self.HEADER_TYPE_MESSAGE:
                if self.last_received_seq != -1:
                    next_msg_seq = self.last_received_seq + 1
                    if next_msg_seq == 256:
                        next_msg_seq = 0
                    if msg_sequence != chr(next_msg_seq):
                        self.log("message seq: expected="+str(next_msg_seq)+" actual="+str(msg_sequence))
                        # should maybe process anyway unless it looks like a dup?
                        return None
                self.last_received_seq = ord(msg_sequence)
            # FIXME: check we received the full expected length
            # FIXME: if panel takes over 2 second to reply probably something is wrong and we need to resend the command with same sequence number
            if msg_type == self.HEADER_TYPE_COMMAND:
                self.log("received command unexpectedly")
                return None
            elif msg_type == self.HEADER_TYPE_RESPONSE:
                return payload
            elif msg_type == self.HEADER_TYPE_MESSAGE:
                self.message_handler_func(payload)
    
    def sendcommandbody(self, body):
        self.last_sequence = chr(self.getnextseq())
        data = self.HEADER_START+self.HEADER_TYPE_COMMAND+\
          chr(len(body)+5)+self.last_sequence+body
        data += chr(self.crc8_func(data))
        if self.print_network_traffic:
            self.log("Sending command:")
            hexdump.hexdump(data)
        self.s.send(data)
        self.last_command_time = time.time()
        self.last_command = data

    def login(self, udl):
        response = self.sendcommand(self.CMD_LOGIN, udl)
        if response == self.CMD_RESPONSE_NAK:
            self.log("NAK response from panel")
            return False
        elif response != self.CMD_RESPONSE_ACK:
            self.log("unexpected ack payload: "+hex(ord(response)))
            return False
        return True

    def set_event_messages(self):
        DEBUG_FLAG = 1
        ZONE_EVENT_FLAG = 1<<1
        AREA_EVENT_FLAG = 1<<2
        OUTPUT_EVENT_FLAG = 1<<3
        USER_EVENT_FLAG = 1<<4
        LOG_FLAG = 1<<5
        events = ZONE_EVENT_FLAG | AREA_EVENT_FLAG | OUTPUT_EVENT_FLAG | USER_EVENT_FLAG | LOG_FLAG
        body = chr(events & 0xff)+chr(events >> 8)
        response = self.sendcommand(self.CMD_SETEVENTMESSAGES, body)
        if response == self.CMD_RESPONSE_NAK:
            self.log("NAK response from panel")
            return False
        elif response != self.CMD_RESPONSE_ACK:
            self.log("unexpected ack payload: "+hex(ord(response)))
            return False
        return True

    def log(self, string):
        timestamp = time.strftime("%Y-%m-%d %X")
        print(timestamp + ": " + string)

    def sendcommand(self, cmd, body):
        if body:
            body = cmd+body
        else:
            body = cmd
        self.sendcommandbody(body)
        retries = 3
        while retries > 0:
            retries -= 1
            try:
                response=self.recvresponse()
                break
            except socket.timeout:
                # FIXME: this maybe isn't quite right as if we get multiple
                # events from the panel that will delay us resending until
                # we don't get any events for 2 second
                self.log("Timeout waiting for response, resending last command")
                # NB: sequence number will be the same as last attempt
                self.s.send(self.last_command)

        commandid,payload = response[0],response[1:]
        if commandid != cmd:
            if commandid == self.CMD_LOGIN and payload[0] == self.CMD_RESPONSE_NAK:
                self.log("Received 'Log on NAK' from panel - session has timed out and needs to be restarted")
                return None
            self.log("Got response for wrong command id: Expected "+hex(ord(cmd))+", got "+hex(ord(commandid)))
            self.log("Payload: "+self.hexstr(payload))
            return None
        return payload

    def get_date_time(self):
        datetimeresp = self.sendcommand(self.CMD_GETDATETIME, None)
        if datetimeresp == None:
            return None
        if len(datetimeresp) < 6:
            self.log("GETDATETIME: response too short")
            self.log("Payload: "+self.hexstr(datetimeresp))
            return None
        datetimeresp = bytearray(datetimeresp)
        datetimestr = '20{2:02d}-{1:02d}-{0:02d} {3:02d}:{4:02d}:{5:02d}'.format(*datetimeresp)
        paneltime = datetime.datetime(2000+datetimeresp[2], datetimeresp[1], datetimeresp[0], *datetimeresp[3:])
        seconds = int((paneltime - datetime.datetime.now()).total_seconds())
        diff = ""
        if seconds > 0:
            diff = " (panel is ahead by {:d} seconds)".format(seconds)
        else:
            diff = " (panel is behind by {:d} seconds)".format(-seconds)
        self.log("Panel date/time: " + datetimestr + diff)
        return datetimestr

    def get_lcd_display(self):
        lcddisplay = self.sendcommand(self.CMD_GETLCDDISPLAY, None)
        if lcddisplay == None:
            return None
        if len(lcddisplay) != 32:
            self.log("GETLCDDISPLAY: response wrong length")
            self.log("Payload: "+self.hexstr(lcddisplay))
            return None
        self.log("Panel LCD display: "+lcddisplay)
        return lcddisplay

    def get_log_pointer(self):
        logpointerresp = self.sendcommand(self.CMD_GETLOGPOINTER, None)
        if logpointerresp == None:
            return None
        if len(logpointerresp) != 2:
            self.log("GETLOGPOINTER: response wrong length")
            self.log("Payload: "+self.hexstr(logpointerresp))
            return None
        logpointer = ord(logpointerresp[0]) + (ord(logpointerresp[1])<<8)
        self.log("Log pointer: {:d}".format(logpointer))
        return logpointer

    def get_panel_identification(self):
        panelid = self.sendcommand(self.CMD_GETPANELIDENTIFICATION, None)
        if panelid == None:
            return None
        if len(panelid) != 32:
            self.log("GETPANELIDENTIFICATION: response wrong length")
            self.log("Payload: "+self.hexstr(panelid))
            return None
        self.log("Panel identification: "+panelid)
        return panelid

    def get_zone_details(self, zone):
        details = self.sendcommand(self.CMD_GETZONEDETAILS, chr(zone))
        if details == None:
            return None
        if len(details) == 34:
            zonetype = ord(details[0])
            areabitmap = ord(details[1])
            zonetext = details[2:]
        elif len(details) == 35:
            zonetype, areabitmap, zonetext = ord(details[0]), ord(details[1]) + (ord(details[2])<<8), details[3:]
            zonetype = ord(details[0])
            areabitmap = ord(details[1]) + (ord(details[2])<<8)
            zonetext = details[3:]
        elif len(details) == 41:
            zonetype = ord(details[0])
            areabitmap = ord(details[1]) + (ord(details[2])<<8) + (ord(details[3])<<16) + (ord(details[4])<<24) + \
              (ord(details[5])<<32) + (ord(details[6])<<40) + (ord(details[7])<<48) + (ord(details[8])<<56)
            zonetext = details[9:]
        else:
            self.log("GETZONEDETAILS: response wrong length")
            self.log("Payload: "+self.hexstr(details))
            return None

        zonetext = zonetext.replace("\x00", " ")
        zonetext = re.sub(r'\W+', ' ', zonetext)
        zonetext = zonetext.strip()
        if zonetype != self.ZONETYPE_UNUSED:
            self.log("zone {:d} zone type {:d} area bitmap {:x} text '{}'".
                format(zone, zonetype, areabitmap, zonetext))
        return (zonetype, areabitmap, zonetext)

    def get_system_power(self):
        details = self.sendcommand(self.CMD_GETSYSTEMPOWER, None)
        if details == None:
            return None
        if len(details) != 5:
            self.log("GETSYSTEMPOWER: response wrong length")
            self.log("Payload: "+self.hexstr(details))
            return None
        ref_v = ord(details[0])
        sys_v = ord(details[1])
        bat_v = ord(details[2])
        sys_i = ord(details[3])
        bat_i = ord(details[4])

        system_voltage = 13.7 + ((sys_v - ref_v) * 0.070)
        battery_voltage = 13.7 + ((bat_v - ref_v) * 0.070)

        system_current = sys_i * 9
        battery_current = bat_i * 9

        self.log("System power: system voltage {:f} battery voltage {:f} system current {:d} battery current {:d}".
            format(system_voltage, battery_voltage, system_current, battery_current))
        return (system_voltage, battery_voltage, system_current, battery_current)

    def get_all_zones(self):
        idstr = tc.get_panel_identification()
        panel_type,num_of_zones,something,firmware_version = idstr.split()
        num_of_zones = int(num_of_zones)
        for zone in range(1, num_of_zones + 1):
            # FIXME: if an event arrives whilst we're waiting for a response, it seems the panel doesn't reply, so we need to timeout and send again
            zonetype, areabitmap, zonetext = tc.get_zone_details(zone)
            zonedata = {
              'type' : zonetype,
              'areas' : areabitmap,
              'text' : zonetext
            }
            self.zone[zone] = zonedata

    def event_loop(self):
        while True:
            try:
                global garage_pir_activated_at
                if garage_pir_activated_at > 0:
                    active_for = time.time() - garage_pir_activated_at
                    self.log("Garage PIR active for {:.1f} minutes".format(active_for/60))
                    if active_for > 4*60:
                        garage_pir_activated_at=time.time()
                        os.system("./garage-pir.sh 'still active'")
                payload = tc.recvresponse()
        
            except socket.timeout:
                # FIXME: this should be in recvresponse, otherwise we
                # won't send if we get a continual stream of events from the
                # panels
                assert self.last_command_time > 0
                time_since_last_command = time.time() - self.last_command_time
                if time_since_last_command > 30:
                    # send any message to reset the panel's 60 second timeout
                    result = tc.get_date_time()
                    if result == None:
                        self.log("'get date time' failed; exiting")
                        # TODO could just reconnect
                        sys.exit(1)

    def decode_message_to_text(self, payload):
        msg_type,payload = payload[0],payload[1:]
        if msg_type == tc.MSG_DEBUG:
            return "Debug message: "+tc.hexstr(payload)
        elif msg_type == tc.MSG_ZONEEVENT:
            if len(payload) == 2:
                zone_number = ord(payload[0])
                zone_bitmap = ord(payload[1])
            elif len(payload) == 3:
                zone_number = ord(payload[0])+(ord(payload[1])<<8)
                zone_bitmap = ord(payload[2])
            else:
                return "unknown zone event message payload length"
            zone_state = zone_bitmap & 0x3
            zone_str = ["secure","active","tamper","short"][zone_bitmap & 0x3]
            if zone_bitmap & (1 << 2):
                zone_str += ", fault"
            if zone_bitmap & (1 << 3):
                zone_str += ", failed test"
            if zone_bitmap & (1 << 4):
                zone_str += ", alarmed"
            if zone_bitmap & (1 << 5):
                zone_str += ", manual bypassed"
            if zone_bitmap & (1 << 6):
                zone_str += ", auto bypassed"
            if zone_bitmap & (1 << 7):
                zone_str += ", zone masked"
            zone_text = self.zone[zone_number]['text']
            return "Zone event message: zone {:d} '{}' {}".\
              format(zone_number, zone_text, zone_str)
        elif msg_type == tc.MSG_AREAEVENT:
            area_number = ord(payload[0])
            area_state = ord(payload[1])
            area_state_str = ["disarmed", "in exit", "in entry", "armed", "part armed", "in alarm"][area_state]
            return "Area event message: area "+str(area_number)+" "+area_state_str
        elif msg_type == tc.MSG_OUTPUTEVENT:
            locations = ["Panel outputs",
            "Digi outputs",
            "Digi Channel low 8",
            "Digi Channel high 8",
            "Redcare outputs",
            "Custom outputs 1",
            "Custom outputs 2",
            "Custom outputs 3",
            "Custom outputs 4",
            "X-10 outputs"]
            output_location = ord(payload[0])
            output_state = ord(payload[1])
            if output_location < len(locations):
                output_name = locations[output_location]
            elif (output_location & 0xf) == 0:
                output_name = "Network {:d} keypad outputs".\
                  format(output_location >> 4, output_location & 0xf)
            else:
                output_name = "Network {:d} expander {:d} outputs".\
                  format(output_location >> 4, output_location & 0xf)
            return "Output event message: location {:d}['{}'] now 0x{:02x}".\
              format(output_location, output_name, output_state)
        elif msg_type == tc.MSG_USEREVENT:
            user_number = ord(payload[0])
            user_state = ord(payload[1])
            user_state_str = ["code", "tag", "code+tag"][user_state]
            return "User event message: logon by user {:d} {}".\
              format(user_number, user_state_str)
        elif msg_type == tc.MSG_LOGEVENT:
            if len(payload) == 8:
                parameter = ord(payload[2])
                areas = ord(payload[3])
                timestamp = payload[4:8]
            elif len(payload) == 9:
                # Premier 168 - longer message as 16 bits of area info
                parameter = ord(payload[2])
                areas = ord(payload[3])+(ord(payload[8])<<8)
                timestamp = payload[4:8]
            elif len(payload) == 10:
                # Premier 640
                # I'm unsure if this is correct and I don't have a panel to test with
                parameter = ord(payload[2])+(ord(payload[3])<<8)
                areas = ord(payload[4])+(ord(payload[5])<<8)
                timestamp = payload[6:10]
            else:
                return "unknown log event message payload length"

            event_type = ord(payload[0])
            group_type = ord(payload[1])
            timestamp_int = ord(timestamp[0]) + (ord(timestamp[1])<<8) + (ord(timestamp[2])<<16) + (ord(timestamp[3])<<24)
            seconds = timestamp_int & 63
            minutes = (timestamp_int >> 6) & 63
            month = (timestamp_int >> 12) & 15
            hours = (timestamp_int >> 16) & 31
            day = (timestamp_int >> 21) & 31
            year = 2000 + ((timestamp_int >> 26) & 63)
            timestamp_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(year, month, day, hours, minutes, seconds)

            if event_type in self.log_event_types:
                event_str = self.log_event_types[event_type]
            else:
                event_str = "Unknown log event type {:d}".format(event_type)

            return "Log event message: {} {} group type: {:d}  parameter: {:d}   areas: {:d}  hex: {} ".format(timestamp_str, event_str, group_type, parameter, areas, tc.hexstr(payload))
        else:
            return "unknown message type "+str(ord(msg_type))+": "+tc.hexstr(payload)

def message_handler(payload):
    tc.log(tc.decode_message_to_text(payload))
    msg_type,payload = payload[0],payload[1:]
    if msg_type == tc.MSG_ZONEEVENT:
        zone_number = ord(payload[0])
        zone_bitmap = ord(payload[1])
        zone_state = zone_bitmap & 0x3
        if zone_number == 73:
            global garage_pir_activated_at
            if zone_state == 1:
                tc.log("Garage PIR activated; running script")
                garage_pir_activated_at=time.time()
                os.system("./garage-pir.sh 'activated'")
            else:
                tc.log("Garage PIR cleared")
                garage_pir_activated_at=0

# disable buffering to stdout when it's redirected to a file/pipe
# This makes sure any events appear immediately in the file/pipe,
# instead of being queued until there is a full buffer's worth.
class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def writelines(self, datas):
       self.stream.writelines(datas)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)

garage_pir_activated_at=0

if __name__ == '__main__':
    texhost = '192.168.1.9'
    port = 10001
    udlpassword = '1234'


    sys.stdout = Unbuffered(sys.stdout)
    tc = TexecomConnect(texhost, port, message_handler)
    tc.connect()
    if not tc.login(udlpassword):
        print("Login failed - udl password incorrect or pre-v4 panel, exiting.")
        sys.exit(1)
    print("login successful")
    if not tc.set_event_messages():
        print("Set event messages failed, exiting.")
        sys.exit(1)
    tc.get_date_time()
    tc.get_system_power()
    tc.get_log_pointer()
    tc.get_all_zones()
    print("Got all zones; waiting for events")
    tc.event_loop()
