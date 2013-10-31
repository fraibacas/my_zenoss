
"""
check_zencommand_thresholds greps for traces in the zencommand log that contain the following text:

  GREP_STRING = 'TOSHIBA-DEBUG: Checking value'
  GREP_STRING_2 = 'for threshold'

and writes the result of this grep to a temp file to analyze the results.

An example of a line that would match the grep is:

2013-10-25 22:59:32,333 INFO zen.thresholds: TOSHIBA-DEBUG: Checking value '1568657408.0' on 'Devices/192.168.200.1/mem_MemFree' for threshold 'Memory Utilization 100 Percent'

The tool analyzes the temp file line by line, and from each line, extracts the ip/hostname of the device, the data point and the threshold name, and stores all that information in a data structure. This data structure is the one that the tool pickles.

For the above example, the tool would extact the following information:

device: 192.168.200.1
datapoint: mem_MemFree
threshold: 'Memory Utilization 100 Percent'

After analyzing the temp file, we get a data structure that contains for each device the list of data points and thresholds that are checked.
"""

import os
import pickle

import sys

COLLECTOR = 'm201sinf01v'
ZENCOMMAND_LOG_FILE = '/opt/zenoss/log/{0}/zencommand.log'.format(COLLECTOR)
TEMP_FILE = '/tmp/check_zencommand_thresholds.tmp'
PICKLE_FILE = '/tmp/check_zencommand_thresholds.pickle'

class Datapoint(object):
  """ """
  def __init__(self):
      self.ip = ''
      self.threshold = ''
      self.datapoint=''
      self.date = ''

  def __str__(self):
      return '[{0}] [{1}] [{2}] [{3}]'.format(self.ip, self.datapoint, self.threshold, self.date)


class Datapoints(object):
  """ Dict {Key: (data point, threshold)} {Value: Datapoint object} """
  def __init__(self):
      self.datapoints = {}
 
  def add_datapoint(self, dp):
      self.datapoints[(dp.datapoint,dp.threshold)] = dp

  def get_datapoints(self):
      dps = []
      for dp, t in sorted(self.datapoints.keys()):
          dps.append(self.datapoints[(dp,t)])
      return dps


class DevicesDatapoints(object):
  """ Dict {Key: ip} {Value Datapoins object} """

  def __init__(self):
      self.devices = {}

  def add_datapoint(self, dp):
      """ """
      if dp.ip not in self.devices.keys():
          datapoints = Datapoints()
          self.devices[dp.ip] = datapoints
      else:
          datapoints = self.devices[dp.ip]

      datapoints.add_datapoint(dp)

  def get_datapoints(self, ip):
      """ """
      datapoints = self.devices.get(ip, None)
      
      return datapoints.get_datapoints() if datapoints is not None else []

  def _print_datapoints(self, ips):
      """ """
      print '-'*100
      for ip in sorted(ips):
          dps = self.devices[ip]
          for dp in dps.get_datapoints():
              s = '{0} {1} {2}'.format(dp.ip.ljust(20), dp.datapoint.ljust(40), dp.threshold)
              print s
          print '-'*100
               

  def print_datapoints(self, ips=None):
      """ """
      if ips is None or len(ips)==0:
          self._print_datapoints(self.devices.keys())
      else:
          self._print_datapoints(ips)

class ZenCommandParser(object):
  """ """
  GREP_STRING = 'TOSHIBA-DEBUG: Checking value'
  GREP_STRING_2 = 'for threshold'

  def parseLine(self, line):
      """ Parses a line and returns a Datapoint object """
      dp = Datapoint()
      dp.date = line.split(',')[0]
      arr = line.split("'")
      datapoint = arr[3]
      dp.datapoint = datapoint.split('/')[-1]
      dp.threshold = arr[5]
      dp.ip = datapoint.split('/')[1]

      return dp

  def run(self):
      """ """
      devices_datapoints = DevicesDatapoints()

      command = "grep '{0}' {1} | grep '{2}' > {3}".format(ZenCommandParser.GREP_STRING, ZENCOMMAND_LOG_FILE, ZenCommandParser.GREP_STRING_2, TEMP_FILE)
      os.system(command)

      temp_file = open(TEMP_FILE)
      for line in temp_file:
          dp = self.parseLine(line)
          devices_datapoints.add_datapoint(dp)
      temp_file.close()

      command = "rm -rf {0}".format(TEMP_FILE)
      os.system(command)

      return devices_datapoints


def generate_pickle(data):
  """ """
  command = "rm -rf {0} 2> /dev/null".format(PICKLE_FILE)
  os.system(command)

  pfile = open(PICKLE_FILE, "wb")
  pickle.dump(data, pfile)
  pfile.close()

if __name__ == '__main__':
  """ 
      Reads the zencommand's outfile file and prints ip datapoint and threshold name
      By default the output file is read from zenoss log. A different file can be passed
      as a command line argument.
  """
  #By default it reads the log file from '/opt/zenoss/log/COLLECTOR_NAME/zencommand.log'
  #If a param is passed, we take it as file path
  if len(sys.argv) > 1:
      ZENCOMMAND_LOG_FILE = str(sys.argv[1])

  parser = ZenCommandParser()
  devices_datapoints = parser.run()
  #
  # ADD YOUR DEVICES' IPS HERE. IF ARRAY EMPTY IT PRINTS ALL DEVICES
  #
  devices = []
  devices_datapoints.print_datapoints(devices)
  generate_pickle(devices_datapoints)




