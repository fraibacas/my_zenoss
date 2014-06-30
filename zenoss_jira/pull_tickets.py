
import os
import getpass
import cgi, json
import xlwt

from jira.client import JIRA

class JiraConnectionError(Exception):
	pass

class SpreadSheetCell(object):

	def __init__(self, data='', color=''):
		self.data = data
		self.color = color

class SpreadSheetWriter(object):

	SPREAD_SHEET_FILE = "./ports.xls"

	def __init__(self):
		self.book = xlwt.Workbook()

	def _get_cell_style(self, color):
		return xlwt.easyxf('pattern: pattern solid, fore_colour {0};'.format(color))

	def _write_row(self, sheet, row, col, data):
		c = col
		for d in data:
			if isinstance(d, SpreadSheetCell):
				if d.color:
					style = self._get_cell_style(d.color)
					sheet.write(row, c, d.data, style)
				else:
					sheet.write(row, c, d.data)
				c = c + 1

	def write_to_spreadsheet(self, data, sheet_name):
		"""
		Writes data to a SpreadSheet. Data is an array of arrays with the data to write.
		"""
		sheet = self.book.add_sheet(sheet_name)
		row = 1
		col = 1
		for d in data:
			self._write_row(sheet, row, col, d)
			row = row + 1
		self.book.save(SpreadSheetWriter.SPREAD_SHEET_FILE)

class L3Ticket(object):
	 def __init__(self):
	 	self.summary = ''
	 	self.fixes = {}

	 def to_spreadsheet(self, versions_order = [ '424', '425', '4x', '5x' ]):
	 	data = [ SpreadSheetCell(data='{0}'.format(self.summary)) ]
	 	for version in versions_order:
	 		link = ''
	 		color = ''
			if version in self.fixes.keys() and self.fixes[version]:
				ports = self.fixes[version]
				if len(ports) == 1 and ports[0]:
					jira = ports[0]
				 	link = u'=HYPERLINK("http://jira.zenoss.com/jira/browse/{0}","{1}")'.format(jira.key, jira.key)
				 	if jira.fields.status.name == 'Closed':
				 		color = 'light_green'
				 	elif jira.fields.status.name == 'Awaiting Verification':
				 		color = 'light_yellow'
				else:
					links = []
					for j in ports:
						if j:
							links.append('{0}'.format(j.key))
					link = ', '.join(links)
			data.append(SpreadSheetCell(data=link, color=color))
		return data

class ZenossL3JiraProxy(object):

	PROJECT = 'ZEN'

	VERSION_IDS = {
		'424' : '10722',
		'425' : '11101',
		'4x'  : '10717',
		'5x'  : '10601'
	}

	def __init__(self):
		self.jira_proxy = None
		self.project = ZenossL3JiraProxy.PROJECT
		self.versions = ZenossL3JiraProxy.VERSION_IDS.keys()
		self.version_ids = ZenossL3JiraProxy.VERSION_IDS

	def connect_to_jira(self):
		""" """
		jira_proxy = None
		options = {
			'server': 'https://jira.zenoss.com'
		}
		try:
			#user = raw_input("User: ")
			#password = getpass.getpass("Password: ")
			user = os.environ['USER']
			password = os.environ['PASS']
			jira_proxy = JIRA(options, basic_auth=(user, password))
		except:
			raise JiraConnectionError()

		self.jira_proxy = jira_proxy

	def get_closed_tickets_since(self, version, date):
		'''
		returns tickets that were closed on or after date
		date is in the format 2010/12/12 
		'''
		version_id = self.version_ids[version]
		query = 'project = "{0}" and fixVersion = "{1}" and status = "closed" and updated >= "{2}" order by updated asc'.format(self.project, version_id, date)
		return self.jira_proxy.search_issues(query, startAt=0, maxResults=1000)

	def find_port(self, ticket, version):
		version_id = self.version_ids[version]
		summary = json.dumps(ticket.fields.summary)
		query = 'project = "{0}" and fixVersion = "{1}" and summary ~ {2}'.format(self.project, version_id, summary)
		return self.jira_proxy.search_issues(query, startAt=0, maxResults=500)

	def get_ports_since(self, date_since, version = '424', port_to_versions = ['425', '4x', '5x']):
		""" """
		ports_found = 0
		errors = 0
		date_since = cgi.escape(date_since)
		closed_in_version = self.get_closed_tickets_since(version, date_since)

		tickets = []

		for jira in closed_in_version:
			ticket = L3Ticket()
			ticket.summary = jira.fields.summary
			ticket.fixes[version] = [ jira ]
			print 'Searching for ports for {0}: {1}'.format(jira.key, jira.fields.summary)
			for port_to_version in port_to_versions:
				port = None
				try:
					port = self.find_port(jira, port_to_version)
					if port:
						ports_found = ports_found + 1
				except Exception as e:
					errors = errors + 1
				if not isinstance(port, list):
					port = [ port ]
				ticket.fixes[port_to_version] = port
			tickets.append(ticket)

		print 'Found {0} {1} closed tickets since {2}'.format(len(closed_in_version), version, date_since)
		print 'Found {0} ports. Got {1} erros querying Jira'.format(ports_found, errors)
		return tickets

def main():

	jira = ZenossL3JiraProxy()
	try:
		jira.connect_to_jira()
	except:
		print '\n\t %%% ERROR: Could not connect to Jira. Check user/pass %%% \n'
	else:
		#tickets = jira.get_ports_since('2014/01/01')
		tickets = jira.get_ports_since('2014/01/01')
		rows = []
		header = [ SpreadSheetCell(data='Description'),
				   SpreadSheetCell(data='4.2.4'),
				   SpreadSheetCell(data='4.2.5'), 
				   SpreadSheetCell(data='4.X'), 
				   SpreadSheetCell(data='4.5') ]
		rows.append(header)
		for ticket in tickets:
			row = ticket.to_spreadsheet()
			row.append('')
			rows.append(row)
		SpreadSheetWriter().write_to_spreadsheet(rows, 'Tickets')
		

if __name__ == '__main__':

	main()




