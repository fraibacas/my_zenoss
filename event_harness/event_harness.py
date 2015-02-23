

import argparse
import csv
import json
import math
import multiprocessing
import pickle
import random
import re
import requests
import sys
import time

PANDAS_INSTALLED = True
try:
	from pandas import DataFrame, Series
	import matplotlib.pyplot as plt
except ImportError:
	PANDAS_INSTALLED = False

class ZenossClient(object):
	""" Proxy to interact with Zenoss """
	def __init__(self, zenoss_url, user='admin', password='zenoss'):
		self.session = None
		self.user = user
		self.password = password
		self.zenoss_url = zenoss_url

		if 'http' not in self.zenoss_url:
			self.BASE_URL = 'http://{0}/zport'.format(self.zenoss_url)
		else:
			self.BASE_URL = '{0}/zport'.format(self.zenoss_url)
		self.AUTH_URL = '{0}/acl_users/cookieAuthHelper/login'.format(self.BASE_URL)
		self.EVENTS_ROUTER_URL = '{0}/dmd/Events/evconsole_router'.format(self.BASE_URL)
		self.DASHBOARD_URL = '{0}/dmd/Dashboard'.format(self.BASE_URL)

	def login(self):
		success = False
		data = { "__ac_name": self.user, "__ac_password": self.password}
		self.session = requests.Session()
		try:
			resp = self.session.post(self.AUTH_URL, data)
			if resp.ok:
				# Lets load the dashboard to check that we are authenticated
				resp = self.session.get(self.DASHBOARD_URL)
				splitted = resp.text.split('title>')
				if "Dashboard" in splitted[1]:
					success = True
				else:
					self.session = None
		except:
			success = False
			self.session = None

		return success

	def _build_request_body(self, request_info):
		body = request_info.get('body')
		if not body:
			body = {}
			body = { 'type':'rpc', 'tid':185, }
			body["action"] = request_info['action']
			body["method"] = request_info['method']

			page = request_info.get('page', 1)
			sort = request_info.get('sort', 'lastTime')
			limit = request_info.get('limit', 200)
			data = {"uid": "/zport/dmd", "page": page, "limit": limit, "sort": sort, "dir":"DESC"}
			
			params = request_info.get('params')
			if not params:
				params = {}
				owner_id = request_info.get('user')
				device = request_info.get('device')
				event_state = request_info.get('event_state', [0, 1, 2, 3, 4, 5, 6])
				event_severty = request_info.get('event_severity', [0, 1, 2, 3, 4, 5])
				incident = request_info.get('incident')
				event_class = request_info.get('event_class')

				summary = request_info.get('summary')
				params['eventState'] = event_state
				params['severity'] = event_severty
				if owner_id:
					params['ownerid'] = owner_id
				if device:
					params['device'] = device
				if summary:
					params['summary'] = summary
				if incident:
					params['zenoss.IncidentManagement.number'] = incident
				if event_class:
					params["eventClass"] = event_class

			default_keys = [ "ownerid", "eventState", "severity", "device", "component", "eventClass", 
						     "summary", "firstTime", "lastTime", "count", "evid", "eventClassKey", "message" ]

			data["params"] = params
			data["keys"] = default_keys
			body["data"] = [data]

		return body

	def _send_request(self, url, body):
		"""
		Sends request using requests module
		"""
		headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
		connected = False
		if not self.session:
			connected = self.login()
		response = self.session.post(url, data=json.dumps(body), headers=headers)
		return response.json()["result"]		

	def send_event_filter_request(self, request_info, archive=False):
		"""
		returns a dict with keys [u'totalCount', u'events', u'success', u'asof']
		"""
		url = self.EVENTS_ROUTER_URL
		request_info['action'] = 'EventsRouter'
		request_info['method'] = 'query'
		if archive:
			request_info['event_state'] = [3, 4, 6]
			request_info['method'] = 'queryArchive'

		body = self._build_request_body(request_info)
		response = self._send_request(url, body)
		return response

	def send_event_creation_request(self, event):
		url = self.EVENTS_ROUTER_URL
		body = {}
		body['type'] = 'rpc'
		body['tid'] = 222
		body['action'] = 'EventsRouter'
		body['method'] = 'add_event'

		body['data'] = [event]
		response = self._send_request(url, body)
		return response
	
	def acknowledge_event(self, uuid):
		url = self.EVENTS_ROUTER_URL
		body = {}
		body['type'] = 'rpc'
		body['tid'] = 223
		body['action'] = 'EventsRouter'
		body['method'] = 'acknowledge'
		body["data"] = [ { "evids":[uuid],  } ]
		response = self._send_request(url, body)
		return response

	def reopen_event(self, uuid):
		url = self.EVENTS_ROUTER_URL
		body = {}
		body['type'] = 'rpc'
		body['tid'] = 223
		body['action'] = 'EventsRouter'
		body['method'] = 'reopen'
		body["data"] = [ { "evids":[uuid],  } ]
		response = self._send_request(url, body)
		return response

	def close_event(self, uuid):
		url = self.EVENTS_ROUTER_URL
		body = {}
		body['type'] = 'rpc'
		body['tid'] = 223
		body['action'] = 'EventsRouter'
		body['method'] = 'close'
		body["data"] = [ { "evids":[uuid],  } ]
		response = self._send_request(url, body)
		return response

