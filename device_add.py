#!/usr/bin/env python

import os
import pwd
import sys
import getopt
import datetime

user_name = pwd.getpwuid(os.getuid())[0]
if user_name != "zenoss":
    print "Error:  This script needs to be run as user \'zenoss\'"
    sys.exit()

import Globals
import re
import Acquisition
import time
import datetime

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from transaction import commit, abort
from ZODB.transact import transact
from Products.Zuul import getFacade


# ZenScriptBase will process sys.argv so grab our paramaters first and save off into "sys_argv"
sys_argv=sys.argv
sys.argv=[sys.argv[0]]
dmd = ZenScriptBase(connect=True).dmd
#zep = getFacade('zep')


sw_collectors = sorted(dmd.Monitors.getPerformanceMonitorNames())
#for sw_collector in sw_collectors:
#    print "sw_collector: %s" % (sw_collector)


##################################################################################################
# usage
##################################################################################################

def usage():
    print """Usage: device_add [options]

Options:
    -c, --class <class>          device class (default is /Ping)
    -l, --collector <collector>  collector (default is non-localhost, but will use localhost if that is all that is available)
    -n, --number <number>        number of devices to create (will increment ip from starting value)
    -m, --model                  model_device (default is false)
    -h, --help                   display this help
    <device ip> <device ip>

    Example:
        device_add 10.171.100.7
        device_add --class /Ping 10.171.100.90
        device_add --collector col1a --class /Network/Cisco 10.171.100.46
        device_add --model --class /Network/Cisco/6500 10.171.100.14
        device_add --model --class /Server/Linux 10.171.101.59
        device_add --model --class /Network/Cisco 10.171.100.40
    """

    sys.exit(1)


##################################################################################################
# createDevices
##################################################################################################

def createDevices(num_devices, collector, device_class, managed_ip, model_device):

    if device_class == "default":
        #deviceClass = dmd.Devices.Discovered
        deviceClass = dmd.Devices.Ping
    else:
        #deviceClass = dmd.Devices.Server.Linux
        #deviceClass = dmd.Devices.Network.Cisco
        device_class_path = "/zport/dmd/Devices" + device_class
        deviceClass = dmd.unrestrictedTraverse(device_class_path)


    if collector != "default":
        num_collectors = 1
        available_collectors = [collector]
    else:
        if len(sw_collectors) == 1:
            available_collectors = ["localhost"]
        else:
            available_collectors = []
            for sw_collector in sw_collectors:
                if sw_collector != "localhost":
                    available_collectors.append(sw_collector)

        num_collectors = len(available_collectors)

    line_list = managed_ip.split('.')
    first_octet = line_list[0]
    second_octet = line_list[1]
    third_octet = int(line_list[2])
    forth_octet = int(line_list[3])

    created = 0
    failed = 0
    start = 0
    collector_index = 0
    forth_octet -= 1
    for i in range(num_devices):
        forth_octet += 1
        if forth_octet == 255:
            forth_octet = 1
            third_octet += 1
        ip_address = "%s.%s.%s.%s" % (first_octet, second_octet, third_octet, forth_octet)
        ip_address_underscore = re.sub("\.", "_", ip_address)
        device_name = "device_" + ip_address_underscore

        #dev.setPerformanceMonitor('localhost')
        collector = available_collectors[collector_index]   

        if num_devices < 100:    
            print "Creating device: %s (%s):   %s  %s" % (device_name, ip_address, collector, deviceClass)
            
        if createDevice(deviceClass, device_name, ip_address, collector, model_device):
            collector_index += 1
            if collector_index == num_collectors:
                collector_index = 0
            created += 1
        else: 
            failed += 1

    return(created, failed)


##################################################################################################
# create a device
##################################################################################################
@transact
def createDevice(deviceClass, device_name, ip_address, collector, model_device):
    success = 1

    try:
        print "deviceClass: %s" % (deviceClass)
        dev = deviceClass.createInstance(device_name)
        #dev = dmd.Devices.Server.Linux.createInstance(device_name)
        dev.setPerformanceMonitor(collector)
        dev.setManageIp(ip_address)
        if model_device:
            dev.collectDevice()
    except:
        print "Error creating device: %s (%s):   %s  %s" % (device_name, ip_address, collector, deviceClass)
        success = 0
        abort()
    
    return success


##################################################################################################
# main
##################################################################################################

def main():

    try:
        opts, extra_params = getopt.getopt(sys_argv[1:], "c:n:l:mh", ["class=", "collector=", "number=", "model", "help"])
    except getopt.GetoptError, err:
        print str(err)
        usage()

    device_class = "default"
    num_devices = 1
    model_device = False
    collector = "default"

    for o,p in opts:
        if o in ['-c','--class']:
            device_class = p
        if o in ['-m','--model']:
            model_device = True    
        if o in ['-n','--number']:
            num_devices = int(p)
        if o in ['-l','--collector']:
            collector = p  
        elif o in ['-h','--help']:
            usage()

    managed_ips = extra_params

    if len(extra_params) == 0:
        print "\nError: list of device ip's is required.\n"
        usage()

    if num_devices > 1 and len(extra_params) > 1:
        print "\nError: Cannot use -n > 1 with more than one managed ip.\n"
        usage()

    if collector != "default":
        found_it = 0
        for available_collector in sw_collectors:
            if collector == available_collector:
                found_it = 1
        if not found_it:
            print "\nError: collector \'%s\' is not on the system" % (collector)
            print "The following are the available collectors on the system:"
            for sw_collector in sw_collectors:
                print "  %s" % (sw_collector)
            sys.exit(1)



    total_created = 0
    total_failed = 0
    secs_since_1970_1 = int(round(time.time()))
    for managed_ip in managed_ips:
        (created, failed) = createDevices(num_devices, collector, device_class, managed_ip, model_device)
        total_created += created
        total_failed += failed

    secs_since_1970_2 = int(round(time.time()))
    execution_time = secs_since_1970_2 - secs_since_1970_1

    print "\n"
    print "Execution Time: %s seconds" % (execution_time)
    print "Total Created: %s" % (total_created)
    print "Total Failed: %s" % (total_failed)


if __name__ == "__main__":
    main()

