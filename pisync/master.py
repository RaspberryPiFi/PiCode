"""master.py: Start up script for master device"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import gobject
import select
import Pyro4

from pisync.core import device_enroll
from pisync.core import player
from pisync.core import poller

gobject.threads_init()

class Master(object):
  def __init__(self,config):
    self.config = config
    self.master_player = player.Player()
    ip_address = Pyro4.socketutil.getIpAddress('localhost',True)
    self.pyro_daemon = Pyro4.Daemon(host=ip_address)
    
  def install_poller_event_callback(self):
    """Add a callback to the gobject event loop to handle poller events."""
    def start_poll():
      poller.poll_for_updates(self.config,self.master_player)
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
  
  def setup_pyro(self):
    """Sets up Pyro, sharing DeviceEnrollHandler"""
    handler = device_enroll.DeviceEnrollHandler(self.config['group_id'])
    ns = Pyro4.locateNS()
    uri = self.pyro_daemon.register(handler)
    #TODO: Handle NS not found error
    ns.register("pisync.device_enroll", uri)
  
  def start(self):
    """Calls the event callback setup methods and starts the MainLoop"""
    self.setup_pyro()
    self.install_poller_event_callback()
    self.install_pyro_event_callback()
    print 'Starting Main Loop'
    gobject.MainLoop().run()