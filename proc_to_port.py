"""
   Given a port it prints all the processes that have a connection with that port.
"""

import sys
import subprocess
import time

class Connection(object):
    """ """
    def __init__(self, protocol="", port="", local="", foreign="", state="", pid="", proc=""):
        """ """
        self.protocol = protocol
        self.port = port
        self.local = local
        self.foreign = foreign
        self.state = state
        self.pid = pid
        self.proc = proc
        
    def __str__(self):    
        """ """
        return '{0}/{1}/{2}/{3}/{4}/{5}/{6}'.format(self.protocol, self.port, self.local, self.foreign, self.state, self.pid, self.proc)
    
    
class ProcessesConnectedToPort(object):
    """ """
    LOOP_SLEEP = 10
    
    def __init__(self, port):
        self.port = port

    def _execute_command(self, command):
        """
        Params: command to execute
        Return: tuple containing the stout and stderr of the command execution
        """
        #print 'Executing ....' + command
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return (stdout, stderr)
        
    def _is_relevant(self, connection):
        """ return true if the connection is relevant """
        return connection.protocol == 'tcp' and connection.state != 'LISTEN' and \
               connection.port==connection.foreign.split(':')[1]

    def _get_process_info_from_pid(self, pid):
        """ """
        process_info = ""
        command = 'ps -f -p {0}'.format(pid)
        stdout, stderr = self._execute_command(command)
        if len(stdout) > 0:
            lines = stdout.split('\n')
            if len(lines) > 1:
                info = lines[1] # first line is the header
                #process_info = " ".join(info.split()[7:])
                process_info = info.split()[8]
        return process_info

    def _get_connection_from_command_output(self, output):
        """ """
        connection = None
        try:
            fields = output.split()
            if len(fields) >= 7:
                protocol = fields[0]
                port = self.port
                local = fields[3]
                foreign = fields[4]
                state = fields[5]
                pid = fields[6].split('/')[0]
                proc = self._get_process_info_from_pid(pid)
                connection = Connection(protocol=protocol, port=port, local=local, foreign=foreign, state=state, pid=pid, proc=proc)
        except:
            connection = None
        return connection
        
    def _get_connections_to_port(self):
        """ """
        command = 'netstat -pt | grep {0}'.format(self.port)
        stdout, stderr = self._execute_command(command)
        connections = []
        if len(stdout) > 0:
            lines = stdout.split('\n')
            for line in lines:
                connection = self._get_connection_from_command_output(line)
                if connection and self._is_relevant(connection):
                    connections.append(connection)
        else:
            print 'No connections found. Run "{0}" manually for more details'.format(command)
        return(connections)
    
    def _get_connections_per_pid(self, connections):
        """ """
        established_connections_per_pid = {}
        for c in connections:
            if c.pid in established_connections_per_pid:
                list_of_conns = established_connections_per_pid[c.pid]
                list_of_conns.append(c)
            else:
                established_connections_per_pid[c.pid] = [ c ]      
        return established_connections_per_pid
    
    def _get_process_name_per_pid(self, connections):
        process_name_per_pid = {}
        for c in connections:
            if not c.pid in process_name_per_pid:
                process_name_per_pid[c.pid] = c.proc
        return process_name_per_pid
        
    def _print_connections_per_process(self, established_connections_per_pid, proc_name_for_pid):
        """ """
        for pid in sorted(established_connections_per_pid.keys()):
            print 'PID [{0}]  /  PROCESS {1}  /  NUMBER OF CONNECTIONS [{2}]'.format(pid, proc_name_for_pid[pid],len(established_connections_per_pid[pid]))

    def _print_connections_changes(self, current_connections_per_pid, previous_connections_per_pid, process_name_per_pid):
        """ """
        changes_per_pid = {}
        for pid in current_connections_per_pid.keys():
            current_number_of_conns = len(current_connections_per_pid[pid])
            prev_number_of_conns = 0
            if pid in previous_connections_per_pid:
                prev_number_of_conns = len(previous_connections_per_pid[pid])
            if current_number_of_conns != prev_number_of_conns:
                changes_per_pid[pid] = current_number_of_conns - prev_number_of_conns
                
        if len(changes_per_pid.keys()) > 0:
            print '--------------------------------------------'
            print 'count changes'        
            for pid in sorted(changes_per_pid.keys()):
                print 'PID [{0}]  /  PROCESS {1}  /  CHANGE [{2}]'.format(pid, process_name_per_pid[pid], changes_per_pid[pid])
            print '--------------------------------------------'
            
    def loop_and_print(self):
        """ """
        print 'checking processes connected to port {}'.format(self.port)
        current_connections_per_pid = {}
        previous_connections_per_pid = {}
        while(True):
            previous_connections_per_pid = current_connections_per_pid
            connections = self._get_connections_to_port()
            #print connections
            current_connections_per_pid = self._get_connections_per_pid(connections)
            process_name_per_pid = self._get_process_name_per_pid(connections)
            self._print_connections_per_process(current_connections_per_pid, process_name_per_pid)
            self._print_connections_changes(current_connections_per_pid, previous_connections_per_pid, process_name_per_pid)
            print '======================================================'
            time.sleep(self.LOOP_SLEEP)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'Error: wrong number of parameters.'
        print 'Usage: proc_to_port <port_number> [process_name]'
    else:
        #if
        procs = ProcessesConnectedToPort(sys.argv[1])
        procs.loop_and_print()
    
