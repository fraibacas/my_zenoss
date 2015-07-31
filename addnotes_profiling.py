
import os
import datetime
import time

from zenoss.protocols.jsonformat import to_dict, from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventSummary, EventNote, EventSummaryUpdate, EventFilter
from zenoss.protocols.protobufs.zep_pb2 import STATUS_NEW, STATUS_ACKNOWLEDGED, STATUS_CLOSED, STATUS_SUPPRESSED

from Products.ZenUtils import debugtools

event_summary = str(datetime.datetime.now())

zep = getFacade('zep')
user_name = 'admin'
user_uuid = zep._getUserUuid(user_name)
filter_dict = { 'event_summary': [ event_summary ] }
filter_protobuf = from_dict(EventFilter, filter_dict)


print 'Creating 1000 events containing "{0}" in the event summary'.format(event_summary)
for i in range(0,1000):
	os.system('zensendevent -d localhost "{0} {1}"'.format(event_summary, i))

print 'Sleeping for 1 minute to wait for events to be created'
time.sleep(60)

#Get the events that we just created
response = zep.getEventSummaries(0, filter=filter_protobuf)

uuids = [ event['uuid'] for event in response['events'] ]

@debugtools.profile
def profile_old_add_note():
	i = 1
	for uuid in uuids:
		zep.addNote(uuid, 'profile_old_add_note. Test note {0}'.format(i), user_name, userUuid=user_uuid)
		i = i + 1

@debugtools.profile
def profile_new_add_note():
	zep.addNoteBulkAsync(uuids, 'profile_new_add_note all events in one call.', user_name, userUuid=user_uuid)

print '-' * 60
print 'Adding one note to each event with addNote.....'
print '-' * 60
profile_old_add_note()

print '-' * 60
print 'Adding one note to each event with addNoteBulkAsync.....'
print '-' * 60
profile_new_add_note()

