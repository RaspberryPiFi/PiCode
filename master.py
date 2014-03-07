"""master.py: Start up script for master device"""

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
from modules import device_enroll
from modules import player
from modules import poller

gobject.threads_init()

class Loader(object):
  def __init__(self):
    self.master_config = self.get_master_config()
    self.master_player = player.Player()
    ip_address = Pyro4.socketutil.getIpAddress('localhost',True)
    self.pyro_daemon = Pyro4.Daemon(host=ip_address)
    
  def get_master_config(self):
    """Reads pisync.json file or enrolls and returns master config"""
    if os.path.isfile(os.path.expanduser("~/.pisync.json")):
      try:
        with open(os.path.expanduser("~/.pisync.json")) as f:
          master_config = json.loads(f.read())
          print "Configuration Loaded - Group ID: %s" % master_config['group_id']
      except IOError as e:
        print 'Error loading configuration file!'
        raise
    else:
      print 'No Configuration file found, enrolling with cloud server'
      group_id, device_id = group_enroll.enroll()
      master_config = {'group_id': group_id, 'device_id': device_id}
      json_string = json.dumps(master_config)
      with open(os.path.expanduser("~/.pisync.json"), "w") as f:
        f.write(json_string)
    return master_config
    
  def install_poller_event_callback(self):
    """Add a callback to the gobject event loop to handle poller events."""
    def start_poll():
      poller.poll_for_updates(self.master_config,self.master_player)
      gobject.timeout_add(3000,start_poll)
    gobject.timeout_add(3000,start_poll)

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
    """Calls the event callback setup methods and starts the MainLoop"""
    device_enroll.setup_pyro(self.master_config['group_id'],self.pyro_daemon)
    self.install_poller_event_callback()
    self.install_pyro_event_callback()
    print 'Starting Main Loop'
    gobject.MainLoop().run()
  

def main():
  Loader().start()


if __name__ == "__main__":
  main()