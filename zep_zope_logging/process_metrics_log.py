

import argparse
import datetime
import sys
import logging
import os
from pandas import DataFrame
import re
import time

import matplotlib.pyplot as plt
import numpy as np

def create_log():
	log = logging.getLogger('ZepMetricsProcessor')
	log.setLevel(logging.DEBUG)
	handler = logging.StreamHandler(sys.stdout)
	handler.setFormatter(logging.Formatter("%(asctime)s => %(message)s"))
	log.addHandler(handler)
	return log

LOG = create_log()

class ZepMetric(object):
	def __init__(self, time_stamp, type, name, value):
		pass


class ZepMetricsLogProcessor(object):
	
	METRIC_TEXT = 'metrics-logger-reporter'
	#TS_RE = '^(dddd-dd-ddTdd:dd:dd)(.*?)'
	METRICS_RE = '(\S+)=(".*?"|\S+)'

	def _convert_types(self, metric):
		''' If value in metric convert to float'''
		float_fields = [ 'value', 'm1', 'mean', 'count' ]
		for field in float_fields:
			if field in metric.keys():
				try:
					metric[field] = float(metric[field])
				except:
					metric[field] = -1

	def _process_raw_metric(self, raw_metric):
		metric = {}
		try:
			raw_data = raw_metric.split()
			ts = raw_data[0]
			values = raw_data[5:]
			metric = { key.strip(','):val.strip(',') for key, val in re.findall(self.METRICS_RE, ' '.join(values)) }
			self._convert_types(metric)
			metric['timestamp_text'] = ts
			metric['timestamp'] = time.mktime(datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f").timetuple())
		except Exception as e:
			LOG.warn('Exception processing log data. {0}'.format(e))
			raise e

		return metric

	def process_file(self, log_file):
		metrics = []
		if os.path.isfile(log_file):
			with open(log_file) as f:
				raw_metrics = [ line for line in f if self.METRIC_TEXT in line ]
				for raw_metric in raw_metrics:
					metric = self._process_raw_metric(raw_metric)
					metrics.append(metric)
		else:
			LOG.error("Could not open file: {0}".format(log_file))

		return metrics

class MetricPlotter(object):

	@staticmethod
	def plot(graph_rows, metrics_to_plot, data, y_axes='value', title=''):
		''' '''
		min_timestamp = data.ix[data['timestamp'].idxmin()]['timestamp_text']
		max_timestamp = data.ix[data['timestamp'].idxmax()]['timestamp_text']

		graph_cols = len(metrics_to_plot)/graph_rows
		if len(metrics_to_plot)%graph_rows != 0:
			graph_cols = graph_cols + 1
		fig = plt.figure()
		fig.suptitle(title, fontsize=16)
		fig.text(0, 0, '        {0}     -     {1}'.format(min_timestamp, max_timestamp))
		i = 1
		for metric in metrics_to_plot:
			data_to_plot = data[data['name']==metric][['timestamp', y_axes]]
			ax = fig.add_subplot(graph_rows, graph_cols, i)
			ax.set_ylabel(y_axes)
			data_to_plot.plot(title=metric, ax=ax, x='timestamp', y=y_axes)
			i = i + 1
		fig.show()

class JvmMetricsProcessor(object):

	def __init__(self, metrics):
		self.metrics = [ m  for m in metrics if 'jvm' in m.get('name') ]
		self.df = DataFrame(self.metrics)

	def plot_metrics(self):
		metrics_to_plot = ['jvm.memory.heap.usage', 'jvm.memory.non-heap.usage', 'jvm.fd.usage', 'jvm.memory.total.used', 'jvm.thread-states.count', 'jvm.memory.pools.Par-Eden-Space.usage']
		MetricPlotter.plot(2, metrics_to_plot, self.df)

class ZepMetricsProcessor(object):

	def __init__(self, metrics):
		self.metrics = [ m  for m in metrics if 'zep' in m.get('name') ]
		self.df = DataFrame(self.metrics)

	def plot_metrics(self):

		metrics_to_plot = [ 'org.zenoss.zep.dao.impl.EventIndexQueueDaoImpl.archiveIndexQueueSize', 
				  			'org.zenoss.zep.dao.impl.EventIndexQueueDaoImpl.summaryIndexQueueSize' ]
		MetricPlotter.plot(2, metrics_to_plot, self.df, title='# events pending to be indexed')

		metrics_to_plot = [ 'org.zenoss.zep.index.impl.EventIndexerImpl.index', 
       						'org.zenoss.zep.index.impl.EventIndexerImpl.indexFully',
       						'org.zenoss.zep.rest.EventsResource.addNote',
       						'org.zenoss.zep.rest.EventsResource.addNoteBulkAsync' ]
		MetricPlotter.plot(2, metrics_to_plot, self.df, 'm1', title='index and addNote')
		#MetricPlotter.plot(2, metrics_to_plot, self.df, 'count', title='index and addNote')

		metrics_to_plot = [ 'org.zenoss.zep.rest.EventsResource.createSavedSearch', 
							'org.zenoss.zep.rest.EventsResource.deleteSavedSearch',
							'org.zenoss.zep.rest.EventsResource.listSavedSearch',
							'org.zenoss.zep.rest.EventsResource.createArchiveSavedSearch', 
       						'org.zenoss.zep.rest.EventsResource.deleteArchiveSavedSearch',
       						'org.zenoss.zep.rest.EventsResource.listArchiveSavedSearch' ]
		MetricPlotter.plot(2, metrics_to_plot, self.df, 'm1')

		metrics_to_plot = [ 'org.zenoss.zep.rest.EventsResource.listEventIndex', 
							'org.zenoss.zep.rest.EventsResource.listEventIndexGet',
							#'org.zenoss.zep.rest.EventsResource.listEventIndexArchive',       # Not used
							#'org.zenoss.zep.rest.EventsResource.listEventIndexArchiveGet' 
							]   # Not used
		MetricPlotter.plot(2, metrics_to_plot, self.df, 'm1')

		metrics_to_plot = [ 'org.zenoss.zep.rest.EventsResource.getEventSummaryByUuid', 
							'org.zenoss.zep.rest.EventsResource.getEventTagSeverities' ]
		MetricPlotter.plot(2, metrics_to_plot, self.df, 'm1')

		metrics_to_plot = [ 'org.zenoss.zep.rest.EventsResource.updateEventDetails', 
							#'org.zenoss.zep.rest.EventsResource.updateEventSummaryByUuid', # not used
							'org.zenoss.zep.rest.EventsResource.updateEvents' ]
		MetricPlotter.plot(2, metrics_to_plot, self.df, 'm1')

		metrics_to_plot = [ 'org.zenoss.zep.index.impl.EventIndexerImpl.index', 
       						'org.zenoss.zep.index.impl.EventIndexerImpl.indexFully' ]
		MetricPlotter.plot(2, metrics_to_plot, self.df, 'mean', title='MEAN index and addNote')



def main(args):
	metrics = ZepMetricsLogProcessor().process_file(args.get('file'))
	
	jvm_metrics = JvmMetricsProcessor(metrics)
	jvm_metrics.plot_metrics()

	zep_metrics = ZepMetricsProcessor(metrics)
	zep_metrics.plot_metrics()

def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(description="Parses zeneventserver log searching for metrics information.")
    parser.add_argument("-f", "--file", action="store", help="path to log file")
    return vars(parser.parse_args())

if __name__ == '__main__':
	cli_args = parse_options()
	if cli_args.get('file'):
		main(cli_args)
		raw_input("Press any key to finish...")
	else:
		LOG.error("Wrong number of arguments. Execute 'python {0} -h' for more info".format(sys.argv[0]))
