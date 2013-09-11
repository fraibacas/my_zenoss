#!/usr/bin/env python

import os
import pwd
import sys
import getopt
import re
import time
import datetime

user_name = pwd.getpwuid(os.getuid())[0]
if user_name != "zenoss":
    print "Error:  This script needs to be run as user \'zenoss\'"
    sys.exit()

import Globals
import Acquisition

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from transaction import commit
from Products.Zuul import getFacade


# ZenScriptBase will process sys.argv so grab our paramaters first and save off into "sys_argv"
sys_argv=sys.argv
sys.argv=[sys.argv[0]]
dmd = ZenScriptBase(connect=True).dmd
zep = getFacade('zep')


############################################################################################################
# def usage
############################################################################################################

def usage():
    print """Usage: events_add [options]

        -c, --class <class name>                    event_class (default of /Status/Ping)
        -d, --details <details>                     details (default of None)
        -f, --from <device name>                    from what resource (device)
        -p, --priority <priority num>               priority (default of 1)
        -q, --production_state <production_state>   production_state (default of 1000)
        -r, --rate <per minute rate>                per minute event rate
        -s, --severity <severity num>               severity (default of 5)
        -u, --duplicate <duplicate num>             duplicate number (default is no duplicate)
        -m, --summary <summary>                     summary text for event 
        -h, --help                                  display this help and exit
        <num_events_to_send>

    Example:
        events_add --priority 1 --severity 3 500
        events_add --class /Cmd/Fail 10
    """

    sys.exit(1)


########################################################################################
# class Ddict
########################################################################################

class Ddict(dict):
    def __init__(self, default=None):
        self.default = default

    def __getitem__(self, key):
        if not self.has_key(key):
            self[key] = self.default()
        return dict.__getitem__(self, key)
                                                                                                                    

########################################################################################
# def add_comma
########################################################################################

def add_comma(number):
    
    try:
        number_int = int(number)
    except:
        return number

    s = '%d' % number_int
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
  
    return s + ','.join(reversed(groups))


########################################################################################
# def get_system_info
########################################################################################

def get_system_info(system_info):

    sw_collectors = sorted(dmd.Monitors.getPerformanceMonitorNames())

    sw_hubs = []
    hw_hubs = []

    hw_collectors = []

    for sw_collector in sw_collectors:
        monitor = dmd.Monitors.getPerformanceMonitor(sw_collector)
        hub = monitor.hub()
        sw_hub = hub.id

        # sw_collector
        if sw_hub not in sw_hubs:
            sw_hubs.append(sw_hub)

        # hw hubs
        hw_hub=getattr(hub, 'hostname', '')
        if hw_hub not in hw_hubs:
            hw_hubs.append(hw_hub)

        # hw collectors
        hw_collector=getattr(monitor, 'hostname', '')
        if hw_collector not in hw_collectors:
            hw_collectors.append(hw_collector)
        system_info["hw_collector_to_sw_hub"][hw_collector] = sw_hub

        system_info["sw_collector_to_hw_collector"][sw_collector] = hw_collector


    system_info["hw_hubs"] = hw_hubs
    system_info["sw_hubs"] = sw_hubs
    system_info["hw_collectors"] = hw_collectors
    system_info["sw_collectors"] = sw_collectors


########################################################################################
# def get_device_info
########################################################################################

def get_device_info(device_info):

    system_info = Ddict(dict)

    get_system_info(system_info)
    device_info["hw_collectors"] = system_info["hw_collectors"]
    device_info["sw_collectors"] = system_info["sw_collectors"]

    for hw_collector in system_info["hw_collectors"]:
        device_info["hw_collector_num_devices"][hw_collector] = 0
        device_info["hw_collector_num_devices_modeled"][hw_collector] = 0
        device_info["hw_collector_num_devices_remodeled"][hw_collector] = 0

    for sw_collector in system_info["sw_collectors"]:
        device_info["sw_collector_to_hw_collector"][sw_collector] = system_info["sw_collector_to_hw_collector"][sw_collector]

        device_info["sw_collector_num_devices"][sw_collector] = 0
        device_info["sw_collector_num_devices_modeled"][sw_collector] = 0
        device_info["sw_collector_num_devices_remodeled"][sw_collector] = 0


    device_ips = []
    device_info["num_devices"] = 0
    device_info["num_devices_not_modeled"] = 0
    device_info["num_devices_modeled_this_iteration"] = 0

    for dev in dmd.Devices.getSubDevices():

        device_ip = dev.getManageIp()
        if device_ip == "":
            continue
        device_ips.append(device_ip)
        device_id = dev.id
        model_time = dev.getSnmpLastCollectionString()
        sw_collector = dev.getPerformanceServerName()
        device_type = dev.getDeviceClassName()

        device_info[device_ip]["device_id"] = device_id
        device_info[device_ip]["model_time"] = model_time
        device_info[device_ip]["sw_collector"] = sw_collector
        device_info[device_ip]["device_type"] = device_type

        device_info["num_devices"] += 1

        device_is_modeled = 1
        if dev.getSnmpLastCollectionString() == "Not Modeled":
            device_info["num_devices_not_modeled"] += 1
            device_is_modeled = 0

        sw_collector = dev.getPerformanceServerName()
        device_info["sw_collector_num_devices"][sw_collector] += 1
        if device_is_modeled:
            device_info["sw_collector_num_devices_modeled"][sw_collector] += 1
        hw_collector = system_info["sw_collector_to_hw_collector"][sw_collector]
        device_info["hw_collector_num_devices"][hw_collector] += 1
        if device_is_modeled:
            device_info["hw_collector_num_devices_modeled"][hw_collector] += 1

    device_info["device_ips"] = device_ips

    device_info["num_devices_modeled"] = device_info["num_devices"] - device_info["num_devices_not_modeled"]


