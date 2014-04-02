
import sys

import xlwt

class RawEvent(object):

	def __init__(self):
		null = "NULL"
		self.queue = null
		self.message_count = null
		self.monitor = null
		self.agent = null
		self.summary = null
		self.timestamp = null
		self.severity = null

	def __str__(self):

		return '{0}/{1}/{2}/{3}/{4}/{5}'.format(self.message_count, self.queue, self.monitor, self.agent, self.summary, self.timestamp)

class DumpProcessor(object):

	def __init__(self):
		self.events = []
		self.events_per_monitor_and_agent = {}
		self.events_per_monitor = {}
		self.monitors_sorted_by_number_of_events = []

	def process_dump(self, file_name):
		""" """
		NEW_EVENT_TOKEN = "X-Protobuf-FullName"
		MONITOR_TOKEN = '"monitor":'
		SUMMARY_TOKEN = '"summary":'
		AGENT_TOKEN = '"agent":'
		TIMESTAMP_TOKEN = '"created_time":'
		QUEUE_TOKEN = 'X-Queue-Name:'
		MESSAGE_COUNT_TOKEN = 'X-Message-Count:'
		SEVERITY_TOKEN = '"severity":'

		self.events = []
		with open(file_name) as file:
			event = None
			for line in file:
				line = line.strip()
				if NEW_EVENT_TOKEN in line:
					if event is not None:
						self.events.append(event)
					event = RawEvent()
				else:
					if MONITOR_TOKEN in line:
						event.monitor = line.split(':')[1].strip().strip('",')
					elif SEVERITY_TOKEN in line: 
						event.severity = line.split(':')[1].strip().strip('",')
					elif QUEUE_TOKEN in line: 
						event.queue = line.split(':')[1].strip().strip('",')
					elif MESSAGE_COUNT_TOKEN in line: 
						event.message_count = line.split(':')[1].strip().strip('",')
					elif SUMMARY_TOKEN in line:
						event.summary = line.split(':')[1].strip().strip('",')
					elif AGENT_TOKEN in line:
						event.agent = line.split(':')[1].strip().strip('",')
					elif TIMESTAMP_TOKEN in line: 
						event.timestamp = line.split(':')[1].strip().strip('",')
			if event is not None:
				self.events.append(event)

		self.events_per_monitor_and_agent = {}
		for event in self.events:
			monitor = event.monitor
			agent = event.agent
			events_by_agent = self.events_per_monitor_and_agent.get(monitor, {})
			if agent in events_by_agent.keys():
				events_by_agent[agent].append(event)
			else:
				events_by_agent[agent] = [ event ]
			self.events_per_monitor_and_agent[monitor] = events_by_agent

		self.events_per_monitor = {}
		for monitor, events_per_agent in self.events_per_monitor_and_agent.iteritems():
			all_events = []
			for agent, events in events_per_agent.iteritems():
				all_events += events
			self.events_per_monitor[monitor] = all_events

		self.monitors_sorted_by_number_of_events = []
		event_count_per_monitor = {}
		for monitor, events_per_monitor in self.events_per_monitor.iteritems():
			event_count_per_monitor[monitor] = len(events_per_monitor)
		self.monitors_sorted_by_number_of_events = sorted(event_count_per_monitor, key = event_count_per_monitor.get)

	def get_report_events_count_per_monitor(self):
		""" Returns list of tuples (monitor, event_count) """
		report = []
		for monitor in self.monitors_sorted_by_number_of_events:
			report.append((monitor, len(self.events_per_monitor[monitor])))
		return report

	def get_report_events_per_monitor_and_agent(self):
		""" returns tuple (monitor agent events_per_agent)"""
		report = []
		for monitor in self.monitors_sorted_by_number_of_events:
			events_per_agent = {}
			for agent, events in self.events_per_monitor_and_agent[monitor].iteritems():
				events_per_agent[agent] = len(events)
			agents_sorted_by_events = sorted(events_per_agent, key = events_per_agent.get)
			for agent in agents_sorted_by_events:
				report.append( (monitor, agent, events_per_agent[agent]))
		return report

class SpreadSheetWriter(object):

	SPREAD_SHEET_FILE = "./rabbitmq_dump_report.xls"

	def __init__(self):
		self.book = xlwt.Workbook()


	def _write_row(self, sheet, row, col, data):
		c = col
		for d in data:
			sheet.write(row, c, d)
			c = c + 1

	def export_data(self, events_per_monitor, events_per_monitor_and_agent):
		""" """
		sheet = self.book.add_sheet("RabbitMQ analysis")

		row = 1
		col = 1
		""" Exports events per monitor """
		header = [ "Collector", "Events" ]
		self._write_row(sheet, row, col, header)
		row = row + 1
		for d in events_per_monitor:
			data = [ d[0], d[1] ]
			self._write_row(sheet, row, col, data)
			row = row + 1

		row = row + 5

		""" Exports events per monitor and agent"""

		header = [ "Collector", "Agent", "Events" ]
		self._write_row(sheet, row, col, header)
		row = row + 1
		for d in events_per_monitor_and_agent:
			data = [ d[0], d[1], d[2] ]
			self._write_row(sheet, row, col, data)
			row = row + 1

		self.book.save(SpreadSheetWriter.SPREAD_SHEET_FILE)

def print_title(title):
    print "="*60
    print title.center(60)
    print "="*60

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print 'Error: wrong number of parameters.'
        print 'Usage: process_rabbitmq_dump.py <rabbitmq_dump_file>'
    else:
    	file_name = sys.argv[1]
    	processor = DumpProcessor()
    	processor.process_dump(file_name)

    	print_title("Number of events in the dump: {0}".format(len(processor.events)))

    	""" EVENTS PER MONITOR """
    	print_title("EVENTS PER MONITOR")
    	events_per_monitor = processor.get_report_events_count_per_monitor()
    	for monitor, count in events_per_monitor:
    		print "Collector: {0}  Number of Events: {1}".format(monitor.ljust(30), count)

    	""" EVENTS PER MONITOR AND AGENT """
    	print_title("EVENTS PER MONITOR AND AGENT")

    	events_per_monitor_and_agent = processor.get_report_events_per_monitor_and_agent()
    	for monitor, agent, events_per_agent in events_per_monitor_and_agent:
    		print 'collector: {0} agent: {1} number of events: {2}'.format(monitor.ljust(30), agent.ljust(15), events_per_agent)

    	print_title("GENERATING SPREADSHEET")
	SpreadSheetWriter().export_data(events_per_monitor, events_per_monitor_and_agent)
