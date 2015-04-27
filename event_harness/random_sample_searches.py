
from common import log_status_msg, can_connect_to_zenoss
from test_harness import EventTestHarness

import argparse
import pickle

class SampleDataLoader(object):

	def load_from_pickle(self, path):
		sample_data = None
		try:
			sample_data = pickle.load(open(path, 'rb'))
		except Exception:
			sample_data = None
		return sample_data

def main(zenoss_url, summary_actions, archive_actions, n_requests, data_file, user, password):
	""" """
	print ""
	connection_status_msg = "Checking connectivity to Zenoss and credentials"
	data_status_msg = "Loading data samples from {0}".format(data_file)

	if can_connect_to_zenoss(zenoss_url, user, password):
		log_status_msg(connection_status_msg, fill=True)
		sample_data = SampleDataLoader().load_from_pickle(data_file)
		if sample_data:
			log_status_msg(data_status_msg, fill=True)

			tasks = []
			if summary_actions > 0:
				summary_context = {}
				summary_context['sample_data'] = sample_data
				summary_context['summary'] = True
				tasks.append((summary_actions, 'random_sample_filter', summary_context))
			if archive_actions > 0:
				archive_context = {}
				archive_context['sample_data'] = sample_data
				archive_context['summary'] = False
				tasks.append( (archive_actions, 'random_sample_filter', archive_context) )

			if tasks > 0:
				EventTestHarness(tasks, n_requests, zenoss_url, user, password).run()
			else:
				print "\nERROR: No tasks found.\n"
		else:
			log_status_msg(data_status_msg, success=False, fill=True)
			print "\nERROR: Could not load sample data from {0}.\n".format(data_file)
	else:
		log_status_msg(connection_status_msg, success=False, fill=True)
		print "\nERROR: Could not log in Zenoss. Please check zenoss host and credentials. [ Zenoss host = {0} / User = {1} / Password = {2} ]\n".format(zenoss_url, user, password)


def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(version="1.0",
                                     description="Sends radom event requests to a zenoss instance to test performance.")
    parser.add_argument("-z", "--zenoss_url", action="store", default='localhost', type=str,
                        help="Zenoss url including port")
    parser.add_argument("-n", "--n_requests", action="store", default=10, type=int,
                        help="Number of radom requests each worker will send.")
    parser.add_argument("-s", "--summary_workers", action="store", default=0, type=int,
                        help="Number of simultaneous workers sending summary requests to Zenoss.")
    parser.add_argument("-a", "--archive_workers", action="store", default=1, type=int,
                        help="Number of simultaneous workers sending archive requests to Zenoss.")
    parser.add_argument("-d", "--data_file", action="store", default='./sample_data.pickle', type=str,
                        help="Pickle containing sample data to build request filters.")
    parser.add_argument("-u", "--user", action="store", default='admin', type=str,
                        help="User to log in Zenoss.")
    parser.add_argument("-p", "--password", action="store", default='zenoss', type=str,
                        help="Password to log in Zenoss.")
    return vars(parser.parse_args())


if __name__ == '__main__':
	""" """
	cli_options = parse_options()
	zenoss_url = cli_options.get('zenoss_url')
	n_requests = cli_options.get('n_requests')
	data_file = cli_options.get('data_file')
	user = cli_options.get('user')
	password = cli_options.get('password')

	archive_actions = cli_options.get('archive_workers')
	summary_actions = cli_options.get('summary_workers')
	actions = [ (archive_actions, "filter_archive"), (summary_actions, "filter_summary") ]

	main(zenoss_url, summary_actions, archive_actions, n_requests, data_file, user, password)

