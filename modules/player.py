"""player.py: Provies gstreamer playing with controlling fucntions"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import pygst
pygst.require('0.10')
import gst


class Player(object):
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
      #TODO: Handle: File descriptor in bad state
      print message