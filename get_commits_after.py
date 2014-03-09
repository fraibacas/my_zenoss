
import os
import sys
import xlwt

DEBUG = True

# Specific stuff for 4.2.5 CA2 Rebase
INITIAL_POPULATE_COMMIT = "938da9a088d496d39846dbdd1e62955ac77951e2"
COMMITS_TO_EXCLUDE = [ 	"9edd2580bb8134a513e6614de7973b979f1dd39b", #Changing GA to 2070 in yamls
						"d251844154f3e618b81f553d7d7c3d833e004712", #Dsabling CSA for now
						"3bd3e4f318e112f167325b260c953ae1c927070b", #ZEN-10259: Fix issue with migrate scripts being incorrectly versioned & the schema version being incorrectly bumped in 4.2.5
						"ed585fee0f4d2edf122742fc3f4cf5884ffd9a1b", #Revert "Dsabling CSA for now"
]
# End of Specific stuff for 4.2.5 CA2 Rebase

GIT_LOG_FIELD_SEPARATOR = "@=@"
GIT_LOG_ALL_COMMITS_COMMAND = "git log --pretty=format:'%H{0}%an{1}%ad{2}%s' --date=iso".format(GIT_LOG_FIELD_SEPARATOR, GIT_LOG_FIELD_SEPARATOR, GIT_LOG_FIELD_SEPARATOR)
GIT_LOG_MERGE_COMMITS_COMMAND = GIT_LOG_ALL_COMMITS_COMMAND + " --merges"
COMMITS_FILE = "/tmp/commits.tmp"
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
	exit_code = os.system(command)


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
		self.commits = []
		self.merge_commits = []

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

	def _process_git_log_output(self):
		commits = []
		with open(COMMITS_FILE) as file:
			for line in file:
				commit = self._parse_commit_log_line(line.strip())
				if commit is None:
					log("Commit line could not be decoded {0}".format(line))
				else:
					commits.append(commit)
		return commits

	def load_commits(self):
		execute_command(GIT_LOG_ALL_COMMITS_COMMAND, redirect_output=COMMITS_FILE)
		self.commits = self._process_git_log_output()
		
		execute_command(GIT_LOG_MERGE_COMMITS_COMMAND, redirect_output=COMMITS_FILE)
		self.merge_commits = self._process_git_log_output()

	def get_commits(self, commits_after=None, commits_to_exclude=[], exclude_merge_commits=True):
		"""
		Gets all commits after commits_after excluding merge commits and commits
		that are in commits_to_exclude. Returns a list of Commit objects
		"""
		commits = []

		if exclude_merge_commits:
			for c in self.merge_commits:
				commits_to_exclude.append(c.hash)

		for commit in self.commits:
			if commits_after is not None and  commit.hash == commits_after:
				break
			elif commit.hash not in commits_to_exclude:
				commits.append(commit)

		return commits

class CherryPickProcessor(object):

	def cherry_pick_commits(commits):
		for c in commits:
			pass

class SpreadSheetWriter(object):

	def __init__(self):
		self.book = xlwt.Workbook()

	def _write_row(self, sheet, row, col, data):
		c = col
		for d in data:
			sheet.write(row, c, d)
			c = c + 1

	def export_commits_list(self, commits, sheet):
		sheet = self.book.add_sheet(sheet)
		row = 1
		col = 1
		header = [ "Date", "Hash", "Dev", "Comment" ]
		self._write_row(sheet, row, col, header)
		row = row + 1
		for c in commits:
			data = [ c.date, c.hash, c.author, c.comment ]
			self._write_row(sheet, row, col, data)
			row = row + 1
		self.book.save(SPREAD_SHEET_FILE)

if __name__ == "__main__":
	"""	
	"""
	commit_retriever = CommitRetriever()
	commit_retriever.load_commits()
	# Gets all commits
	all_commits = commit_retriever.get_commits(exclude_merge_commits=False)
	# Gets all commits excluding merge pull request
	all_commits_no_merges = commit_retriever.get_commits()
	# Gets commits after CA1 Initial code population
	all_ca2_commits = commit_retriever.get_commits(commits_after=INITIAL_POPULATE_COMMIT)
	# Gets the commits to cherry pick for CA2
	ca2_commits_to_cherry_pick = commit_retriever.get_commits(commits_after=INITIAL_POPULATE_COMMIT, commits_to_exclude=COMMITS_TO_EXCLUDE)


	xls_writer = SpreadSheetWriter()
	xls_writer.export_commits_list(all_commits, "All Commits")
	xls_writer.export_commits_list(all_commits_no_merges, "All Commits no merges")
	xls_writer.export_commits_list(all_ca2_commits, "CA2 Relevant Commits")
	xls_writer.export_commits_list(ca2_commits_to_cherry_pick, "Commits to CherryPick")



