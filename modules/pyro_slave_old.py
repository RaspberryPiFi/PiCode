"""pyro_slave.py: Remote Objects for the slave devices"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import Pyro4
import pygst
pygst.require('0.10')
import gst
import threading
import time
import gobject


class Slave(object):
  """Provides methods for playback on slave devices"""
  def __init__(self):
    self.playlist = []
    self.playlist_index = 0
    self.playlist_length = 0
    self.player = gst.element_factory_make('playbin2', 'player')
    fakesink = gst.element_factory_make('fakesink', 'fakesink')
    self.player.set_property('video-sink', fakesink)
    bus = self.player.get_bus()
    bus.add_signal_watch()
    bus.connect('message', self.on_message)
    
  def play_list(self, playlist):
    """Starts playing the playlist provided"""
    self.player.set_state(gst.STATE_NULL)
    self.playlist = playlist
    self.playlist_index = 0
    self.playlist_length = len(self.playlist)
    self.player.set_property('uri', self.playlist[self.playlist_index])
    self.player.set_state(gst.STATE_PLAYING)
    
  def stop(self):
    """Stops the current media playing, if any"""
    self.player.set_state(gst.STATE_NULL)
  
  def skip_forward(self):
    self.player.set_state(gst.STATE_NULL)
    if self.playlist_index + 1 != self.playlist_length:
      self.playlist_index += 1
      self.player.set_property('uri', self.playlist[self.playlist_index])
      self.player.set_state(gst.STATE_PLAYING)
  
  def skip_backward(self):
    self.player.set_state(gst.STATE_NULL)
    if not self.playlist_index - 1 < 0 :
      self.playlist_index -= 1
      self.player.set_property('uri', self.playlist[self.playlist_index])
      self.player.set_state(gst.STATE_PLAYING)
  
  def play_pause(self):
    if self.player.get_state()[1] == gst.STATE_PLAYING:
      self.player.set_state(gst.STATE_PAUSED)
    elif self.player.get_state()[1] == gst.STATE_PAUSED:
      self.player.set_state(gst.STATE_PLAYING)
      
  def set_volume(self, volume):
    self.player.set_property('volume', volume)
      
  def on_message(self, bus, message):
    t = message.type
    if t == gst.MESSAGE_EOS:
      self.skip_forward()
    elif t == gst.MESSAGE_ERROR:
      self.skip_forward()
      #TODO: Log this!
  
def start_pyro(device_id,slave):
  """Sets up Pyro, sharing Slave, and starting the eventloop"""
  
  #TODO: Seriously re-consider life as a programmer for using this workaround
  ip_address = Pyro4.socketutil.getIpAddress('localhost',True)
  
  daemon=Pyro4.Daemon(host=ip_address)
  ns=Pyro4.locateNS()
  uri=daemon.register(slave)
  ns.register("pisync.slave.%s" % device_id, uri)
  
  print "Ready!"
  daemon.requestLoop()

def slave_thread():
  gobject.threads_init()
  gobject.MainLoop().run()

def start_slave(device_id):
  """Starts MainLoop in a thread to deal with gst's bus and starts pyro"""
  slave = Slave()
  t = threading.Thread(target=slave_thread)
  t.daemon = True
  t.start()
  start_pyro(device_id,slave)
  
  
  