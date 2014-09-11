
import json
import argparse
import datetime
import sys
import logging
import os
from pandas import Series, DataFrame
import re
import time

import matplotlib.pyplot as plt
import numpy as np
import pickle

class ZopeLogProcessor(object):

	def _process_request(self, raw_request):
		request = {}
		try:
			raw_request_dict = json.loads(raw_request)
			request['user'] = raw_request_dict.get('user', '')
			# ----------------------------------------------
			router = raw_request_dict.get('router', '')
			call = raw_request_dict.get('call', '')
			if 'dmd' in call or 'dmd' in router:
				import pdb; pdb.set_trace()
			# SG data is in special format
			if 'request' in raw_request_dict.keys() and raw_request_dict.get('request'):
				try:
					data = raw_request_dict.get('request')
					if isinstance(data, list):
						data = data[0]
					if isinstance(data, dict):
						if 'action' in data.keys():
							router = data['action']
						if 'method' in data.keys():
							call = data['method']
				except Exception:
					pass
			request['call'] = '{0}.{1}'.format(router, call)
			# ----------------------------------------------
			request['elapsed'] = float(raw_request_dict.get('elapsed_time', -1))
			ts_text = raw_request_dict.get('timestamp', '')
			request['timestamp_text'] = ts_text
			request['timestamp'] = time.mktime(datetime.datetime.strptime(ts_text, "%Y-%m-%d %H:%M:%S").timetuple())

		except Exception as e:
			pass # bad datapoint
		return request	

	def process_file(self, log_file):
		requests = []
		if os.path.isfile(log_file):
			with open(log_file) as f:
				#raw_requests = [ line for line in f if self.METRIC_TEXT in line ]
				for raw_request in f: #raw_requests:
					request = self._process_request(raw_request)
					if request:
						requests.append(request)
		else:
			LOG.error("Could not open file: {0}".format(log_file))

		return requests

