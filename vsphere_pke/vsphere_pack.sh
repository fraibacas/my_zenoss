#!/bin/bash
/opt/zenoss/bin/zenossdbpack -e session -t
zendmd --script=vsphere_refs.py
echo ''
/opt/zenoss/bin/zenossdbpack -e session
echo ''
zendmd --script=vsphere_refs.py 
