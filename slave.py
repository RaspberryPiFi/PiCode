"""slave.py: Start up script for slave device"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import os.path
import gobject
import select
import Pyro4
import json


from modules import group_enroll
from modules import player
from modules import poller

#TDOD: Possibly don't need this any-more, we'll see.
gobject.threads_init()
Pyro4.config.SERVERTYPE = "multiplex"

class Loader(object):
  def __init__(self):
    self.slave_config = self.get_slave_config()
    self.slave_player = player.Player()
    #TODO: Seriously re-consider life as a programmer for using this workaround
    ip_address = Pyro4.socketutil.getIpAddress('localhost',True)
    self.pyro_daemon = Pyro4.Daemon(host=ip_address)
    
  def get_slave_config(self):
    """Reads pisync.json file or enrolls and returns slave config"""
    if os.path.isfile(os.path.expanduser("~/.pisync.json")):
      try:
        with open(os.path.expanduser("~/.pisync.json")) as f:
          slave_config = json.loads(f.read())
          print 'Config Loaded - Device ID: %s' % slave_config['device_id']
      except IOError as e:
        print 'Error loading configuration file!'
        raise
    else:
      print 'No Configuration file found, enrolling with master'
      device_enroll = Pyro4.Proxy('PYRONAME:pisync.device_enroll')
      slave_config = device_enroll.enroll()
      print 'Enrolled Successfully - Device ID: %s' % slave_config['device_id']
      with open(os.path.expanduser("~/.pisync.json"), "w") as f:
        f.write(json.dumps(slave_config))
    return slave_config
  
  def install_pyro_event_callback(self):
    """Add a callback to the gobject event loop to handle Pyro requests."""
    def pyro_event():
      while True:
        s,_,_ = select.select(self.pyro_daemon.sockets,[],[],0.01)
        if s:
          self.pyro_daemon.events(s)
        else:
          break
        gobject.timeout_add(20, pyro_event)
      return True
    gobject.timeout_add(20, pyro_event)

  def start(self):
    """Sets up Pyro, sharing slave_player, and starts the eventloop"""
    name_server = Pyro4.locateNS()
    uri = self.pyro_daemon.register(self.slave_player)
    name_server.register("pisync.slave.%s" % self.slave_config['device_id'],uri)
    
    self.install_pyro_event_callback()
    print 'Starting Main Loop'
    gobject.MainLoop().run()
  

def main():
  Loader().start()


if __name__ == "__main__":
  main()