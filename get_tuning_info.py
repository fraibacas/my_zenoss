
#############################

import sys
import datetime
import os
import subprocess

#############################


class ConfigCollector(object):
  """ """
  _OUTPUT_ROOT = '/tmp/'
  _MEMORY_REPORT = 'mem.txt'
  _CATALOG_REPORT = 'catalog_size.txt'
  _ZENTUNE_REPORT = 'zentune.txt'
  _ZOPE_CONF_REPORT = 'zope_conf.txt'
  _MEMCACHE_CONF_REPORT = 'memcached.txt'
  _ERROR_REPORT = 'log.txt'

  _ZOPE_CONFIG_FILE = '/etc/zope.conf'
  _MEMCACHE_CONFIG_FILE = '/etc/sysconfig/memcached'

  def __init__(self, zen_home):
    """ """
    self._zenhome = zen_home
    self._output_dir = ''
    self._output_path = ''
    self._output_file = ''
    self._log_file = ''

  @staticmethod
  def get_timestamp():
    """ """
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return timestamp

  def _initialize_file_names(self):
    """ """
    self._output_dir = 'config_{0}'.format(ConfigCollector.get_timestamp())
    self._output_path = ConfigCollector._OUTPUT_ROOT + self._output_dir
    self._output_file = self._output_path + '.tar'
    self._log_file = self._output_path + '/' + ConfigCollector._ERROR_REPORT 

  def _execute_command(self, command, out = None):
    """ """
    #print 'Executing ....' + command
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if out is not None:
      f_out = open(out, 'w')
      f_out.write(stdout)
      f_out.close()
    f_err = open(self._log_file, 'a')
    f_err.write("\n\n" + '*'*60 + "\n")
    f_err.write('    Command => ' + command + "\n")
    f_err.write('    Output  => ' + str(out) + "\n")
    f_err.write('*'*60 + "\n")
    f_err.write(stderr)
    f_err.close()

  def _create_ouput_dir(self):
    """ """
    command = 'mkdir -p {0}'.format(self._output_path)
    self._execute_command(command)
    from time import sleep
    sleep(1)

  def _get_memory_info(self):
    """ """
    command = 'cat /proc/meminfo'
    output = '{0}/{1}'.format(self._output_path, ConfigCollector._MEMORY_REPORT)
    errors = '{0}/{1}'.format(self._output_path, ConfigCollector._MEMORY_REPORT)
    self._execute_command(command, out=output)

  def _get_zope_conf(self):
    """ """
    command = 'cat {0}/{1}'.format(self._zenhome, ConfigCollector._ZOPE_CONFIG_FILE)
    output = '{0}/{1}'.format(self._output_path, ConfigCollector._ZOPE_CONF_REPORT)
    self._execute_command(command, out=output)

  def _get_catalog_size(self):
    """ """
    zendmd = '{0}/bin/zendmd'.format(self._zenhome)
    command = '{0} << EOF\ndmd.global_catalog.__len__()\nquit()\nEOF'.format(zendmd)
    output = '{0}/{1}'.format(self._output_path, ConfigCollector._CATALOG_REPORT)
    self._execute_command(command, out=output)

  def _get_memcache_conf(self):
    """ """
    command = 'cat {0}'.format(ConfigCollector._MEMCACHE_CONFIG_FILE)
    output = '{0}/{1}'.format(self._output_path, ConfigCollector._MEMCACHE_CONF_REPORT)
    self._execute_command(command, out=output)

  def _run_zentune(self):
    """ """
    zentune = '{0}/bin/zentune'.format(self._zenhome)
    command = '{0} run'.format(zentune)
    output = '{0}/{1}'.format(self._output_path, ConfigCollector._ZENTUNE_REPORT)
    self._execute_command(command, out=output)

  def _get_config(self):
    """ """
    self._get_memory_info()
    self._get_zope_conf()
    self._get_catalog_size()
    self._get_memcache_conf()
    self._run_zentune()

  def _compress_output(self):
    """ """
    # makes the tar
    command = 'cd {0}; tar cfv {1}.tar {2}'.format(ConfigCollector._OUTPUT_ROOT, self._output_dir, self._output_dir) 
    self._execute_command(command)

    # compresses it
    command = 'gzip {0}'.format(self._output_file)
    self._execute_command(command)

    # removes the folder
    #command = 'rm -rf {0} &> /dev/null'.format(self._output_path)
    #self._execute_command(command)

  def get_configuration(self):
    """ """
    print '\nRetrieving information... please wait.'
    self._initialize_file_names()
    self._create_ouput_dir()
    self._get_config()
    self._compress_output()
    print '\nConfiguration retrieved to file {0}.gz !'.format(self._output_file)
    print '\nLog available in {0}\n\n'.format(self._log_file)


#############################

if __name__ == '__main__':

  zen_home = os.getenv('ZENHOME', '/opt/zenosss')
  if os.path.isdir(zen_home):
    config_collector = ConfigCollector(zen_home)
    config_collector.get_configuration()
  else:
    print '\n\nERROR: Enviroment variable ZENHOME is not defined! \n\n'

#############################





