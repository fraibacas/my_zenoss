
from common import BColors
from results import ResultProcessor
from zenoss_client import ZenossClient

import multiprocessing
import random
import time

class TestHarnessTask(object):

	def __init__(self, task_name, zenoss_url, user, password, context={}):
		""" """
		self.task_name = task_name
		self.zenoss_url = zenoss_url
		self.context = context
		self.user = user
		self.password = password
		self.summary = context.get('summary', True)
		self.zenoss_client = ZenossClient(zenoss_url, user, password)

	def init_task(self):
		pass

	def pre_run_hook(self):
		pass

	def run_task(self):
		raise NotImplementedError

	def post_run_hook(self, result):
		return result

	def _run(self):
		result = {}
		result["success"] = False
		result["results"] = -1
		result["data"] = self.context.get('request_info')
		result["worker"] = self.task_name

		start = time.time()
		try:
			response = self.run_task()
		except KeyboardInterrupt as e:
			raise e
		except Exception as ex:
			print ex
			response = None
		end = time.time()
		result["start"] = start
		result["elapsed"] = end-start

		if response:
			if response.get('success'):
				if response.get('print_message'):
					print "\t{0} => Request took {1} seconds. {2}".format(self.task_name, end-start, response.get('print_message'))
				else:
					print "\t{0} => Request took {1} seconds and returned {2} results. {3}".format(self.task_name, end-start, response['totalCount'], result['data'])
				result["results"] = response['totalCount']
				result["success"] = True
			else:
				print "\t{0} => {1}Request failed{2}. Request time: {3}. Request info: {4}".format(self.task_name, BColors.FAIL, BColors.ENDC, end-start, result['data'])	
		else:
			print "\t{0} => {1}Request failed{2}. Request time: {3}".format(self.task_name, BColors.FAIL, BColors.ENDC, end-start)

		return result

	def run(self, times=1):
		""" run the task 'times' times """
		results = []
		self.init_task()
		for request in range(times):
			try:
				self.pre_run_hook()
				result = self._run()
				result = self.post_run_hook(result)
				results.append(result)
			except KeyboardInterrupt:
				break
			except Exception:
				pass
		return results

class SampleBasedFilterTask(TestHarnessTask):

	class SampleBasedFilterRequestGenerator(object):

		KEYS = [ 'incident', 'user', 'device', 'event_class' ]

		def __init__(self, sample_data):
			self.sample_data = sample_data
			for key in self.KEYS:
				if key not in self.sample_data.keys():
					self.sample_data[key] = []

		def validate(self):
			# We need some sample data to generate queries
			return self.sample_data.get('incident') or self.sample_data.get('user') or self.sample_data.get('device') or self.sample_data.get('event_class')

		def generate_random_request(self, archive=True):
			request_info = {}
			field_to_filter = random.choice(self.KEYS)
			value_to_filter = random.choice(self.sample_data[field_to_filter])
			request_info[field_to_filter] = value_to_filter
			return request_info

	def init_task(self):
		# retrieve sample data and create the requests generator
		sample_data = self.context['sample_data']
		self.context['request_generator'] = SampleBasedFilterTask.SampleBasedFilterRequestGenerator(sample_data)

	def run_task(self):
		request_generator = self.context['request_generator']
		request_info = request_generator.generate_random_request()
		self.context['request_info'] = request_info
		return self.zenoss_client.send_event_filter_request(request_info, archive=(not self.summary))

class RandomActionTask(TestHarnessTask):

	def init_task(self):
		# Get number of events
		response = self.zenoss_client.send_event_filter_request()

		self.context['total_count'] = 0
		self.context['total_pages'] = 0
		if response.get('success'):
			self.context['total_count'] = response.get('totalCount')
			self.context['total_pages'] = max(int(response.get('totalCount')/200), 1)

	def pre_run_hook(self):
		# lets randomly pick an event
		radom_page = random.randint(1, self.context['total_pages'])
		self.context['radom_page'] = radom_page
		self.context['success'] = False
		response = self.zenoss_client.send_event_filter_request(request_info={'page': radom_page})
		if response.get('success'):
			events = response.get('events')
			if events:
				random_event = random.choice(events)
				self.context['success'] = True
				self.context['event'] = random_event
				uuid = random_event.get('evid')
				old_state = random_event.get('eventState')
				if old_state == "New":
					action = random.choice(['ack', 'close'])
				else:
					action = "reopen"
				self.context['request_info'] = {'evid': uuid, 'old_state': old_state, 'action': action}

	def run_task(self):
		# lets perform an action
		response = {}
		response['success'] = False
		response['totalCount'] = 0
		if self.context['success'] and self.context['event']:
			event = self.context['event']
			action = 'ack'
			if self.context.get('request_info') and self.context.get('request_info').get('action'):
				action = self.context.get('request_info').get('action')
			if action == 'ack':
				response = self.zenoss_client.acknowledge_event(event['evid'])
			elif action == 'close':
				response = self.zenoss_client.close_event(event['evid'])
			else:
				response = self.zenoss_client.reopen_event(event['evid'])
			if response.get('success'):
				response['totalCount'] = response['data'].get('updated');
				response['print_message'] = "Action {0} performed on event {1}".format(action, event['evid'])

		return response

class TaskFactory(object):
	@staticmethod
	def build_task(task_name, zenoss_url, user, password, context):
		if 'random_sample_filter' in task_name:
			return SampleBasedFilterTask(task_name, zenoss_url, user, password, context)
		elif 'random_action' in task_name:
			return RandomActionTask(task_name, zenoss_url, user, password, context)

def worker_task(task, n_requests):
	"""" Method that all the workers will run as their task """
	#task = RandomSearchTask(task, zenoss_url, n_requests, sample_data, user, password)
	return task.run(n_requests)

class EventTestHarness(object):

	def __init__(self, tasks, n_requests, zenoss_url, user, password):
		"""
		tasks = [ (n_workers, task_id, task_context), (n_workers, task_id, task_context), ..... ]
		"""
		self.zenoss_url = zenoss_url
		self.n_requests = n_requests
		self.user = user
		self.password = password
		self.n_workers = 0
		self.tasks = []
		for workers, task_id, context in tasks:
			self.n_workers = self.n_workers + workers
			for id in range(1, workers+1):
				if context.get('summary') is not None:
					if context.get('summary') is True:
						task_name = "{0}_summary_{1}".format(task_id, id)
					else:
						task_name = "{0}_archive_{1}".format(task_id, id)
				else:
					task_name = "{0}_{1}".format(task_id, id)
				task = TaskFactory.build_task(task_name, self.zenoss_url, self.user, self.password, context)
				self.tasks.append(task)

	def run(self):
		interrupted = False
		results = []
		start = time.time()
		if self.n_workers > 1:
			print "\nSpinning [{0}] workers that will send [{1}] requests each to [{2}]....".format(self.n_workers, self.n_requests, self.zenoss_url)
			try:
				pool = multiprocessing.Pool(processes=self.n_workers)
				results = [ pool.apply_async(worker_task, args=(task, self.n_requests)) for task in self.tasks ]
				results = [ p.get() for p in results ]
			except KeyboardInterrupt:
				interrupted = True
				pool.terminate()
				print "Execution terminated by user!"
		elif self.n_workers == 1:
			results = [ worker_task(self.tasks[0], self.n_requests) ]
		else:
			print "ERROR: No worker tasks were specified"

		end = time.time()
		if not interrupted:
			if results:
				ResultProcessor().process_results(results)
				print "Test took {0} seconds".format(end - start)
				raw_input("Press any key to finish...")
			else:
				print "ERROR: no results returned"""

