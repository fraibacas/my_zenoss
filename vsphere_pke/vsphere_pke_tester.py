#!/opt/zenoss/bin/zendmd

from Products.Zuul.routers.device import DeviceRouter

import argparse
import multiprocessing
import os
import random
import shlex
from subprocess import Popen, PIPE
import sys
import time
from ZODB.POSException import POSKeyError

class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class VSphereHelper(object):
	def get_vsphere_devices(self):
			return dmd.Devices.vSphere.devices()


class RemoveComponentsTask(object):

	def __init__(self):
		self.vsphere_helper = VSphereHelper()
		self.name = 'RemoveComponentsTask'

	def get_vsphere_devices(self):
		return dmd.Devices.vSphere.devices()

	def delete_random_vsphere_components(self):
		sync()
		router = DeviceRouter(dmd)
		devices = self.vsphere_helper.get_vsphere_devices()
		for dev in devices:
			sync()
			try:
				components = dev.componentSearch()
				if components:
					n_components_to_delete = random.randint(1, min(10, len(components)))
					print "{0}Removing {1} components from {2}{3}".format(BColors.OKBLUE, n_components_to_delete, dev, BColors.ENDC)
					for i in range(n_components_to_delete):
						components = dev.componentSearch()
						if components:
							component = components[random.randint(0,len(components)-1)].getPath()
							#print "Deleting {0}".format(component)
							router.deleteComponents(uids=[component], hashcheck=None)
					commit()
				else:
					print "{0}No components found for {1}{2}".format(BColors.WARNING, dev, BColors.ENDC)
			except POSKeyError:
				print "{0}PKE found for device {1}{2}".format(BColors.FAIL, dev, BColors.ENDC)

	def run(self):
		self.delete_random_vsphere_components()

class ModelerTask(object):
	""" Models all vSphere devices """
	def __init__(self):
		self.vsphere_helper = VSphereHelper()
		self.name = 'ModelerTask'

	def model_device(self, dev):
		os.system('zenmodeler run -d {0} &> /dev/null'.format(dev))
		"""cmd = 'zenmodeler run -d {0}'.format(dev)
		process = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
		(output, err) = process.communicate()
		exit_code = process.wait()
		return err # pack output is written to stderr"""

	def run(self):
		sync()
		for dev in self.vsphere_helper.get_vsphere_devices():
			print "{0}Modeling {1}.{2}".format(BColors.OKBLUE, dev, BColors.ENDC)
			self.model_device(dev.id)	
			sync()

class PackTask(object):
	""" Runs zenossdbpack """
	def __init__(self):
		self.name = 'PackTask'

	def run(self):
		pack_cmd = '/opt/zenoss/bin/zenossdbpack -e session'
		process = Popen(shlex.split(pack_cmd), stdout=PIPE, stderr=PIPE)
		(output, err) = process.communicate()
		exit_code = process.wait()
		return err # pack output is written to stderr

def log_exception(text):
	print "{0}{1}{2}".format(BColors.FAIL, text, BColors.ENDC)

def run_delete_components():
	""" """
	task = RemoveComponentsTask()
	counter = 0
	error_counter = 0
	while True:
		try:
			task.run()
			counter = counter + 1
			time.sleep(20)
		except KeyboardInterrupt:
			print "{0}{1} was executed {2}{3}".format(BColors.OKBLUE, task.name, counter, BColors.ENDC)
			break #raise
		except Exception as e:
			log_exception('Exception executing {0}: {1}'.format(task.name, e))
			if error_counter == 5:
				error_counter = 0
				log_exception('Restarting Zenoss.....')
				os.system('zenoss restart &> /dev/null')
				log_exception('Zenoss restarted!')
			else:
				error_counter = error_counter + 1
				time.sleep(random.randint(30, 60))

def run_modeler():
	""" """
	task = ModelerTask()
	counter = 0
	error_counter = 0
	while True:
		try:
			task.run()
			counter = counter + 1
			error_counter = 0
			time.sleep(60)
		except KeyboardInterrupt:
			print "{0}{1} was executed {2}{3}".format(BColors.OKBLUE, task.name, counter, BColors.ENDC)
			break #raise
		except Exception as e:
			log_exception('Exception executing {0}: {1}'.format(task.name, e))
			if error_counter == 5:
				log_exception('Restarting zenmodeler...')
				os.system('zenmodeler restart')
				log_exception('Zenmodeler restarted')
				error_counter = 0
			else:
				error_counter = error_counter + 1
				time.sleep(random.randint(30, 60))

def run_pack():
	task = PackTask()
	counter = 0
	while True:
		try:	
			task.run()
			counter = counter + 1
			time.sleep(300)
		except KeyboardInterrupt:
			print "{0}{1} was executed {2}{3}".format(BColors.OKBLUE, task.name, counter, BColors.ENDC)
			break
		except Exception as e:
			log_exception('Exception executing {0}: {1}'.format(task.name, e))
			time.sleep(random.randint(30, 90))

def main(skip_pack=False):
	try:
		delete_task = multiprocessing.Process(target=run_delete_components)
		modeler_task = multiprocessing.Process(target=run_modeler)

		# Start modeler and component remover tasks
		delete_task.start()
		time.sleep(30)
		modeler_task.start()
		
		# In case we want to run pack as a separate process
		#pack_task = multiprocessing.Process(target=run_pack)
		#pack_task.start()

		time.sleep(60)
		counter = 0
		pack_task = PackTask()
		while True:
			try:
				if not skip_pack:
					output = pack_task.run()
					counter = counter + 1
					print output
					with open('/opt/zenoss/log/pack.log', 'a') as file:
						file.write(output)
					if 'FAILED' in output:
						print '{0}PKE situation detected after {1} runs of zodbpack. Check zodbscan{2}'.format(BColors.FAIL, counter, BColors.ENDC)
				time.sleep(300)
			except KeyboardInterrupt:
				print "{0}{1} was executed {2}{3}".format(BColors.OKBLUE, pack_task.name, counter, BColors.ENDC)
				raise
		for task in [delete_task, modeler_task]:
			if task:
				task.terminate()
	except:
		for task in [delete_task, modeler_task]:
			try:
				task.terminate()
			except:
				print "Exception stopping tasks"

if __name__ == '__main__':
	main(skip_pack=False)
