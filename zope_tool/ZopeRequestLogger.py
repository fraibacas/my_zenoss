
import logging

class ZopeRequestLogger(object):

    SEPARATOR = '@$@'
    FIELDS = []
    FIELDS.append('Trace_Type')
    FIELDS.append('Timestamp')
    FIELDS.append('Server_Name')
    FIELDS.append('Server_Port')
    FIELDS.append('Path_Info')
    FIELDS.append('Method')
    FIELDS.append('Client')
    FIELDS.append('HTTP_Host')
    #fields.append('XFF')
    #fields.append('Zope_Id')
    #fields.append('Fingerprint')

    def __init__(self, filename = '/opt/zenoss/log/paco.log'):
        self._log = logging.getLogger('request_logger')
        self._log.propagate = False
        handler = logging.FileHandler(filename, 'a')
        handler.setFormatter(logging.Formatter("%(asctime)s{0}%(message)s".format(ZopeRequestLogger.SEPARATOR)))
        self._log.addHandler(handler)

    def _retrieve_zope_id(self, request):
        zope_id = ''
        cookie_info = request.get('HTTP_COOKIE')
        if cookie_info:
            try:
                for var in cookie_info.split(';'):
                    if '_ZopeId' in var:
                        zope_id = var.split('=')[-1]
            except:
                pass    
        return zope_id
        
    def log_request(self, request, timestamp, method='', finished=False):
        data = {}
        if finished:
            data['Trace_Type'] = 'END'
        else:
            data['Trace_Type'] = 'START'
        data['HTTP_Host'] = request.get('HTTP_HOST', default='')
        data['Server_Name'] = request.get('SERVER_NAME', default='')
        data['Server_Port'] = request.get('SERVER_PORT', default='')
        data['Path_Info'] = request.get('PATH_INFO', default='')
        data['Method'] = method
        data['Client'] = request.get('REMOTE_ADDR', default='')
        data['Timestamp'] = timestamp
        str(request.environ.get('channel.creation_time'))
        #request.get('channel.creation_time', default='')
        #data['Zope_Id'] = self._retrieve_zope_id(request)
        #data['XFF'] = request.get('X_FORWARDED_FOR', default='')

        trace = []
        for field in ZopeRequestLogger.FIELDS:
            trace.append(data.get(field, ''))
        
        self._log.info((ZopeRequestLogger.SEPARATOR).join(trace))


