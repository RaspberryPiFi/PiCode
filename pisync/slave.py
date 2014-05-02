"""slave.py: Start up script for slave device"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import logging
import select
import sys

# pylint: disable=F0401
import gobject
import Pyro4
# pylint: enable=F0401

from pisync.core import player

gobject.threads_init()

class Slave(object):
  """Provides methods needed by a slave device"""
  def __init__(self, config):
    self.config = config
    self.slave_player = player.SlavePlayer()
    #TODO: Seriously re-consider life as a programmer for using this workaround
    ip_address = Pyro4.socketutil.getIpAddress('localhost', True)
    self.pyro_daemon = Pyro4.Daemon(host=ip_address)
  
  def install_pyro_event_callback(self):
    """Add a callback to the gobject event loop to handle Pyro requests."""
    def pyro_event():
      """Handles any pyro event that needs handling"""
      while True:
        s, _, _ = select.select(self.pyro_daemon.sockets, [], [], 0.01)
        if s:
          self.pyro_daemon.events(s)
        else:
          break
      return True
    gobject.timeout_add(20, pyro_event)
  
  def setup_pyro(self):
    """Sets up Pyro, sharing slave_player"""
    try:
      ns = Pyro4.locateNS()
    except Pyro4.errors.PyroError:
      logging.error('Unable to find Master Device, cannot start as a slave.')
      sys.exit()
    uri = self.pyro_daemon.register(self.slave_player)
    #TODO: Handle NS not found error
    ns.register("pisync.slave.%s" % self.config['device_id'], uri)

  def start(self):
    """Sets up Pyro, sharing slave_player, and starts the eventloop"""
    self.setup_pyro()
    self.install_pyro_event_callback()
    logging.info('Starting Main Loop')
    gobject.MainLoop().run()