
from zenoss_client import ZenossClient

class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log_status_msg(msg, success=True, fill=False, width=80):
	if fill:
		msg = msg.ljust(width, '.')
	if success:
		print '{0} OK'.format(msg)
	else:
		print '{0} FAILED'.format(msg)

def can_connect_to_zenoss(zenoss_url, user, password):
	return ZenossClient(zenoss_url, user, password).login()