############################################################################################################
# def sendEvents
############################################################################################################

def sendEvents(count, dev, sev, event_class, production_state, priority, details, duplicate, requested_summary):

    from uuid import uuid4
    from Products.ZenMessaging.queuemessaging.publisher import EventPublisher
    from Products.ZenEvents.Event import buildEventFromDict
    publisher = EventPublisher()

    if duplicate > 0:
        if requested_summary == "not_set": 
            summary = "sent from tool events_add -- duplicate set of: %s (%s)" % (duplicate, uuid4())
        else:
            summary = requested_summary

    for x in xrange(count):
   
        if duplicate == 0:
            if requested_summary == "not_set": 
                summary = "sent from tool events_add: %s (%s)" % (x, uuid4())
            else:
                summary = requested_summary

        event = {
            "evid":       str(uuid4()),
            "device":     dev,
            "severity":   sev,
            "eventClass": event_class,   
            "summary":    "%s" % (summary),
            "zenoss.device.production_state": production_state,
            "zenoss.device.priority": priority,
        }
        if details:
            event.update(details)
        publisher.publish(buildEventFromDict(event))


        #curl -u "admin:zenoss" -X POST -H "Content-Type:application/json" -d "{\"action\":\"EventsRouter\", \"method\":\"add_event\", \"data\":[{\"summary\":\"test55\", \"device\":\"test-rhel6.zenoss.loc\", \"component\":\"\", \"severity\":\"Critical\", \"evclasskey\":\"\", \"evclass\":\"/App\"}], \"type\":\"rpc\", \"tid\":1}" "jwhitworth-tb3.zenoss.loc:8080/zport/dmd/evconsole_router"

    publisher.close()



############################################################################################################
# Main
############################################################################################################

def main():

    try:
        opts, extra_params = getopt.getopt(sys_argv[1:], "c:d:f:hs:p:q:r:u:m:", ["class=", "details=", "from=", "severity=", "priority=", "production_state=", "rate=", "duplicate=", "summary=", "help"])
    except getopt.GetoptError, err:
        print str(err)
        usage()

    event_class = "/Status/Ping"
    details = None
    severity = 5 
    priority = 1 
    production_state = 1000
    from_which_device = "default"
    per_minute_rate = 0
    duplicate = 0
    summary = "not_set"

    for o,p in opts:
        if o in ['-c','--class']:
            event_class = p
        elif o in ['-d','--details']:
            details = p
        elif o in ['-f','--from']:
            from_which_device = p
        elif o in ['-s','--severity']:
            severity = p
        elif o in ['-p','--priority']:
            priority = p
        elif o in ['-q','--production_state']:
            production_state = p
        elif o in ['-r','--rate']:
            per_minute_rate = int(p)
        elif o in ['-u','--duplicate']:
            duplicate = int(p)
        elif o in ['-m','--summary']:
            summary = p
        elif o in ['-h','--help']:
            usage()

    if len(extra_params) == 0:
        print "\nError: number of events to send is required.\n"
        usage()

    num_events_to_send = int(extra_params[0])

    if duplicate > num_events_to_send:
        print "Error:  number of duplicates is greater than number of events to send."
        sys.exit()

    start = time.time()
    device_info = Ddict(dict)

    if from_which_device == "default":
        get_device_info(device_info)
    else:
        device_ip = from_which_device
        device_info["device_ips"] = [device_ip]
        device_info[device_ip]["device_id"] = device_ip


    if len(device_info["device_ips"]) == 0:
        device_ip = "localhost.localdomain"
        device_info["device_ips"] = [device_ip]
        device_info[device_ip]["device_id"] = device_ip


    num_events_sent = 0
    all_done = 0
    
    start_time = 0
    duration = 0
    counter = 0
    
    if duplicate == 0:
        num_to_send_per_iteration = 1
    else:
        num_to_send_per_iteration = duplicate

    while 1:
        for device_ip in device_info["device_ips"]:
            device_id = device_info[device_ip]["device_id"]
            
            if (per_minute_rate > 0) and (counter == 0) :
                start_time = time.time()

            sendEvents(num_to_send_per_iteration, device_id, severity, event_class, production_state, priority, details, duplicate, summary)

            num_events_sent += num_to_send_per_iteration
          
            #print "num_to_send_per_iteration: %s" % (num_to_send_per_iteration)
            #print "num_events_sent: %s" % (num_events_sent)

            if (per_minute_rate > 0):
                counter += num_to_send_per_iteration
                duration = time.time() - start_time
                if (duration < 60 and counter >= per_minute_rate):
                    time.sleep(60-duration)
                    counter = 0
                    
            if num_events_sent >= num_events_to_send:
                all_done = 1
                break

            if (num_events_sent % 10000) == 0:
                print "Events Sent: %s" % (num_events_sent)

        if all_done:
            break

    if num_events_to_send < len(device_info["device_ips"]):
        unique_devices = num_events_to_send
    else:
        unique_devices = len(device_info["device_ips"])


    execution_time = int(round(time.time() - start))
    print "Events Sent: %s" % (num_events_to_send)
    print "From Unique devices: %s" % (unique_devices)
    print "Duplicate: %s" % (duplicate)
    print "Execution Time: %s seconds" % (execution_time)
    print ""


main()
