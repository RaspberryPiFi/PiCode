"""master.py: Start up script for master device"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

from pisync.core import device_enroll
from pisync.core import group_enroll
from pisync import master
from pisync import slave
import base_config

import Pyro4
import json
import sys
import os


class Loader(object):
  def __init__(self, device_type):
    self.device_type = device_type
    self.config = self.get_config()
    
  def get_config(self):
    """Reads pisync.json file or enrolls and returns config"""
    if os.path.isfile(os.path.expanduser("~/.pisync.json")):
      try:
        with open(os.path.expanduser("~/.pisync.json")) as f:
          config = json.loads(f.read())
          print "Configuration Loaded!"
      except IOError as e:
        print 'Error loading configuration file!'
        raise
    else:
      print 'No Configuration file found, enrolling!'
      if self.device_type == 'master':
        config = group_enroll.enroll()
      elif self.device_type == 'slave':
        device_enroll = Pyro4.Proxy('PYRONAME:pisync.device_enroll')
        config = device_enroll.enroll()
      else:
        raise ValueError('device_type must be either master or slave')
      with open(os.path.expanduser("~/.pisync.json"), "w") as f:
        f.write(json.dumps(config))
    return config
    
  def start(self):
    """Calls the appropriate start method using device_type provided"""
    if self.device_type == 'master':
      master.Master(self.config).start()
    elif self.device_type == 'slave':
      slave.Slave(self.config).start()
    else:
      raise ValueError('device_type must be either master or slave')
    
    
def main():
  if len(sys.argv) <= 1 or sys.argv[1] not in ['slave', 'master']:
    print 'Device type must be specified (master or slave). e.g:'
    print ' python PiSync.py master'
  else:
    Loader(sys.argv[1]).start()


if __name__ == "__main__":
  main()