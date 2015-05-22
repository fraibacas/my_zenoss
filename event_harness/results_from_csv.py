
from results import ResultProcessor, PANDAS_INSTALLED

import argparse
import csv
import os.path

from collections import defaultdict

def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(version="1.0",
                                     description="Produces graphs from results csv.")
    parser.add_argument("-f", "--file", action="store", default='event_harness_results.csv', type=str,
                        help="Results file path")
    return vars(parser.parse_args())

def main(results_file):
	with open(results_file, 'rb') as f:
		reader = csv.reader(f)
		results_per_worker = defaultdict(list)
		first_row = True
		for row in reader:
			if first_row:
				first_row = False
				continue
			else:
				result = {}
				worker = row[0]
				result["worker"] = worker
				result["success"] = bool(row[1])
				result["start"] = float(row[2])
				result["elapsed"] = float(row[3])
				result["results"] = int(row[4])
				result["data"] = row[5]
				#results.append(result)
				results_per_worker[worker].append(result)
		results = []
		for worker in sorted(results_per_worker.keys()):
			results.append(results_per_worker[worker])
		if results:
			result_processor = ResultProcessor()
			result_processor.print_result_summary(results)
			if PANDAS_INSTALLED:
				print "Plotting results..."
				result_processor.plot_results(results)
			else:
				print "Error: Could not generate graphs. pandas and/or matplotlib are not installed"
			raw_input("Press any key to finish...")

if __name__ == '__main__':
	""" """
	cli_options = parse_options()
	results_file = cli_options.get('file')
	if os.path.isfile(results_file):
		main(results_file)
	else:
		print "Error: Could not open results file: {0}".format(results_file)