class SampleDataLoader(object):

	def load_from_pickle(self, path):
		sample_data = None
		try:
			sample_data = pickle.load(open(path, 'rb'))
		except Exception:
			sample_data = None
		return sample_data

	# TODO: Load data from database

class HarnessResultProcessor(object):

	CSV_FILE = './archive_harness_results.csv'

	def plot_results(self, workers_results):
		""" """
		try:
			flattened_results = []
			for worker_results in workers_results:
				flattened_results.extend(worker_results)
			df = DataFrame(flattened_results)

			if not df.empty:
				# Normalize the timestamp
				min_ts = df['start'].min()
				df['timestamp'] = (df['start'] - min_ts)

				workers = df.worker.unique()

				"""  Plot response times per worker """

				max_response_time = df.elapsed.max() # y axes max value
				max_start_time = df.timestamp.max() # x axes max value

				# hack to have all x axis with the same xlim. The call to set_xlim does not seem to work
				last_values = []
				for worker in workers:
					last_timestamp = df[df['worker']==worker].timestamp.max()
					last_values.append({'worker': worker, 'timestamp': math.ceil(last_timestamp + 1), 'elapsed': 0, 'start':0, 'success': True})
					last_values.append({'worker': worker, 'timestamp': math.ceil(max_start_time + 1), 'elapsed': 0, 'start':0, 'success': True})
				
				response_time_df = df.append(DataFrame(last_values))
				
				rows = cols = math.ceil(math.sqrt(len(workers)))
				if cols*(cols-1) >= len(workers):
					rows = cols - 1

				subplot = 1
				response_time_fig = plt.figure()
				response_time_fig.suptitle('\nResponse time (seconds) per worker over time', fontsize=18)
				for worker in workers:
					ax = response_time_fig.add_subplot(rows, cols, subplot)
					ax.set_ylim([0, max_response_time + 1])
					ax.xaxis.set_visible(False)
					response_time_df[response_time_df['worker']==worker].plot(title=worker, ax=ax, x='timestamp', y='elapsed', marker='o')
					subplot = subplot + 1
				plt.subplots_adjust(wspace=0.3, hspace=0.3, top=0.85, left=0.08, bottom=0.1, right=0.92)
				response_time_fig.show()

				"""  Plot response times per worker """

				worker_summary = []
				requests_summary = []
				for worker in workers:
					min_elapsed = df[df['worker']==worker].elapsed.min()
					max_elapsed = df[df['worker']==worker].elapsed.max()
					mean_elapsed = df[df['worker']==worker].elapsed.mean()
					worker_summary.append({ 'worker': worker, 'min': min_elapsed, 'max': max_elapsed, 'mean': mean_elapsed })
					successful_requests = df[(df.worker==worker) & (df.success==True)].worker.count()
					failed_requests = df[(df.worker==worker) & (df.success==False)].worker.count()
					requests_summary.append({'worker': worker, 'success': successful_requests, 'failed': failed_requests})

				worker_summary_df = DataFrame(worker_summary)
				worker_summary_df = worker_summary_df.set_index('worker')

				requests_summary_df  = DataFrame(requests_summary)
				requests_summary_df = requests_summary_df.set_index('worker')

				worker_summary_fig = plt.figure()
				worker_summary_fig.suptitle('\nResponse Time Summary', fontsize=18)
				ax = worker_summary_fig.add_subplot(1, 1, 1)
				worker_summary_df.plot(kind='barh', ax=ax)

				plt.subplots_adjust(wspace=0.3, hspace=0.3, top=0.85, left=0.20, bottom=0.1, right=0.92)
				worker_summary_fig.show()


				"""  Plot failed/successful requests """

				requests_summary_fig = plt.figure()
				requests_summary_fig.suptitle('\nNumber of Failed/Successful Requests', fontsize=18)
				ax = requests_summary_fig.add_subplot(1, 1, 1)
				requests_summary_df.plot(kind='barh', ax=ax, color=['r','g'], stacked=True)
				plt.subplots_adjust(wspace=0.3, hspace=0.3, top=0.85, left=0.20, bottom=0.1, right=0.92)
				requests_summary_fig.show()

		except:
			print "Exception plotting results"

	def print_result_summary(self, workers_results):
		""" """
		for worker_result in workers_results:
			min_resp = sys.maxsize
			max_resp = -1
			total_time = 0
			successful_calls = 0
			failed_calls = 0
			for result in worker_result:
				if result and result['success']:
					successful_calls = successful_calls + 1
					total_time = total_time + result['elapsed']
					min_resp = min(result['elapsed'], min_resp)
					max_resp = max(result['elapsed'], max_resp)
				else:
					failed_calls = failed_calls + 1
			LJUST = 40
			print "\n{0}".format(result['worker'])
			if successful_calls > 0:
				print "\tNumber of sucessful calls: ".ljust(LJUST) + "{0}".format(successful_calls)
				print "\tNumber of failed calls: ".ljust(LJUST) + "{0}".format(failed_calls)
				print "\tMin response time (ms): ".ljust(LJUST) + "{0}".format(min_resp)
				print "\tMax response time (ms): ".ljust(LJUST) + "{0}".format(max_resp)
				print "\tAverage response time (ms):".ljust(LJUST) + "{0}".format(total_time / successful_calls)
			else:
				print "\tERROR: All requests failed"
		print "\n"

	def process_results(self, workers_results):
		print "\nExporting results to csv file..."
		self.generate_results_csv(workers_results)
		print "Results exported to {0}.".format(self.CSV_FILE)
		
		self.print_result_summary(workers_results)

		if PANDAS_INSTALLED:
			print "\nPlotting results..."
			self.plot_results(workers_results)
		else:
			print "\nWARNING: Results can not be plotted. Modules pandas and matplotlib needed."

	def generate_results_csv(self, workers_results):
		with open(self.CSV_FILE, 'wb') as f:
			writer = csv.writer(f)
			writer.writerow( ('Worker', 'Success', 'Time', 'Results', 'Params') )
			for worker_results in workers_results:
				for result in worker_results:
					if not result: continue
					row = (result["worker"], result["success"], result["elapsed"], result["results"], result["data"])
					writer.writerow(row)

