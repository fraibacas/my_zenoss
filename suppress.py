

from zenoss.protocols.jsonformat import to_dict, from_dict
from zenoss.protocols.protobufs.zep_pb2 import EventSummary, EventNote, EventSummaryUpdate, EventFilter
from zenoss.protocols.protobufs.zep_pb2 import STATUS_NEW, STATUS_SUPPRESSED
zep = getFacade('zep')
user_name = 'admin'
user_uuid = zep._getUserUuid(user_name)
filter_dict = {'event_summary': ['hola']}
filter_protobuf = from_dict(EventFilter, filter_dict)

suppress_update = from_dict(EventSummaryUpdate, dict(
        status = STATUS_SUPPRESSED,
        current_user_uuid = user_uuid,
        current_user_name = user_name,
))


new_update = from_dict(EventSummaryUpdate, dict(
        status = STATUS_NEW,
        current_user_uuid = user_uuid,
        current_user_name = user_name,
))

print 'Suppressing events that contain the word "hola" in the summary'

#zep.client.updateEventSummaries(suppress_update, event_filter=filter_protobuf)
#zep.client.updateEventSummaries(new_update, event_filter=filter_protobuf)


