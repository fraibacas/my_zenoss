
from Products.Zuul.routers.device import DeviceRouter
import random
import time
def delete_vSphere_components():
	router = DeviceRouter(dmd)
	devices = dmd.Devices.vSphere.devices()
	for dev in devices:
		components = dev.componentSearch()
		if components:
			n_components_to_delete = random.randint(1, min(40, len(components)))
			print "Removing {0} components from {1}".format(n_components_to_delete, dev)
			for i in range(n_components_to_delete):
				components = dev.componentSearch()
				if components:
					component = components[random.randint(0,len(components)-1)].getPath()
					print "Deleting {0}".format(component)
					router.deleteComponents(uids=[component], hashcheck=None)
			commit()
			time.sleep(5)
		else:
			print "No components found for {0}".format(dev)
delete_vSphere_components()