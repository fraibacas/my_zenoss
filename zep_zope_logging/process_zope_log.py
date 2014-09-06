
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
			router = raw_request_dict.get('router', '')
			call = raw_request_dict.get('call', '')
			request['call'] = '{0}.{1}'.format(router, call)
			request['elapsed'] = float(raw_request_dict.get('elapsed_time', -1))
			ts_text = raw_request_dict.get('timestamp', '')
			request['timestamp_text'] = ts_text
			request['timestamp'] = time.mktime(datetime.datetime.strptime(ts_text, "%Y-%m-%d %H:%M:%S").timetuple())
		except Exception:
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

class RequestPlotter(object):

	@staticmethod
	def plot(data, x_axes, y_axes, title='', kind='line'):
		''' '''
		if len(data) == 0:
			return

		fig = plt.figure()
		if x_axes == 'timestamp':
			min_timestamp_row = data.ix[data['timestamp'].idxmin()]
			min_timestamp_value = min_timestamp_row['timestamp']
			min_timestamp = min_timestamp_row['timestamp_text']
			max_timestamp = data.ix[data['timestamp'].idxmax()]['timestamp_text']

			#Normalize Timestamp to hours
			data['timestamp'] = (data['timestamp'] - min_timestamp_value) / 3600

			#fig.text(0, 0, '        {0}     -     {1}'.format(min_timestamp, max_timestamp))
			#fig.suptitle(title, fontsize=16)

			date_string = '{0} - {1}'.format(min_timestamp, max_timestamp)
			if title:
				title = '{0}\n{1}'.format(title, date_string)
			else:
				title = date_string

		ax = fig.add_subplot(1, 1, 1)
		if isinstance(data, Series):
			#data.plot(title=title, ax=ax, x=x_axes, y=y_axes, marker='o')
			data.plot(title=title, kind=kind)
		else:
			data.plot(title=title, ax=ax, x=x_axes, y=y_axes, marker='o', kind=kind)
		fig.show()

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

	def plot_requests(self):

		self.plot_call_summary()
		'''
		# top 15 calls count
		call_count = {}
		for call, group in self.df.groupby('call'):
			call_count[call] = group.count()[0]
		call_count_df = Series(call_count)
		call_count_df.sort(ascending=False)
		RequestPlotter.plot(call_count_df[:15], 'count', 'call', 'Top 15 calls (count)', kind='barh')

		# top 15 calls mean
		call_mean = {}
		for call, group in self.df.groupby('call'):
			call_mean[call] = group['elapsed'].mean()
		call_mean_df = Series(call_mean)
		call_mean_df.sort(ascending=False)
		RequestPlotter.plot(call_mean_df[:15], 'mean', 'call', 'Top 15 calls (mean)', kind='barh')

		# mean of top 1000 most expensive calls grouped by call
		top_100 = self.df.sort_index(by='elapsed', ascending=False)[:1000]
		top_100_mean = {}
		for call, group in top_100.groupby('call'):
			top_100_mean[call] = group['elapsed'].mean()
		top_100_mean_series = Series(top_100_mean)
		top_100_mean_series.sort(ascending=False)
		RequestPlotter.plot(top_100_mean_series, 'count', 'user', 'Top most expensive calls (mean) ', kind='barh')

		# count of top 1000 most expensive calls grouped by call
		top_100_count = {}
		for call, group in top_100.groupby('call'):
			top_100_count[call] = group['elapsed'].count()
		top_100_count_series = Series(top_100_count)
		top_100_count_series.sort(ascending=False)
		RequestPlotter.plot(top_100_count_series, 'count', 'user', 'Top most expensive calls (count) ', kind='barh')
		

		import pdb; pdb.set_trace()

		# top 20 users
		user_count = {}
		for user, group in self.df.groupby('user'):
			user_count[user] = group.count()[0]
		user_count_series = Series(user_count)
		user_count_series.sort(ascending=False)
		RequestPlotter.plot(user_count_series[:20], 'count', 'user', 'Top 20 users ', kind='barh')

		# Call counts for top user
		top_user = user_count_series.index[0]
		top_user_calls = {}
		for call, group in self.df[self.df['user']==top_user].groupby('call'): #self.df[top_user].groupby('call'):
			top_user_calls[call] = group.count()[0]
		top_user_calls_series = Series(top_user_calls)
		top_user_calls_series.sort(ascending=False)
		RequestPlotter.plot(top_user_calls_series[:5], 'count', 'user', 'Top user top calls', kind='barh')

		top_user = user_count_series.index[1]
		top_user_calls = {}
		for call, group in self.df[self.df['user']==top_user].groupby('call'): #self.df[top_user].groupby('call'):
			top_user_calls[call] = group.count()[0]
		top_user_calls_series = Series(top_user_calls)
		top_user_calls_series.sort(ascending=False)
		RequestPlotter.plot(top_user_calls_series[:5], 'count', 'user', 'Top user top calls', kind='barh')

		top_user = user_count_series.index[2]
		top_user_calls = {}
		for call, group in self.df[self.df['user']==top_user].groupby('call'): #self.df[top_user].groupby('call'):
			top_user_calls[call] = group.count()[0]
		top_user_calls_series = Series(top_user_calls)
		top_user_calls_series.sort(ascending=False)
		RequestPlotter.plot(top_user_calls_series[:5], 'count', 'user', 'Top user top calls', kind='barh')		
		
		# Call Summary
		call_df = self.df.groupby('call').elapsed.apply(get_stats).unstack()

		# User Summary
		# - Number of calls per user
		self.df.groupby('user').apply(get_count).unstack()

		# - 10 most expensive calls by user
		self.df.groupby(['user','call']).elapsed.apply(get_stats).unstack().sort_index(by=['max'], ascending=False)[:10]
		'''

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

	ZopeRequestPlotter(requests).plot_requests()


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