#!/opt/zenoss/bin/python

def print_job(job):
	title = ' Running Job found : {0} '.format(job.id)
	print '-' * len(title)
	print title
	print '-' * len(title)
	print ''.join(job.getLog().readlines())
	print '-' * len(title)

jobs = dmd.JobManager.jobs.objectValues()

running_jobs = []

print 'Searching for running jobs...'
for j in jobs:
	if j.started is not None and j.finished is None:
		running_jobs.append(j)
		

if len(running_jobs) == 0:
	print 'No running jobs found!'
else:
	for job in running_jobs:
		print_job(job)

