
from common import log_status_msg, can_connect_to_zenoss
from test_harness import EventTestHarness

import argparse

def main(zenoss_url, user, password, workers, n_requests):
	""" """
	print ""
	connection_status_msg = "Checking connectivity to Zenoss and credentials"

	if can_connect_to_zenoss(zenoss_url, user, password):
		log_status_msg(connection_status_msg, fill=True)
		tasks = [ (workers, "random_action", {}) ]
		if workers > 0 and n_requests > 0:
			EventTestHarness(tasks, n_requests, zenoss_url, user, password).run()
	else:
		log_status_msg(connection_status_msg, success=False, fill=True)
		print "\nERROR: Could not log in Zenoss. Please check zenoss host and credentials. [ Zenoss host = {0} / User = {1} / Password = {2} ]\n".format(zenoss_url, user, password)

def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(version="1.0",
                                     description="Performs radom actions on events to a zenoss instance.")
    parser.add_argument("-z", "--zenoss_url", action="store", default='localhost', type=str,
                        help="Zenoss url including port")
    parser.add_argument("-n", "--n_requests", action="store", default=10, type=int,
                        help="Number of radom requests each worker will send.")
    parser.add_argument("-w", "--workers", action="store", default=1, type=int,
                        help="Number of simultaneous workers performing actions to Zenoss.")
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
	user = cli_options.get('user')
	password = cli_options.get('password')
	workers = cli_options.get('workers')

	main(zenoss_url, user, password, workers, n_requests)