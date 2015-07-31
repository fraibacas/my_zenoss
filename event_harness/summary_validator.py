#######################################################################################
#
# Checks for uuids that are in lucene and not in the database
#
#######################################################################################

from common import log_status_msg, can_connect_to_zenoss, ScriptConfiguration, BColors
from zenoss_client import ZenossClient

import argparse
import csv
import pymysql
import time

class SummaryIndexIntegrityChecker(object):

    def __init__(self, config):
        self.config = config
        self.zenoss_client = None

    def get_lucene_uuids(self):
        events = []
        self.zenoss_client = ZenossClient(self.config.zenoss_url, self.config.zenoss_user, self.config.zenoss_password)

        request_info = {}
        request_info['keys'] = [ ]
        response = self.zenoss_client.send_event_filter_request(request_info, archive=False)

        if response.get('success'):
            n_events = response.get('totalCount', -1)
            if n_events >= 0:
                start = time.time()
                print "{0} events found in summary index. Retrieving uuids....".format(n_events)
                page_size = 1000
                request_info['keys'] = [ 'evid' ]
                request_info['limit'] = page_size
                retrieved = 0
                for page in range(1, (n_events/page_size) + 2):
                    request_info['page'] = page
                    response = self.zenoss_client.send_event_filter_request(request_info, archive=False)
                    if response.get('success'):
                        evs = response.get('events', [])
                        for event in evs:
                            if event:
                                events.append(event['evid'])
                                retrieved = retrieved + 1
                    else:
                        print "Could not retreive page {0}".format(page)
                print "Retrieving {0} uuids from index took {1} seconds".format(len(events), time.time() - start)
                start = time.time()
            else:
                print "Error retrieving events from lucene"
        return events

    def _get_uuids_from_database(self, cursor, uuids, table="event_summary"):
        values = ', '.join([ "'{0}'".format(evid) for evid in uuids ])
        sql = """SELECT BINARY_UUID_TO_STR(uuid) FROM {0} WHERE BINARY_UUID_TO_STR(uuid) IN ({1});""".format(table, values)
        cursor.execute(sql)
        return [ evid for evid, in cursor.fetchall() ]

    def _find_missing_uuids_in_events_db(self, cursor, uuids, table="event_summary"):
        batch_size=10000
        queue = uuids[:]
        missing_events = []
        while queue:
            batch = queue[:batch_size]
            del queue[:batch_size]
            db_events = self._get_uuids_from_database(cursor, batch, "event_summary")
            if len(db_events) != len(batch):
                s_batch = set(batch)
                s_db_events = set(db_events)
                missing_events.extend( (s_batch - s_db_events) )
        return missing_events

    def _generate_csv(self, report):
        filename = "./summary_validator_results_{0}.csv".format(int(time.time()))
        with open(filename, 'wb') as f:
            writer = csv.writer(f)
            writer.writerow( ('UUID', 'Status', 'In archive?', 'Owner', 'Event Class', 'Summary') )
            for event in report:
                if not event: continue
                row = (event["uuid"], event["status"], event["in_archive"], event["owner"], event["event_class"], event["summary"])
                writer.writerow(row)
        return filename

    def _save_results(self, missing_uuids, missing_uuids_in_archive):
        report = []
        batch_size=100
        queue = sorted(missing_uuids[:])
        while queue:
            batch = queue[:batch_size]
            del queue[:batch_size]
            request_info = {}
            request_info['evid'] = batch
            response = self.zenoss_client.send_event_filter_request(request_info, archive=False)
            if response.get('success'):
                events = response.get('events', [])
                if events:
                    for event in events:
                        report_line = {}
                        uuid = event.get("evid")
                        report_line["uuid"] = uuid
                        report_line["summary"] = event.get("summary")
                        report_line["event_class"] = event.get("eventClass").get("text")
                        report_line["status"] = event.get("eventState")
                        report_line["owner"] = event.get("ownerid")
                        report_line["in_archive"] = uuid in missing_uuids_in_archive
                        report.append(report_line)
        if report:
            filename = self._generate_csv(report)
            print "\nMissing events exported to {0}".format(filename)
        else:
            print "No results to export"


    def check_uuids_in_events_db(self, events):
        conn = None
        try:
            conn = pymysql.connect(host=self.config.db_host, port=self.config.db_port,
                                   user=self.config.db_user, passwd=self.config.db_password, db="zenoss_zep")
            cursor = conn.cursor()
            start = time.time()
            print "Checking that uuids in index exists in DB..."
            missing_events = self._find_missing_uuids_in_events_db(cursor, events)
            if len(missing_events) > 0:
                print "\n{0}CHECK FAILED:{1} {2} events have been found in the index and not in the database".format(BColors.FAIL, BColors.ENDC, len(missing_events))
                print "Checking if the events are in archive..."
                found_in_archive = self._get_uuids_from_database(cursor, missing_events, table="event_archive")
                print "{0} out of {1} missing events have been found in archive".format(len(found_in_archive), len(missing_events))
                self._save_results(missing_events, found_in_archive)
            else:
                print "\n{0}CHECK SUCCESSFUL:{1} All summary events in the index have been found in the database".format(BColors.OKGREEN, BColors.ENDC)

        except Exception as e:
            print "ERROR quering DataBase: {0}".format(e)
            raise e
        finally:
            if conn:
                conn.close()

    def check(self):
        connection_status_msg = "Checking connectivity to Zenoss and credentials"
        indexed_events = {}
        if can_connect_to_zenoss(self.config.zenoss_url, self.config.zenoss_user, self.config.zenoss_password):
            log_status_msg(connection_status_msg, success=True, fill=True)
            indexed_events = self.get_lucene_uuids()
            self.check_uuids_in_events_db(indexed_events)
        else:
            log_status_msg(connection_status_msg, success=False, fill=True)


def parse_options():
    """ Defines command-line options for script """
    parser = argparse.ArgumentParser(version="1.0",
                                     description="Checks consistency between lucene and DB for event summary.")
    parser.add_argument("-z", "--zenoss_url", action="store", default='localhost', type=str,
                        help="Zenoss url including port")
    parser.add_argument("-u", "--user", action="store", default='admin', type=str,
                        help="User to log in Zenoss.")
    parser.add_argument("-p", "--password", action="store", default='zenoss', type=str,
                        help="Password to log in Zenoss.")
    parser.add_argument("-dh", "--db_host", action="store", default='localhost', type=str,
                        help="Host where mysql is running")
    parser.add_argument("-dp", "--db_port", action="store", default='localhost', type=str,
                        help="Database port")
    return vars(parser.parse_args())

def main(config):
    start = time.time()
    integrityChecker = SummaryIndexIntegrityChecker(config)
    integrityChecker.check()
    print "\nTotal execution time: {0} seconds".format(time.time()-start)

if __name__ == '__main__':
    """ """
    cli_options = parse_options()
    config = ScriptConfiguration()
    config.zenoss_url = cli_options.get('zenoss_url', config.zenoss_url)
    config.db_host = cli_options.get('db_host', config.db_host)
    main(config)
