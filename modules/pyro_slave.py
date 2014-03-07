"""pyro_slave.py: Remote Objects for the slave devices"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import Pyro4
import gobject
import select

from modules.player import Player
  
def install_pyro_event_callback(daemon):
  """
  Add a callback to the event loop that is invoked every so often.
  The callback checks the Pyro sockets for activity and dispatches to the
  daemon's event process method if needed.
  """
  def pyro_event():
    while True:
      s,_,_ = select.select(daemon.sockets,[],[],0.01)
      if s:
        daemon.events(s)
      else:
        break
      gobject.timeout_add(20, pyro_event)
    return True
  gobject.timeout_add(20, pyro_event)

def start_pyro(device_id):
  """Sets up Pyro, sharing Slave, and starting the eventloop"""
  
  Pyro4.config.SERVERTYPE = "multiplex"
  player = Player()
  
  #TODO: Seriously re-consider life as a programmer for using this workaround
  ip_address = Pyro4.socketutil.getIpAddress('localhost',True)
  
  daemon=Pyro4.Daemon(host=ip_address)
  ns=Pyro4.locateNS()
  uri=daemon.register(player)
  ns.register("pisync.slave.%s" % device_id, uri)
  
  install_pyro_event_callback(daemon)
  print 'Ready!'
  gobject.MainLoop().run()

  
  