class RandomArchiveRequestGenerator(object):

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

class ArchiveTestHarnessTask(object):

	def __init__(self, task_name, zenoss_url, n_requests, sample_data, user, password):
		self.task_name = task_name
		self.zenoss_url = zenoss_url
		self.n_requests = n_requests
		self.sample_data = sample_data
		self.user = user
		self.password = password
		self.zenoss_client = ZenossClient(zenoss_url, user, password)

	def send_request(self, request_info):
		result = {}
		result["success"] = False
		result["results"] = -1
		result["data"] = request_info
		result["worker"] = self.task_name

		start = time.time()
		try:
			response = self.zenoss_client.send_event_filter_request(request_info, archive=True)
		except KeyboardInterrupt as e:
			raise e
		except Exception as ex:
			response = None
		end = time.time()
		result["start"] = start
		result["elapsed"] = end-start

		if response and response.get('success'):
			print "\t{0} => Request took {1} seconds and returned {2} results. {3}".format(self.task_name, end-start, response['totalCount'], request_info)
			result["results"] = response['totalCount']
			result["success"] = True
		else:
			print "\tRequest failed. Request time: {0}".format(end-start)

		return result

	def run(self):
		results = []
		request_generator = RandomArchiveRequestGenerator(self.sample_data)
		for request in range(self.n_requests):
			try:
				request_info = request_generator.generate_random_request()
				result = self.send_request(request_info)
				results.append(result)
			except KeyboardInterrupt:
				break
		return results		