class ZopeRequestPlotter(object):

	def __init__(self, requests):
		self.requests = requests
		self.df = DataFrame(self.requests)
		self.df.to_pickle('data_frame.pickle')
		#Normalize Timestamp to hours
		min_timestamp_row = self.df.ix[self.df['timestamp'].idxmin()]
		min_timestamp_value = min_timestamp_row['timestamp']
		self.min_timestamp = min_timestamp_row['timestamp_text']
		self.max_timestamp = self.df.ix[self.df['timestamp'].idxmax()]['timestamp_text']
		self.df['timestamp'] = (self.df['timestamp'] - min_timestamp_value) / 3600

	def plot_call_summary(self):
		""" """
		# Gets the most expensive 1000 calls
		top_n_expensive_calls = self.df.sort_index(by='elapsed', ascending=False)[:1000]
		calls = [ call  for call, group in top_n_expensive_calls.groupby('call') ]

		data = []
		for call in calls:
			call_info = self.df[self.df['call']==call]['elapsed']
			call_data = {}
			call_data['call'] = call
			call_data['mean'] = call_info.mean()
			call_data['count'] = call_info.count()
			call_data['max'] = call_info.max()
			call_data['min'] = call_info.min()
			data.append(call_data)

		call_data_df = DataFrame(data)

		fig = plt.figure()
		fig.suptitle('{0}   -   {1}'.format(self.min_timestamp, self.max_timestamp), fontsize=16)

		ax = fig.add_subplot(3, 1, 1)
		#ax.get_xaxis().set_visible(False)
		self.df[self.df['elapsed']>=5].sort_index(by='timestamp').plot(title='Response time > 5 seconds', ax=ax, x='timestamp', y='elapsed')

		ax = fig.add_subplot(3, 1, 2)
		call_data_df[['call', 'min', 'max', 'mean']].set_index('call').plot(title='Response Time', ax=ax, kind='barh')

		ax = fig.add_subplot(3, 1, 3)
		call_data_df.plot(title='Call Count', ax=ax, x='call', y='count', kind='barh')

		fig.show()

		self.plot_calls_distribution(calls)

	def plot_calls_distribution(self, calls_to_plot):

		# plots call distribution for 2 calls
		#calls_to_plot = [ 'EventsRouter.query', 'EventsRouter.queryArchive', 'MessagingRouter.setBrowserState' ]
		#calls_to_plot = [ 'IncidentManagementRouter.runNotification', 'IncidentManagementRouter.associateIncident', 'EventsRouter.queryArchive' ]

		fig = plt.figure()
		fig.suptitle('{0}   -   {1}'.format(self.min_timestamp, self.max_timestamp), fontsize=16)

		graph_rows = 4
		graph_cols = len(calls_to_plot)/graph_rows
		if len(calls_to_plot)%graph_rows != 0:
			graph_cols = graph_cols + 1

		plot_n = 1
		for call in calls_to_plot:
			data = self.df[self.df['call']==call]
			ax = fig.add_subplot(graph_rows, graph_cols, plot_n)
			data.plot(title=call, ax=ax, x='timestamp', y='elapsed', style='.', fontsize=10)
			plot_n = plot_n + 1

		fig.show()

	def plot_user_call_data(self, fmean=False, fcount=False):
		function = None
		if fmean:
			function = mean
		else:
			function = count

		if function:
			fig = plt.figure()
			# call analysis (mean)
			graph_rows = 3
			graph_cols = 1
			plot_n = 1

			# top 3 users data
			top_users = users_call_count.index[:3]
			for top_user in top_users:
				#top_user = users_call_count.index[0]
				top_user_calls = self.df[ self.df.user == top_user ]
				ax = fig.add_subplot(graph_rows, graph_cols, plot_n)
				top_user_calls_count = top_user_calls.groupby('call').call.function()
				top_user_calls_count.sort()
				top_user_calls_count.plot(title='Call count for {0}'.format(top_user), ax = ax, kind='barh')
				plot_n = plot_n + 1
			fig.show()

	def plot_user_data(self):

		# call analysis per user (count)

		users_call_count = self.df.groupby('user')['timestamp'].count()
		users_call_count.sort(ascending=False)

		count_fig = plt.figure()
		count_fig.suptitle('{0}   -   {1}'.format(self.min_timestamp, self.max_timestamp), fontsize=16)
		graph_rows = 4
		graph_cols = 1
		plot_n = 1

		ax = count_fig.add_subplot(graph_rows, graph_cols, plot_n)
		users_call_count[:10].plot(title='Top 10 users. Number of calls', ax = ax, kind='barh')
		plot_n = plot_n + 1

		top_users = users_call_count.index[:3]
		for top_user in top_users:
			top_user_calls = self.df[ self.df.user == top_user ]
			ax = count_fig.add_subplot(graph_rows, graph_cols, plot_n)
			top_user_calls_count = top_user_calls.groupby('call').call.count()
			top_user_calls_count.sort()
			top_user_calls_count.plot(title='Call count for {0}'.format(top_user), ax = ax, kind='barh')
			plot_n = plot_n + 1

		count_fig.show()

		# call analysis per user (mean)

		mean_fig = plt.figure()
		mean_fig.suptitle('{0}   -   {1}'.format(self.min_timestamp, self.max_timestamp), fontsize=16)
		users_call_mean = self.df.groupby('user')['elapsed'].mean()
		users_call_mean.sort(ascending=False)

		graph_rows = 4
		graph_cols = 1
		plot_n = 1

		ax = mean_fig.add_subplot(graph_rows, graph_cols, plot_n)
		users_call_mean[:10].plot(title='Top 10 users: mean elapsed time per call', ax = ax, kind='barh')
		plot_n = plot_n + 1

		# top 3 users data
		top_users = users_call_mean.index[:3]
		for top_user in top_users:
			top_user_calls = self.df[ self.df.user == top_user ]
			ax = mean_fig.add_subplot(graph_rows, graph_cols, plot_n)
			top_user_calls_count = top_user_calls.groupby('call').elapsed.mean()
			top_user_calls_count.sort()
			top_user_calls_count.plot(title='Call mean for {0}'.format(top_user), ax = ax, kind='barh')
			plot_n = plot_n + 1
		mean_fig.show()
		

	def plot_archive_calls(self):

		archive_calls = self.df[ self.df.call == 'EventsRouter.queryArchive' ]
		archive_calls_count = archive_calls.groupby('user')['elapsed'].count()
		archive_calls_count.sort(ascending=False)

		archive_fig = plt.figure()

		archive_fig.suptitle('{0}   -   {1}'.format(self.min_timestamp, self.max_timestamp), fontsize=16)

		graph_rows = 2
		graph_cols = 1
		plot_n = 1

		# Archive call count per user
		ax = archive_fig.add_subplot(graph_rows, graph_cols, plot_n)
		archive_calls_count.plot(title='Archive call count per user', ax = ax, kind='barh')
		plot_n = plot_n + 1
		'''
		# Archive call mean per user
		ax = archive_fig.add_subplot(graph_rows, graph_cols, plot_n)
		archive_calls_mean = archive_calls.groupby('user')['elapsed'].mean()
		archive_calls_mean.plot(title='Archive call mean elapsed time per user', ax = ax, kind='barh')
		plot_n = plot_n + 1
		'''
		# Archive call distribution for user with more calls to archive
		user_pegging_archive = archive_calls_count.index[0]

		pegger_df = archive_calls[archive_calls.user=='zec'][['elapsed', 'timestamp']]
		pegger_df.sort_index(by='timestamp')
		ax = archive_fig.add_subplot(graph_rows, graph_cols, plot_n)
		pegger_df.plot(title='Top archive user call distribution vs elapsed time', ax=ax, x='timestamp', y='elapsed', style='.', fontsize=10)

		archive_fig.show()

	def plot_zec_user_calls(self):

		zec_calls = self.df[ self.df.user == 'zec' ]
		zec_calls_count = zec_calls.groupby('call')['elapsed'].count()
		zec_calls_count.sort(ascending=False)

		# Call count
		fig = plt.figure()
		fig.suptitle('{0}   -   {1}'.format(self.min_timestamp, self.max_timestamp), fontsize=16)

		ax = fig.add_subplot(2, 1, 1)
		zec_calls_count.plot(title='Zec User calls', ax = ax, kind='barh')

		# Call Distribution
		data_to_plot = DataFrame()
		for call, group in zec_calls.groupby('call'):
			data_to_plot = data_to_plot.append(group[['call','elapsed','timestamp']])

		ax = fig.add_subplot(2, 1, 2)

		data_to_plot.plot(title='Zec user call distribution vs elapsed time', ax=ax, x='timestamp', y='elapsed', style='.', fontsize=10)
		
		fig.show()


	def plot_requests_info(self):

		self.plot_call_summary()
		self.plot_user_data()
		#self.plot_archive_calls()
		self.plot_zec_user_calls()


PICKLE_FILE = '/tmp/zope_log_pickle'

def main(args):

	requests = {}
	if args.get('file'):
		print 'Loading data from file {0}'.format(args.get('file'))
		requests = ZopeLogProcessor().process_file(args.get('file'))
		pickle.dump(requests, open(PICKLE_FILE, 'wb'))

	if args.get('pickle'):
		print 'Loading data from pickle {0}'.format(PICKLE_FILE)
		requests = pickle.load(open(PICKLE_FILE))

	ZopeRequestPlotter(requests).plot_requests_info()


def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(description="Parses zope log searching for requests information.")
    parser.add_argument("-f", "--file", action="store", help="path to log file")
    parser.add_argument("-p", "--pickle", action="store_true", default=False, help="loads data from pickle")
    return vars(parser.parse_args())

if __name__ == '__main__':
	cli_args = parse_options()
	if cli_args.get('file') or cli_args.get('pickle'):
		main(cli_args)
		raw_input("Press any key to finish...")
	else:
		LOG.error("Wrong number of arguments. Execute 'python {0} -h' for more info".format(sys.argv[0]))