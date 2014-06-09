
import subprocess
import re
import time
import datetime
import os

def execute_command(command):
    """
    Params: command to execute
    Return: tuple containing the stout and stderr of the command execution
    """
    #print 'Executing ....' + command
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    return (stdout, stderr)

class ZopeInfoRetriever(object):

	COMMAND = "zenwebserver status -v"
	STATUS_REGEX = '(?P<name>.*) status (\s+)\[(?P<status>.+)\]'
	PID_PORT_REGEX = 'Running \(pid (?P<pid>\d+)\), Listening \(port (?P<port>.*)\)'
	def __init__(self):
		pass

	def _execute_regex(self, expr, line):
		results = {}
		regex = re.compile(expr)
		match = regex.search(line)
		if match:
			results = match.groupdict()
		return results

	def _match_status_line(self, line):
		return self._execute_regex(ZopeInfoRetriever.STATUS_REGEX, line)

	def _match_pid_line(self, line):
		return self._execute_regex(ZopeInfoRetriever.PID_PORT_REGEX, line)

	def _parse_command_output(self, output):
		zopes = []
		zope = None
		for line in output.split('\n'):
			status_line_results = self._match_status_line(line)
			if status_line_results:
				zope = ZopeInfo()
				zope.name = status_line_results.get('name', '')
				zope.status = status_line_results.get('status', '')
				if 'UP' in zope.status:
					zope.running = True
				else:
					zopes.append(zope)
					zope = None
			else:
				pid_line_results = self._match_pid_line(line)
				if pid_line_results:
					zope.pid = pid_line_results.get('pid', '')
					zope.port = pid_line_results.get('port', '')
					zope.id = zope.port
					zopes.append(zope)
		return zopes

	def getZopesInfo(self):
		""" """
		zopes = []
		output, stderr = execute_command(ZopeInfoRetriever.COMMAND)
		if len(stderr) > 0:
			print 'error'
		else:
			zopes = self._parse_command_output(output)
		return zopes

class ProcessInfoRetriever(object):

	COMMAND = 'ps -p {0} -o %cpu,%mem,etime,cmd | tail -n +2'

	def __init__(self):
		pass

	def get_process_info(self, pid):
		info = {}
		command = ProcessInfoRetriever.COMMAND.format(pid)
		output, stderr = execute_command(command)
		if len(stderr) == 0 and len(output) > 0:
			data = output.split()
			if len(data) >= 3:
				info['pid'] = pid
				info['cpu'] = data[0]
				info['mem'] = data[1]
				info['etime'] = data[2]
				info['cmd'] = ' '.join(data[3:])
		return info

class ZopeLogRetriever(object):

	SEPARATOR = '@$@'

	FIELDS = []
	FIELDS.append('log_timestamp')
	FIELDS.append('trace_type')
	FIELDS.append('start_time')
	FIELDS.append('server_name')
	FIELDS.append('server_port')
	FIELDS.append('path_info')
	FIELDS.append('method')
	FIELDS.append('client')
	FIELDS.append('http_host')

	def __init__(self):
		pass

	def _parse_line(self, line):
		parsed_line = {}
		line = line.strip()
		data = line.split(ZopeLogRetriever.SEPARATOR)
		if len(data) > 0:
			parsed_line['fingerprint'] = (ZopeLogRetriever.SEPARATOR).join(data[2:])
			for field, value in zip(ZopeLogRetriever.FIELDS, data):
				parsed_line[field] = value
		return parsed_line

	def read_log(self):
		lines = []
		with open("/opt/zenoss/log/paco.log") as f:
			for line in f:
				parsed_line = self._parse_line(line)
				lines.append(parsed_line)
		return lines

#------------------------------------------------------------------------------------------------

class ZopeInfo(object):

	def __init__(self):
		self.id = ''
		self.name = ''
		self.pid = ''
		self.status = ''
		self.running = False
		self.port = ''
		#Zope process info
		self.cpu = '-1'
		self.mem = '-1'
		self.cmd = ''
		self.running_for = ''
		#Zope Assigments
		self.assignments = {}

	def add_assignment(self, assignment):
		if 'START' in assignment.trace_type:
			self.assignments[assignment.fingerprint] = assignment
		elif 'END' in assignment.trace_type and assignment.fingerprint in self.assignments.keys():
			del self.assignments[assignment.fingerprint]

	def set_process_info(self, data):
		self.cpu = data.get('cpu', '')
		self.mem = data.get('mem', '')
		self.running_for = data.get('etime', '')
		self.cmd = data.get('cmd', '')

	def __str__(self):
		return 'port [{0}] / pid [{1}] / %cpu [{2}] / %mem [%{3}]'.format(self.port, self.pid, self.cpu, self.mem,)

class ZopeAssignment(object):

	def __init__(self, data):
		self.log_timestamp = data.get('log_timestamp', '')
		self.fingerprint = data.get('fingerprint', '')
		self.trace_type = data.get('trace_type', '')
		self.start_time = data.get('start_time', '')
		self.server_name = data.get('server_name', '')
		self.server_port = data.get('server_port', '')
		self.path_info = data.get('path_info', '')
		self.method = data.get('method', '')
		self.client = data.get('client', '')
		self.http_host = data.get('http_host', '')
		self.zope_id = self.server_port

class ZopesManager(object):

	def __init__(self):
		self.zopes = {}
		self.running_zopes = []

	def _get_zope_for_assignment(self, assignment):
		"""
		assigment: ZopeAssignment
		"""
		assignment_for = None
		for zope_id in self.running_zopes:
			zope = self.zopes.get(zope_id)
			if zope and assignment.zope_id in zope_id:
				assignment_for = zope
		return assignment_for

	def add_assignment(self, assignment):
		"""
		assigment: ZopeAssignment
		"""
		zope = self._get_zope_for_assignment(assignment)
		if zope:
			zope.add_assignment(assignment)

	def _set_zopes(self, zopes_list):
		for zope in zopes_list:
			self.zopes[zope.id] = zope
		self.running_zopes = [ z.id for z in zopes_list if 'Load balancer' not in z.name and z.running ]

	def load_zopes(self):
		self.zopes = {}

		zope_retriever = ZopeInfoRetriever()
		zopes = zope_retriever.getZopesInfo()
		self._set_zopes(zopes)

		process_info_retreiver = ProcessInfoRetriever()
		for zope in zopes:
			process_info = process_info_retreiver.get_process_info(zope.pid)
			zope.set_process_info(process_info)
			self.zopes[zope.id] = zope

	def load_zopes_assignments(self):
		if len(self.running_zopes) > 0:
			log_retreiver = ZopeLogRetriever()
			parsed_lines = log_retreiver.read_log()
			for data in parsed_lines:
				self.add_assignment(ZopeAssignment(data))
		else:
			print 'No running zopes found!'

	def print_zopes(self):
		for zid, zope in self.zopes.iteritems():
			print '{0} => {1}'.format(zid, zope)

	def print_running_zopes_stats(self):
		for zope_id in sorted(self.running_zopes):
			zope = self.zopes.get(zope_id)
			print 'Zope {0}'.format(zope)
			for fingerprint, assignment in zope.assignments.iteritems():
				print '      assignment {0}-{1}'.format(fingerprint, assignment.trace_type)
			print '\n------------------------------------------'


if __name__ == "__main__":

	while True:
		os.system('clear')
		zopes_manager = ZopesManager()
		#import pdb; pdb.set_trace()
		zopes_manager.load_zopes()
		zopes_manager.load_zopes_assignments()
		zopes_manager.print_running_zopes_stats()
		time.sleep(5)


