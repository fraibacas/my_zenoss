
import os
import re
import sys
import xlwt

DEBUG = True

def log(text, debug=False):
	""" G"""
	if not debug or (debug and DEBUG):
		print text

def execute_command(cmd, ignore_error=False, redirect_output=None):
	""" """
	command = cmd
	if redirect_output is not None:
		command = "{0} > {1}".format(command, redirect_output)
	exit_code = os.system(command)
	if exit_code == 0:
		log("Executing: {0}".format(command), True)
	else:
		log("\nERROR: Executing: {0}\n".format(command), True)
		if not ignore_error:
			sys.exit()
	return exit_code


class Commit(object):

	def __init__(self, hash, author, date, comment):
		self.hash = hash
		self.author = author
		self.date = date
		self.comment = comment

	def __str__(self):
		return "[{0}] [{1}] [{2}] [{3}]".format(self.date, self.hash, self.author,  self.comment)

class CommitRetriever(object):

	GIT_LOG_FIELD_SEPARATOR = "@=@"
	GIT_LOG_ALL_COMMITS_COMMAND = "git log --pretty=format:'%H{0}%an{1}%ad{2}%s' --date=iso".format(GIT_LOG_FIELD_SEPARATOR, GIT_LOG_FIELD_SEPARATOR, GIT_LOG_FIELD_SEPARATOR)
	GIT_LOG_MERGE_COMMITS_COMMAND = GIT_LOG_ALL_COMMITS_COMMAND + " --merges"
	COMMITS_FILE = "/tmp/commits.tmp"

	def __init__(self):
		self.commits = []
		self.merge_commits = []
		self._load_commits()

	def _parse_commit_log_line(self, line):
		"""
		Returns a line from the git log output and returns 
		Commit object
		"""
		commit = None
		fields = line.split(CommitRetriever.GIT_LOG_FIELD_SEPARATOR)
		if len(fields) == 4:
			commit = Commit(hash=fields[0], author=fields[1], date=fields[2], comment=fields[3])

		return commit

	def _process_git_log_output(self):
		commits = []
		with open(CommitRetriever.COMMITS_FILE) as file:
			for line in file:
				commit = self._parse_commit_log_line(line.strip())
				if commit is None:
					log("Commit line could not be decoded {0}".format(line))
				else:
					commits.append(commit)
		return commits

	def _load_commits(self):
		execute_command(CommitRetriever.GIT_LOG_ALL_COMMITS_COMMAND, redirect_output=CommitRetriever.COMMITS_FILE)
		self.commits = self._process_git_log_output()
		
		execute_command(CommitRetriever.GIT_LOG_MERGE_COMMITS_COMMAND, redirect_output=CommitRetriever.COMMITS_FILE)
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

	def cherry_pick_commits(self, commits):
		for c in commits:
			print "-"*100
			print "Cherry-Picking Commit {0}".format(c.hash)
			print "-"*100
			code = execute_command("git cherry-pick {0}".format(c.hash))

class SpreadSheetWriter(object):

	SPREAD_SHEET_FILE = "/tmp/commits.xls"

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
		self.book.save(SpreadSheetWriter.SPREAD_SHEET_FILE)