def worker_task(zenoss_url, n_requests, sample_data, user, password):
	"""" Method that all the workers will run as their task """
	task_name = multiprocessing.current_process()._name
	task = ArchiveTestHarnessTask(task_name, zenoss_url, n_requests, sample_data, user, password)
	return task.run()

class ArchiveTestHarness(object):

	def __init__(self, zenoss_url, workers, n_requests, sample_data, user, password):
		""" """
		self.zenoss_url = zenoss_url
		self.n_workers = workers
		self.n_requests = n_requests
		self.sample_data = sample_data
		self.user = user
		self.password = password

	def run(self):
		interrupted = False
		results = []
		start = time.time()
		if self.n_workers > 1:
			print "\nSpinning [{0}] workers that will send [{1}] random requests each to [{2}]....".format(self.n_workers, self.n_requests, self.zenoss_url)
			try:
				pool = multiprocessing.Pool(processes=self.n_workers)
				results = [ pool.apply_async(worker_task, args=(self.zenoss_url, self.n_requests, self.sample_data, self.user, self.password)) for i in range(self.n_workers) ]
				results = [ p.get() for p in results ]
			except KeyboardInterrupt:
				interrupted = True
				pool.terminate()
				print "Execution terminated by user!"
		else:
			results = [ worker_task(self.zenoss_url, self.n_requests, self.sample_data, self.user, self.password) ]

		end = time.time()
		if not interrupted:
			if results:
				HarnessResultProcessor().process_results(results)
				print "Test took {0} seconds".format(end - start)
				raw_input("Press any key to finish...")
			else:
				print "ERROR: no results returned"""

def log_status_msg(msg, success=True, fill=False, width=80):
	if fill:
		msg = msg.ljust(width, '.')
	if success:
		print '{0} OK'.format(msg)
	else:
		print '{0} FAILED'.format(msg)

def main(zenoss_url, n_workers, n_requests, data_file, user, password):
	""" """
	print ""
	connection_status_msg = "Checking connectivity to Zenoss and credentials"
	data_status_msg = "Loading data samples from {0}".format(data_file)

	if ZenossClient(zenoss_url, user, password).login():
		log_status_msg(connection_status_msg, fill=True)
		sample_data = SampleDataLoader().load_from_pickle(data_file)
		if sample_data:
			log_status_msg(data_status_msg, fill=True)
			if RandomArchiveRequestGenerator(sample_data).validate():
				ArchiveTestHarness(zenoss_url, n_workers, n_requests, sample_data, user, password).run()
			else:
				print "\nERROR: Sample data does not contain enough information to generate random queries.\n"
		else:
			log_status_msg(data_status_msg, success=False, fill=True)
			print "\nERROR: Could not load sample data from {0}.\n".format(data_file)
	else:
		log_status_msg("Checking connectivity to Zenoss and credentials", success=False, fill=True)
		print "\nERROR: Could not log in Zenoss. Please check zenoss host and credentials. [ Zenoss host = {0} / User = {1} / Password = {2} ]\n".format(zenoss_url, user, password)


def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(version="1.0",
                                     description="Sends radom requests to a zenoss instance to test performance.")
    parser.add_argument("-z", "--zenoss_url", action="store", default='localhost', type=str,
                        help="Zenoss url including port")
    parser.add_argument("-n", "--n_requests", action="store", default=10, type=int,
                        help="Number of radom requests each worker will send.")
    parser.add_argument("-w", "--n_workers", action="store", default=1, type=int,
                        help="Number of simultaneous workers sending requests to Zenoss.")
    parser.add_argument("-d", "--data_file", action="store", default='./sample_data.pickle', type=str,
                        help="Pickle containing sample data to build request filters.")
    parser.add_argument("-u", "--user", action="store", default='admin', type=str,
                        help="User to log in Zenoss.")
    parser.add_argument("-p", "--password", action="store", default='zenoss', type=str,
                        help="Password to log in Zenoss.")
    return vars(parser.parse_args())


if __name__ == '__main__':
	""" """
	cli_options = parse_options()
	zenoss_url = cli_options.get('zenoss_url')
	n_workers = cli_options.get('n_workers')
	n_requests = cli_options.get('n_requests')
	data_file = cli_options.get('data_file')
	user = cli_options.get('user')
	password = cli_options.get('password')
	main(zenoss_url, n_workers, n_requests, data_file, user, password)

