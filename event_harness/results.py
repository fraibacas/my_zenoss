
import argparse
import csv
import math
import sys

PANDAS_INSTALLED = True
try:
	from pandas import DataFrame, Series
	import matplotlib.pyplot as plt
except ImportError:
	PANDAS_INSTALLED = False

class ResultProcessor(object):

	CSV_FILE = './event_harness_results.csv'

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
			writer.writerow( ('Worker', 'Success', 'Start', 'Time', 'Results', 'Params') )
			for worker_results in workers_results:
				for result in worker_results:
					if not result: continue
					row = (result["worker"], result["success"], result["start"], result["elapsed"], result["results"], result["data"])
					writer.writerow(row)