class RPSCodePopulator(object):
	"""
	    Populates the 4.2.5 RPS repo with a new version of the rpm in a test branch.
	"""

	BACKUP_BRANCH = "CA2_Backup"
	TEST_BRANCH = "test_branch"
	COMMIT_BEFORE_INITIAL_POPULATE_COMMIT = "2f4a25028ec83723fbb50bd2f8cad09c6c5225cc"
	INITIAL_POPULATE_COMMIT = "938da9a088d496d39846dbdd1e62955ac77951e2"
	COMMITS_TO_EXCLUDE = [ 	"9edd2580bb8134a513e6614de7973b979f1dd39b", #Changing GA to 2070 in yamls
							"d251844154f3e618b81f553d7d7c3d833e004712", #Dsabling CSA for now
							"3bd3e4f318e112f167325b260c953ae1c927070b", #ZEN-10259: Fix issue with migrate scripts being incorrectly versioned & the schema version being incorrectly bumped in 4.2.5
							"ed585fee0f4d2edf122742fc3f4cf5884ffd9a1b", #Revert "Dsabling CSA for now"
	]

	POPULATE_SCRIPT = "populate_src"
	NEW_BUILD_TAG="2108"
	TMP_FILE = "/tmp/ca2_rebase.tmp"

	def __init__(self):
		pass


	def _check_cwd(self):
		""" Check that the script is executed from 4.2.5-RPS/bin """
		cwd = os.getcwd()
		if not cwd.endswith("4.2.5-RPS/bin"):
			log("\nERROR: This script has to be executed from the bin dir of the 4.2.5_RPS repo\n")
			sys.exit()

	def _create_backup_branch(self):
		""" Creates a backup branch """
		self.print_message("Checking out {0} branch".format(RPSCodePopulator.BACKUP_BRANCH))
		code = execute_command("git checkout -f master")
		code = execute_command("git checkout -f {0}".format(RPSCodePopulator.BACKUP_BRANCH), ignore_error=True)
		if code != 0:
			log("Branch {0} does not exists. Lets's create it.".format(RPSCodePopulator.BACKUP_BRANCH))
			execute_command("git checkout -f -b {0}".format(RPSCodePopulator.BACKUP_BRANCH))

	def _retrieve_commits_to_cherry_pick(self):
		""" Retrieving commits """
		self.print_message("Retrieving commits")
		commit_retriever = CommitRetriever()
		# Gets all commits
		#all_commits = commit_retriever.get_commits(exclude_merge_commits=False)
		# Gets all commits excluding merge pull request
		#all_commits_no_merges = commit_retriever.get_commits()
		# Gets commits after CA1 Initial code population
		#all_ca2_commits = commit_retriever.get_commits(commits_after=INITIAL_POPULATE_COMMIT)
		# Gets the commits to cherry pick for CA2
		ca2_commits_to_cherry_pick = commit_retriever.get_commits(commits_after=RPSCodePopulator.INITIAL_POPULATE_COMMIT, 
																  commits_to_exclude=RPSCodePopulator.COMMITS_TO_EXCLUDE)
		return ca2_commits_to_cherry_pick

	def _switch_to_test_branch(self):
		""" Creates and switches to TEST_BRANCH """
		self.print_message("Checking out {0}".format(RPSCodePopulator.TEST_BRANCH))
		code = execute_command("git branch -D {0}".format(RPSCodePopulator.TEST_BRANCH), ignore_error=True)
		if code != 0:
			log("Branch {0} does not exists. Lets's create it.".format(RPSCodePopulator.TEST_BRANCH))
		code = execute_command("git branch {0}".format(RPSCodePopulator.TEST_BRANCH))
		code = execute_command("git checkout -f {0}".format(RPSCodePopulator.TEST_BRANCH))

	def _revert_branch_to_start_commit(self):
		""" Reset the branch to the commit right before the code population """
		self.print_message("Reverting branch to commit before '2070 Initial Load'")
		code = execute_command("git reset --hard {0}".format(RPSCodePopulator.COMMIT_BEFORE_INITIAL_POPULATE_COMMIT))

	def _update_populate_script_build_tag(self):
		""" Modify the populate script to use the new Build TAG """
		self.print_message("Adding new build TAG to {0} script".format(RPSCodePopulator.POPULATE_SCRIPT))
		
		TAG_PATTERN = 'TAG="zenoss-build-'
		with open(RPSCodePopulator.POPULATE_SCRIPT) as read_file:
			with open(RPSCodePopulator.TMP_FILE, "w") as write_file:
				for line in read_file:
					line_to_write = line
					if TAG_PATTERN in line:
						line_to_write = '{0}{1}"\n'.format(TAG_PATTERN, RPSCodePopulator.NEW_BUILD_TAG)
					write_file.write(line_to_write)
		execute_command("cp {0} ./{1}".format(RPSCodePopulator.TMP_FILE, RPSCodePopulator.POPULATE_SCRIPT))

		# Commit the changes
		code = execute_command("git add {0}".format(RPSCodePopulator.POPULATE_SCRIPT))
		commit_msg = "CA2_REBASE: Change Build TAG to {0}".format(RPSCodePopulator.NEW_BUILD_TAG)
		code = execute_command("git commit -m '{0}'".format(commit_msg))

	def _update_yamls_build_tag(self):
		""" Updates the yaml files with the new build tag """
		components = [ "core", "csa", "resmgr" ]
		for comp in components:
			file_path = "../etc/{0}.yaml".format(comp)
			pattern = "http://artifacts.zenoss.loc/releases/4.2.5/"
			pattern_re = '(\s*- http://artifacts.zenoss.loc/releases/4.2.5/)(\w*)(/\w*/zenoss_\w*-4.2.5-)(\d\d\d\d)(.el[56].x86_64.rpm\s*)'

			with open(file_path) as read_file:
				with open(RPSCodePopulator.TMP_FILE, "w") as write_file:
					for line in read_file:
						line_to_write = line
						if pattern in line:
							match = re.search(pattern_re, line)
							if match:
								line_to_write = match.groups()[0] + "ca2" + match.groups()[2] + RPSCodePopulator.NEW_BUILD_TAG + match.groups()[4]
						write_file.write(line_to_write)
				execute_command("cp {0} {1}".format(RPSCodePopulator.TMP_FILE, file_path))

			# git add modified file
			code = execute_command("git add {0}".format(file_path))

		# Commit the changes
		commit_msg = "CA2_REBASE: Change Build TAG to {0} in yamls".format(RPSCodePopulator.NEW_BUILD_TAG)
		code = execute_command("git commit -m '{0}'".format(commit_msg))


	def _update_build_tag_in_repo_files(self):
		""" Updates populate script and yaml files """
		self._update_populate_script_build_tag()
		self._update_yamls_build_tag()

	def _populate_code(self):
		""" Populates the repo with the code from the new build tag """
		self.print_message("Populating Repo with Build TAG {0}".format(RPSCodePopulator.NEW_BUILD_TAG))
		code = execute_command("./populate_src ")
		# Commit the changes
		code = execute_command("git add ../src/*")
		commit_msg = "CA2_REBASE: Populate code with TAG {0}".format(RPSCodePopulator.NEW_BUILD_TAG)
		code = execute_command("git commit -m '{0}'".format(commit_msg))

	def _cherry_pick_commits(self, commits):
		""" Cherry-pick commits """
		self.print_message("Cherry-Picking commits")
		cherry_pick_processor = CherryPickProcessor()
		cherry_pick_processor.cherry_pick_commits(commits[::-1])

	def populate(self):
		""" Do not change order of calls """
		self._check_cwd()
		self._create_backup_branch()
		commits = self._retrieve_commits_to_cherry_pick()
		self._switch_to_test_branch()
		self._revert_branch_to_start_commit()
		self._update_build_tag_in_repo_files()
		self._populate_code()
		self._cherry_pick_commits(commits)

		msgs = []
		print("\n\n")
		msgs.append("CA2 REBASE DONE in branch {0}!".format(RPSCodePopulator.TEST_BRANCH))
		msgs.append("Please push the changes to the repo and merge accordingly")
		msgs.append("THE END")
		self.print_message(msgs)

	def print_message(self, msg):
		WIDTH = 100
		print "="*WIDTH
		if not isinstance(msg, list):
			msg = [ msg ]
		for line in msg:
			print "{0}".format(line).center(WIDTH)
		print "="*WIDTH

if __name__ == "__main__":

	"""
	=============================================================================
	==> NOTICE: THIS SCRIPT MUST BE RUN FROM THE BIN DIR OF THE 4.2.5 REPO!!! <==
	=============================================================================
	""" 

	code_populator = RPSCodePopulator()
	code_populator.populate()

	"""  Writes spreadsheet with info about the commits cherry-picked
	xls_writer = SpreadSheetWriter()
	xls_writer.export_commits_list(all_commits, "All Commits")
	xls_writer.export_commits_list(all_commits_no_merges, "All Commits no merges")
	xls_writer.export_commits_list(all_ca2_commits, "CA2 Relevant Commits")
	xls_writer.export_commits_list(ca2_commits_to_cherry_pick, "Commits to CherryPick")
	"""



