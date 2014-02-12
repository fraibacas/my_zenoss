
import re
import sys


class LogParser(object):

	def __init__(self):
		self.name = "DefaultParserName"

	def parse_line(self, line):
		print "Calling default line parser."

	def print_results(self):
		print "Calling default result printer."

	def reset(self):
		print "Calling default reset method."

class CatalogExceptionParser(LogParser):

	def __init__(self):
		self.numberOfCatalogServiceException = 0
		self.name = "Number of CatalogExceptions"

	def parse_line(self, line):
		if "CatalogServiceException" in line:
			self.numberOfCatalogServiceException = self.numberOfCatalogServiceException + 1

	def print_results(self):
		print "Number of CatalogServiceExceptions: {0}".format(self.numberOfCatalogServiceException)

	def reset(self):
		self.numberOfCatalogServiceException = 0

class TimeStampIntervalParser(object):
	""" Prints the first and last timestamps of the file """
	def __init__(self):
		self.name = "Log Time Interval"
		self.first_line = ""
		self.last_line = ""

	def reset(self):
		self.first_line = ""
		self.last_line = ""

	def parse_line(self, line):
		if len(self.first_line) == 0:
			self.first_line = line
		else:
			self.last_line = line

	def print_results(self):
		date_re = r'(2014-\d\d-\d\d \d\d:\d\d:\d\d)'
		first_timestamp = "Unknown"
		last_timestamp = "Unknown"

		match = re.search(date_re, self.first_line)
		if match:
			first_timestamp = match.groups()[0]

		match = re.search(date_re, self.last_line)
		if match:
			last_timestamp = match.groups()[0]

		print "Log's First Timestamp  =>  {0}".format(first_timestamp)
		print "Log's Last  Timestamp  =>  {0}".format(last_timestamp)

class LongTransformsParser(LogParser):

	class _TransformStatistics(object):
		def __init__(self, name, time):
			self.name = name
			self.occurrences = 1
			self.total_time = float(time)

	def __init__(self):
		self.results = {}
		self.name = "Long Running Transforms"

	def reset(self):
		self.results = {}

	def parse_line(self, line):
		if "WARNING zen.Events: Event transform took" in line:
			match_text = r'(.*) WARNING zen.Events: Event transform took (.*) seconds .* transform is: (.*)'
			line = line.replace('\n', '')
			match = re.search(match_text, line)
			if match:
				name = match.groups()[2]
				time = match.groups()[1]

				if name in self.results.keys():
					transform = self.results[name]
					transform.occurrences = transform.occurrences + 1
					transform.total_time = transform.total_time + float(time)
				else:
					transform = LongTransformsParser._TransformStatistics(name, time)
					self.results[name] = transform

	def print_results(self):
		total_time = 0.0
		if len(self.results.keys()) > 0:
			for t_name in self.results.keys():
				transform = self.results[t_name]
				name = transform.name
				if len(name) > 90:
					name = name[0:90] + "..."
				name_str = "Transform: {0}".format(name.ljust(100))
				avg_time = transform.total_time / transform.occurrences
				avg_time_str = "Average Time {0} seconds".format(avg_time).ljust(40)
				occurrences_str = "Occurrences {0}".format(transform.occurrences)
				total_time = total_time + transform.total_time
				print "{0}  /  {1}  /  {2}".format(name_str, avg_time_str, occurrences_str)
			print "Total time spent processing transforms = {0} seconds".format(total_time)
		else:
			print "No transforms found"

class LogAnalyzer(object):

	def __init__(self, file_names, parsers):
		self.file_names = file_names
		self.parsers = parsers

	def _process_line(self, line):
		for parser in self.parsers:
			parser.parse_line(line)

	def _process_log(self, file_name, parser):
		f = open(file_name)
		previous_line = ""
		for line in f:
			date_re = r'^2014-\d\d-\d\d \d\d:\d\d:\d\d'
			if re.search(date_re, line) is not None and len(previous_line) > 0:
				parser.parse_line(previous_line)
				previous_line = line
			else:
				previous_line = previous_line + line

		# Process line
		if previous_line is not None and len(previous_line) > 0:
			parser.parse_line(previous_line)

	def _print_results(self, file_name, parser):
		print '\n'
		print '-' * 100
		text = ' '*(50 - len(parser.name)/2) + parser.name
		print "{0}".format(text.ljust(100))
		print '-' * 100
		parser.print_results()
		print '-' * 100

	def analyze(self):
		for file_name in self.file_names:
			print "=" * 125
			text = ' '*(125/2 - len(file_name)/2) + file_name
			print "{0}".format(text)
			print "=" * 125
			for parser in self.parsers:
				parser.reset()
				self._process_log(file_name, parser)
				self._print_results(file_name, parser)
			print "=" * 125
			print '\n'
		

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print 'Error: wrong number of parameters.'
        print 'Usage: parse2.py <zeneventd_log_file>'
    else:
    	file_names = sys.argv[1:]
    	parsers = []
    	parsers.append(CatalogExceptionParser())
    	parsers.append(LongTransformsParser())
    	parsers.append(TimeStampIntervalParser())
    	LogAnalyzer(file_names, parsers).analyze()



