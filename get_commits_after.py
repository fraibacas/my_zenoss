
import os
import sys
import xlwt

DEBUG = True

REPO_BRANCH="rps_candidate_99999999"
GIT_LOG_FIELD_SEPARATOR = "@=@"
#GIT_LOG_COMMAND = "git log --no-merges --pretty=format:'%H{0}%an{1}%ad{2}%s' --date=iso".format(GIT_LOG_FIELD_SEPARATOR, GIT_LOG_FIELD_SEPARATOR, GIT_LOG_FIELD_SEPARATOR)
GIT_LOG_COMMAND = "git log --pretty=format:'%H{0}%an{1}%ad{2}%s' --date=iso".format(GIT_LOG_FIELD_SEPARATOR, GIT_LOG_FIELD_SEPARATOR, GIT_LOG_FIELD_SEPARATOR)
COMMITS_FILE = "/tmp/commits.txt"
SPREAD_SHEET_FILE = "/tmp/commits.xls"

def log(text, debug=False):
	if not debug or (debug and DEBUG):
		print text


def execute_command(cmd, redirect_output=None):
	""" """
	command = cmd
	if redirect_output is not None:
		command = "{0} > {1}".format(command, redirect_output)
	log("Executing: {0}".format(command), True)
	os.system(command)


class Commit(object):

	def __init__(self, hash, author, date, comment):
		self.hash = hash
		self.author = author
		self.date = date
		self.comment = comment

	def __str__(self):
		return "[{0}] [{1}] [{2}] [{3}]".format(self.date, self.hash, self.author,  self.comment)

class CommitRetriever(object):

	def __init__(self):
		pass

	def _parse_commit_log_line(self, line):
		"""
		Returns a line from the git log output and returns 
		Commit object
		"""
		commit = None
		fields = line.split(GIT_LOG_FIELD_SEPARATOR)
		if len(fields) == 4:
			commit = Commit(hash=fields[0], author=fields[1], date=fields[2], comment=fields[3])

		return commit

	def get_commits(self, commits_after=None, commits_to_exclude=[]):
		"""
		Gets all commits after commits_after excluding merge commits and commits
		that are in commits_to_exclude. Returns a list of Commit objects
		"""
		commits = []
		execute_command(GIT_LOG_COMMAND, redirect_output=COMMITS_FILE)
		with open(COMMITS_FILE) as file:
			for line in file:
				commit = self._parse_commit_log_line(line.strip())
				if commit is None:
					log("Commit line could not be decoded {0}".format(line))
				else:
					if commits_after is not None and  commit.hash == commits_after:
						break
					elif commit.hash not in commits_to_exclude:
						commits.append(commit)
		return commits

class SpreadSheetWriter(object):

	def _write_row(self, sheet, row, col, data):
		c = col
		for d in data:
			sheet.write(row, c, d)
			c = c + 1

	def export_commits_list(self, commits):
		book = xlwt.Workbook()
		sheet = book.add_sheet("Commits")
		row = 1
		col = 1
		header = [ "Date", "Hash", "Dev", "Comment" ]
		self._write_row(sheet, row, col, header)
		row = row + 1
		for c in commits:
			data = [ c.date, c.hash, c.author, c.comment ]
			self._write_row(sheet, row, col, data)
			row = row + 1
		book.save(SPREAD_SHEET_FILE)


if __name__ == "__main__":
	"""
	
	"""
	#if len(sys.argv) > 1:
	initial_populate_commit = "938da9a088d496d39846dbdd1e62955ac77951e2"
	commit_retriever = CommitRetriever()
	#commits = commit_retriever.get_commits(commits_after=initial_populate_commit)
	commits = commit_retriever.get_commits()
	xls_writer = SpreadSheetWriter()
	xls_writer.export_commits_list(commits)
	for c in commits: print c

