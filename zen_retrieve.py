
#############################

import sys
import datetime
import os
import subprocess

#############################


class ConfigCollector(object):
  """ """

  """
  #------------------------------------------------------------------------------------
  # Class variables
  #------------------------------------------------------------------------------------
  """
  _OUTPUT_ROOT = '/tmp/'
  _OUTPUT_REPORT_NAME = 'zen_retrieve_' # the report name has a timestamp appended

  _ZOPE_CONFIG_FILE = '/etc/zope.conf'
  _MEMCACHE_CONFIG_FILE = '/etc/sysconfig/memcached'

  def __init__(self, zen_home):
    """ """
    self._zenhome = zen_home
    self._output_file = ''

  @staticmethod
  def get_timestamp():
    """ """
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return timestamp

  def _initialize_report_name(self):
    """ """
    self._output_file = '{0}{1}{2}.txt'.format(self._OUTPUT_ROOT, self._OUTPUT_REPORT_NAME, ConfigCollector.get_timestamp())

  def _get_config(self):
    """ """
    self._get_memory_info()
    self._get_zope_conf()
    self._get_catalog_size()
    self._get_memcache_conf()
    self._run_zentune()

  def get_configuration(self):
    """ """
    print '\nRetrieving information... please wait.'
    self._initialize_report_name()
    self._get_config()
    print '\nConfiguration retrieved to file {0} !!'.format(self._output_file)

  """
  #------------------------------------------------------------------------------------
  # Method that executes Unix commands
  #------------------------------------------------------------------------------------
  """

  def _execute_command(self, command):
    """
        Params: command to execute
        Return: tuple containing the stout and stderr of the command execution
    """
    #print 'Executing ....' + command
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()

    return (stdout, stderr)

  """
  #------------------------------------------------------------------------------------
  # Method that writes info to the output file
  #------------------------------------------------------------------------------------
  """
  def _write_to_output(self, title, command, out, err):
    """ """
    f_report = open(self._output_file, 'a')
    # Writes header
    f_report.write('#'*60 + "\n")
    f_report.write('#  {0}\n'.format(title))
    f_report.write('#  Command: {0}\n'.format(command))
    f_report.write('#'*60 + "\n\n")

    # Writes stdout
    f_report.write('-'*60 + "\n")
    f_report.write(" STDOUT\n")
    f_report.write('-'*60 + "\n")
    f_report.write("{0}\n".format(str(out)))

    # Writes stderr
    f_report.write('-'*60 + "\n")
    f_report.write(" STDERR\n")
    f_report.write('-'*60 + "\n")
    f_report.write("{0}\n".format(str(err)))

    f_report.close()

  """
  #------------------------------------------------------------------------------------
  # Methods to retrieve the info
  #------------------------------------------------------------------------------------
  """

  def _get_memory_info(self):
    """ """
    command = 'cat /proc/meminfo'
    (out, err) = self._execute_command(command)
    self._write_to_output("", command, out, err)

  def _get_zope_conf(self):
    """ """
    command = 'cat {0}/{1}'.format(self._zenhome, ConfigCollector._ZOPE_CONFIG_FILE)
    (out, err) = self._execute_command(command)
    self._write_to_output("", command, out, err)

  def _get_catalog_size(self):
    """ """
    zendmd = '{0}/bin/zendmd'.format(self._zenhome)
    command = '{0} << EOF\ndmd.global_catalog.__len__()\nquit()\nEOF'.format(zendmd)
    (out, err) = self._execute_command(command)
    self._write_to_output("", command, out, err)

  def _get_memcache_conf(self):
    """ """
    command = 'cat {0}'.format(ConfigCollector._MEMCACHE_CONFIG_FILE)
    (out, err) = self._execute_command(command)
    self._write_to_output("", command, out, err)

  def _run_zentune(self):
    """ """
    zentune = '{0}/bin/zentune'.format(self._zenhome)
    command = '{0} run'.format(zentune)
    (out, err) = self._execute_command(command)
    self._write_to_output("", command, out, err)


"""
#------------------------------------------------------------------------------------
#                                     MAIN
#------------------------------------------------------------------------------------
"""

if __name__ == '__main__':

  zen_home = os.getenv('ZENHOME', '/opt/zenoss')
  if os.path.isdir(zen_home):
    config_collector = ConfigCollector(zen_home)
    config_collector.get_configuration()
  else:
    print '\n\nERROR: Enviroment variable ZENHOME is not defined! \n\n'

"""
#------------------------------------------------------------------------------------
"""





