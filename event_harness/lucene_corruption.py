
#############################################################################################
#
# Checks for uuids whose event status is not the same in lucene and in the database
#
#############################################################################################

from common import log_status_msg, can_connect_to_zenoss, ScriptConfiguration, BColors
from zenoss_client import ZenossClient

from collections import defaultdict

import argparse
import csv
import pymysql
import time
                

class EventUpdateTimeValidator(object):

    STATUS_TO_ID = {
        'New': 0,
        'Acknowledged': 1,
        'Suppressed': 2,
        'Closed': 3,
        'Cleared': 4,
        'Aged': 6
    }

    ID_TO_STATUS = {}
    for s_text, s_id in STATUS_TO_ID.iteritems():
        ID_TO_STATUS[s_id] = s_text
    STATUSES = [0, 1, 3, 4] # we only check new, ack, closed, and cleared events

    def __init__(self, config):
        self.config = config
        self.zenoss_client = None

    def get_lucene_events(self):
        """ returns dict {uuid: status} for all summary events """
        events = {}
        self.zenoss_client = ZenossClient(self.config.zenoss_url, self.config.zenoss_user, self.config.zenoss_password)

        request_info = {}
        request_info['keys'] = [ ]
        request_info['event_state'] = self.STATUSES
        response = self.zenoss_client.send_event_filter_request(request_info, archive=False)

        if response.get('success'):
            n_events = response.get('totalCount', -1)
            if n_events >= 0:
                start = time.time()
                #print "{0} events found in summary index (statuses new, ack, closed, and cleared). Retrieving uuids....".format(n_events)
                print "Retrieving new, ack, closed and cleared events from the index..."
                page_size = 1000
                request_info['keys'] = [ 'evid', 'eventState' ]
                request_info['limit'] = page_size
                request_info['event_state'] = self.STATUSES
                retrieved = 0
                for page in range(1, (n_events/page_size) + 2):
                    request_info['page'] = page
                    response = self.zenoss_client.send_event_filter_request(request_info, archive=False)
                    if response.get('success'):
                        evs = response.get('events', [])
                        for event in evs:
                            if event:
                                uuid = event['evid']
                                events[uuid] = self.STATUS_TO_ID[event['eventState']]
                                retrieved = retrieved + 1
                    else:
                        print "Could not retreive page {0}".format(page)
                print "Retrieving {0} events from index took {1} seconds".format(len(events), time.time() - start)
                start = time.time()
            else:
                print "Error retrieving events from lucene"
        return events

    def get_db_events(self, table="event_summary"):
        """ """
        start = time.time()
        print "Retrieving new, ack, closed and cleared events from the database..."
        conn = pymysql.connect(host=self.config.db_host, port=self.config.db_port,
                                   user=self.config.db_user, passwd=self.config.db_password, db=self.config.zep_db)
        cursor = conn.cursor()
        values = ', '.join([ str(status) for status in self.STATUSES ])
        sql = """SELECT BINARY_UUID_TO_STR(uuid), status_id FROM {0} WHERE status_id IN ({1});""".format(table, values)
        cursor.execute(sql)
        events = {}
        for evid, status in cursor.fetchall():
            events[evid] = status
        print "Retrieving {0} events from database took {1} seconds".format(len(events), time.time() - start)
        return events

    class _status(object):
        def __init__(self):
            self.index_status = -1
            self.db_status = -1

    def _validate(self, index_events, db_events):
        events = defaultdict(self._status)

        for uuid, status in index_events.iteritems():
            events[uuid].index_status = status

        for uuid, status in db_events.iteritems():
            events[uuid].db_status = status

        corrupt_events = {}
        for uuid, status in events.iteritems():
            if status.index_status!=-1 and status.db_status!=-1 and status.index_status != status.db_status:
                print "{0} / {1} - {2}".format(uuid, status.index_status, status.db_status)
                corrupt_events[uuid] = status

        return corrupt_events

    def _generate_csv(self, events):
        filename = "/tmp/corrupt_events.csv" #.format(int(time.time()))
        with open(filename, 'wb') as f:
            writer = csv.writer(f)
            writer.writerow( ('UUID', 'Index Status', 'DB Status') )
            for uuid, status in events.iteritems():
                row = (uuid, status.index_status, status.db_status)
                writer.writerow(row)
        return filename

    def validate(self):
        connection_status_msg = "Checking connectivity to Zenoss and credentials"
        print ''
        if can_connect_to_zenoss(self.config.zenoss_url, self.config.zenoss_user, self.config.zenoss_password):
            log_status_msg(connection_status_msg, success=True, fill=True)
            print ''
            index_events = self.get_lucene_events()
            print ''
            db_events = self.get_db_events()
            corrupt_events = self._validate(index_events, db_events)
            if len(corrupt_events) > 0:
                print "{0} corrupt events found".format(len(corrupt_events))
                self._generate_csv(corrupt_events)
                print "Corrupt events exported to /tmp/corrupt_events.csv"
            else:
                print "NO corrupt events found"
        else:
            log_status_msg(connection_status_msg, success=False, fill=True)

def parse_options():
    """ Defines command-line options for script """
    parser = argparse.ArgumentParser(description="Checks consistency between lucene and DB for event summary.")
    parser.add_argument("-z", "--zenoss_url", action="store", default='localhost', type=str,
                        help="Zenoss url including port")
    parser.add_argument("-u", "--user", action="store", default='admin', type=str,
                        help="User to log in Zenoss.")
    parser.add_argument("-p", "--password", action="store", default='zenoss', type=str,
                        help="Password to log in Zenoss.")
    parser.add_argument("-dbh", "--db_host", action="store", default='localhost', type=str,
                        help="Host where mysql is running")
    parser.add_argument("-dbp", "--db_port", action="store", default=13306, type=int,
                        help="Database port")
    parser.add_argument("-dbu", "--db_user", action="store", default='root', type=str,
                        help="Database user")
    parser.add_argument("-dbP", "--db_password", action="store", default='', type=str,
                        help="Database user's password")
    parser.add_argument("-db", "--zep_db", action="store", default='zenoss_zep', type=str,
                        help="Zep's database name")
    return vars(parser.parse_args())

def main(config):
    start = time.time()
    validator = EventUpdateTimeValidator(config)
    validator.validate()
    print "\nTotal execution time: {0} seconds".format(time.time()-start)

if __name__ == '__main__':
    """ """
    cli_options = parse_options()
    config = ScriptConfiguration()
    config.zenoss_url = cli_options.get('zenoss_url', config.zenoss_url)
    config.zenoss_user = cli_options.get('user', config.zenoss_user)
    config.zenoss_password = cli_options.get('password', config.zenoss_password)
    config.db_host = cli_options.get('db_host', config.db_host)
    config.db_port = cli_options.get('db_port', config.db_port)
    config.db_user = cli_options.get('db_user', config.db_user)
    config.db_password = cli_options.get('db_password', config.db_password)
    config.zep_db = cli_options.get('zep_db', config.zep_db)
    main(config)