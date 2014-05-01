"""master.py: Start up script for master device"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

from argparse import ArgumentParser
import threading
import logging
import json
import sys
import os

from lib import pidfile
import daemon
import Pyro4

import base_config

# Need to use edited version of eyed3 
dirname, _ = os.path.split(os.path.abspath(__file__))
sys.path.append(dirname + '/lib')

class Loader(object):
  """Gets config and provides function to start the program"""
  def __init__(self, role):
    self.config = self.get_config(role)
    if self.config:
      self.device_type = self.config['device_type']
      logging.info('Configuration Loaded! Device Type: %s' % self.device_type) 
    else:
      if role == 'auto':
        logging.info('No config file found, detecting device_type')
        self.device_type = self.detect_device_type()
        logging.info('Detected device type as %s' % self.device_type)
      else:
        self.device_type = role
      self.config = self.create_config()
    
  def get_config(self, arg):
    """Reads pisync.json file or enrolls and returns config"""
    if os.path.isfile(os.path.expanduser(base_config.CONFIG_FILE_PATH)):
      try:
        with open(os.path.expanduser(base_config.CONFIG_FILE_PATH)) as f:
          config = json.loads(f.read())
          if arg != 'auto' and arg != config['device_type']:
            return
      except IOError as e:
        logging.error('Error loading configuration file!')
        raise e
      return config
      
  def detect_device_type(self):
    """Searches for master on network, if so returns slave else master"""
    try:
      nameserver = Pyro4.locateNS()
      nameserver.lookup('pisync.device_enroll')
      return 'slave'
    except Pyro4.errors.NamingError:
      return 'master'
    
  def create_config(self):
    """Creates a configuration file"""
    logging.info('Enrolling device!')
    if self.device_type == 'master':
      logging.info('Device enrolling as a Master Device')
      from pisync.core import groupenroll
      config = groupenroll.GroupEnrollHandler().enroll()
      config['slave_device_ids'] = []
    elif self.device_type == 'slave':
      logging.info('Device enrolling as a Slave Device')
      device_enroll = Pyro4.Proxy('PYRONAME:pisync.device_enroll')
      config = device_enroll.enroll()
    else:
      raise ValueError('device_type must be either master or slave')
    config['device_type'] = self.device_type
    with open(os.path.expanduser(base_config.CONFIG_FILE_PATH), 'w') as f:
      f.seek(0)
      f.write(json.dumps(config))
      f.truncate()
    return config
    
  def start(self):
    """Calls the appropriate start method using device_type provided"""
    if self.device_type == 'master':
      try:
        Pyro4.locateNS()
      except Pyro4.errors.NamingError:
        self.start_name_server()
      from pisync import master
      master.Master(self.config).start()
    elif self.device_type == 'slave':
      from pisync import slave
      slave.Slave(self.config).start()
    else:
      raise ValueError('device_type must be either master or slave')
    
  def start_name_server(self):
    """Starts Pyro4 nameserver in a new thread"""
    t = threading.Thread(target=Pyro4.naming.startNSloop, args=('0.0.0.0',))
    t.daemon = True
    t.start()
    
    
def main():
  """Runs if the script is started directly"""
  parser = ArgumentParser(prog='PiSync.py')
  parser.add_argument('--role', choices=['slave', 'master', 'auto'],
                      help='slave, master or auto to detect')
  parser.add_argument('--daemon', action='store_true',
                      help='Run PiSync as a daemon')
  parser.add_argument('--pidfile', help='Location of PID file')
  options = parser.parse_args(sys.argv[1:])
  if options.role:
    device_type = options.role
  else:
    device_type = 'auto'
  
  if not os.path.exists(os.path.expanduser(base_config.CONFIG_DIR)):
    os.makedirs(os.path.expanduser(base_config.CONFIG_DIR))
  
  if options.daemon:
    context = daemon.DaemonContext()
    if options.pidfile:
      context.pidfile = pidfile.PidFile(options.pidfile)
    with context:
      log_file_path = os.path.expanduser(base_config.LOG_FILE_PATH)
      logging.basicConfig(filename=log_file_path, level=logging.DEBUG)
      try:
        loader = Loader(device_type)
        loader.start()
      except Exception as e:
        logging.exception(e)
  else:
    logging.basicConfig(level=logging.DEBUG)
    Loader(device_type).start()


if __name__ == '__main__':
  main()