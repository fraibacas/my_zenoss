#!/opt/zenoss/bin/python
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
dmd = ZenScriptBase(connect=True).dmd
Organizers = dmd.Events.getSubOrganizers()
Organizers.insert(0,dmd.Events)
for ec in Organizers:
    if ec:
            if ec.transform:
                print "= %s ===" % ec.getOrganizerName()
                print ec.transform
                print
            for i in ec.instances():
                if i.transform:
                    print "= %s/%s ===" % (ec.getOrganizerName(), i.id)
                    print i.transform
                    print
