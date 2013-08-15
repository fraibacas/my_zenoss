
#############################

import sys
import datetime
import os
import subprocess

#############################


class FileCollector(object):
    """ """
    def __init__(self, zenhome, files, output_filename = ''):
        """ """
        self._zenhome = zenhome
        self._files = files
        self._output_filename = output_filename

    @staticmethod
    def get_timestamp():
        """ """
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        return timestamp

    def _execute_command(self, command):
        """
        Params: command to execute
        Return: tuple containing the stout and stderr of the command execution
        """
        #print 'Executing ....' + command
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()

        return (stdout, stderr)

    def _get_existing_files(self):
        """ """
        files_to_tar = []
        for f in self._files:
            file_path = self._zenhome + "/" + f
            if not os.path.isfile(file_path):
                print 'Skipping {0}. File not found.'.format(file_path)
            else:
                files_to_tar.append(f)
                print 'File Found!! {0}'.format(file_path)
        return files_to_tar

    def _tar_files(self, files_to_tar):
        """ """
        tar_filename = 'files_{0}_{1}.tar'.format(self._output_filename, FileCollector.get_timestamp())
        tar_file = '/tmp/{0}'.format(tar_filename)
        command = "cd {0}; tar cvf {1} {2}".format(self._zenhome, tar_file, " ".join(files_to_tar))
        stdout, stderr = self._execute_command(command)
        value_to_return = {}
        value_to_return ['tar_file'] = tar_file
        value_to_return ['stdout'] = stdout
        value_to_return ['stderr'] = stderr
        return value_to_return

    def get_files(self):
        """ """
        files_to_tar = self._get_existing_files()

        if len(files_to_tar) > 0:
            output = self._tar_files(files_to_tar)
            stderr = output.get('stderr', '')
            if len(stderr) > 0:
                print 'Errors found executing the tar command.\n{0}\n'.format(stderr)
            else:
                print 'Files tar\'ed in {0}'.format(output.get('tar_file', 'ERROR'))
        else:
            print 'ERROR: Empty set of files to tar.'

"""
#------------------------------------------------------------------------------------
#                                     MAIN
#------------------------------------------------------------------------------------
"""

if __name__ == '__main__':
    """ """
    zen_home = os.getenv('ZENHOME', '/opt/zenoss')
    if os.path.isdir(zen_home):
        files = ['Products/ZenHub/PBDaemon.py', \
                 'Products/ZenHub/services/EventService.py', \
                 'Products/ZenHub/zenhub.py', \
                 'Products/ZenEvents/zensyslog.py', \
                 'Products/ZenEvents/zentrap.py', \
                 'Products/ZenHub/interfaces.py', \
                 'Products/ZenHub/configure.zcml', \
                ]

        output_filename = ''
        if len(sys.argv) > 1:
            output_filename = sys.argv[1]

        file_collector = FileCollector(zen_home, files, output_filename)
        file_collector.get_files()
    else:
        print '\n\nERROR: Enviroment variable ZENHOME is not defined! \n\n'

"""
#------------------------------------------------------------------------------------
"""





