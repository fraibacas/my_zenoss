
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

	COMMAND = 'ps -p {0} -o %cpu,%mem,cmd | tail -n +2'

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
				info['cmd'] = ' '.join(data[2:])

		return info

class ZopeLogRetriever(object):

	SEPARATOR = '@$@'

	FIELDS = []
	FIELDS.append('Log_Timestamp')
	FIELDS.append('Trace_Type')
	FIELDS.append('Timestamp')
	FIELDS.append('Server_Name')
	FIELDS.append('Server_Port')
	FIELDS.append('Path_Info')
	FIELDS.append('Method')
	FIELDS.append('Client')
	FIELDS.append('HTTP_Host')

	def __init__(self):
		pass

	def _parse_line(self, line):
		parsed_line = {}
		line = line.strip()
		data = line.split(ZopeLogRetriever.SEPARATOR)
		if len(data) > 0:
			#import pdb; pdb.set_trace()
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
		self.cmd = data.get('cmd', '')

	def __str__(self):
		return 'port [{0}] / pid [{1}] / %cpu [{2}] / %mem [%{3}]'.format(self.port, self.pid, self.cpu, self.mem,)

class ZopeAssignment(object):

	def __init__(self, data):
		self.log_timestamp = data.get('Log_Timestamp', '')
		self.fingerprint = data.get('fingerprint', '')
		self.trace_type = data.get('Trace_Type', '')
		self.timestamp = data.get('Timestamp', '')
		self.server_name = data.get('Server_Name', '')
		self.server_port = data.get('Server_Port', '')
		self.path_info = data.get('Path_Info', '')
		self.method = data.get('Method', '')
		self.client = data.get('Client', '')
		self.http_host = data.get('HTTP_Host', '')
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
		for zope_id, zope in self.zopes.iteritems():
			if assignment.zope_id in zope_id:
				assignment_for = zope
		return assignment_for

	def add_assignment(self, assignment):
		"""
		assigment: ZopeAssignment
		"""
		zope = self._get_zope_for_assignment(assignment)
		if zope:
			zope.add_assignment(assignment)
		else:
			print 'Error: could not find zope for assignment'

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
			#parsed_lines = parsed_lines[::-1]
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
		zopes_manager.load_zopes()
		zopes_manager.load_zopes_assignments()
		zopes_manager.print_running_zopes_stats()

		if True: #running_zopes:
			pass
			"""
			# Retrieve cpu and mem usage for each zope
			processes_info = {}
			for zope in running_zopes:
				process_info = process_info_retreiver.get_process_info(zope.pid)
				zope.set_process_info(process_info)

			#print 'Loading log file....'
			#print datetime.datetime.now()
			parsed_lines = log_retreiver.read_log()
			parsed_lines = parsed_lines[::-1]
			#print datetime.datetime.now()

			for data in parsed_lines:
				zopes_manager.add_assignment(ZopeAssignment(data))

			"""
			"""
			zopes_assignments = {}
			for data in parsed_lines:
				if len(zopes_assignments.keys()) == len(running_zopes):
					break
				else:
					server_port = data.get('Server_Port', '')
					for zope in running_zopes:
						if server_port in zope.port and zope not in zopes_assignments.keys():
							zopes_assignments[zope] = data

			if zopes_assignments:
				for zope in zopes_assignments.keys():
					data = zopes_assignments[zope]
					timestamp = data.get('Log_Timestamp', '')
					path = data.get('Path_Info', '')
					method = data.get('Method', '')
					url = '{0}#{1}'.format(path, method)
					zope_info = processes_info.get(zope.pid)
					cpu = zope_info.get('cpu', '')
					mem = zope_info.get('mem', '')
					print 'Server: {0}  Time:{1} %CPU: {2} %MEM: {3} Resource: {4}'.format(zope.port.ljust(20), timestamp.ljust(30), cpu.ljust(10), mem.ljust(10), url.ljust(150) )
			print '\n'*5
			"""
			time.sleep(5)
		else:
			print 'Error: zenwebserver is not running...'
			time.sleep(5)


