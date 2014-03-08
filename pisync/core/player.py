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
    self.synced = False
    self.reset_player()
    
  def reset_player(self):
    """Resets the player back to original state"""
    #TODO: Work out what to do with volume when turning device on
    if hasattr(self,'player'):
      self.player.set_state(gst.STATE_NULL)
    self.player = gst.element_factory_make('playbin2', 'player')
    bus = self.player.get_bus()
    bus.add_signal_watch()
    bus.connect('message', self.on_message)
    
  def play_list(self, playlist):
    """Starts playing the playlist provided"""
    if self.synced:
      #TODO: Fix volume when returning to normal playmode 
      self.reset_player()
      self.synced = False
    self.player.set_state(gst.STATE_NULL)
    self.playlist = playlist
    self.playlist_index = 0
    self.playlist_length = len(self.playlist)
    self.player.set_property('uri', self.playlist[self.playlist_index])
    base_time = self.player.get_clock().get_time()
    self.player.set_base_time(base_time)
    self.player.set_state(gst.STATE_PLAYING)
    
  def stop(self):
    """Stops the current media playing, if any"""
    self.player.set_state(gst.STATE_NULL)
  
  def skip_forward(self):
    """Stops the current audio and plays the next in the playlist"""
    self.player.set_state(gst.STATE_NULL)
    if self.playlist_index + 1 != self.playlist_length:
      self.playlist_index += 1
      self.player.set_property('uri', self.playlist[self.playlist_index])
      self.player.set_state(gst.STATE_PLAYING)
  
  def skip_backward(self):
    """Stops the current audio and plays the previous in the playlist"""
    self.player.set_state(gst.STATE_NULL)
    if not self.playlist_index - 1 < 0:
      self.playlist_index -= 1
      self.player.set_property('uri', self.playlist[self.playlist_index])
      self.player.set_state(gst.STATE_PLAYING)
  
  def play_pause(self):
    """Pauses the current player"""
    if self.player.get_state()[1] == gst.STATE_PLAYING:
      self.player.set_state(gst.STATE_PAUSED)
    elif self.player.get_state()[1] == gst.STATE_PAUSED:
      self.player.set_state(gst.STATE_PLAYING)
      
  def set_volume(self, volume):
    """Sets the player's volume"""
    self.player.set_property('volume', volume)
    
  def on_message(self, bus, message):
    """Handles messages on the player's bus"""
    t = message.type
    if t == gst.MESSAGE_EOS and self.synced == False:
      self.skip_forward()
    elif t == gst.MESSAGE_ERROR:
      self.skip_forward()
      #TODO: Handle: File descriptor in bad state
      print message
  
      
class SlavePlayer(Player):
  def play_synced(self, uri, base_time, ip_address):
    """Plays specified URI in sync with the master"""
    self.synced = True
    self.player.set_state(gst.STATE_NULL)
    self.player.set_new_stream_time(gst.CLOCK_TIME_NONE)
    clock = gst.NetClientClock(None, ip_address, 5637, base_time)
    self.player.use_clock(clock)
    self.player.set_property("uri", uri)
    self.player.set_base_time(base_time)
    self.player.set_state(gst.STATE_PLAYING)
    
      
class MasterPlayer(Player):
    
  def _setup_synced_player(self):
    """Sets up clock and provides it over the network"""
    self.player.set_state(gst.STATE_NULL)
    # May need to create a new player here, we'll see!
    self.clock = self.player.get_clock()
    self.player.use_clock(self.clock)
    self.clock_provider = gst.NetTimeProvider(self.clock, None, 5637)
    self.player.set_new_stream_time(gst.CLOCK_TIME_NONE)
    
  def play_list_synced(self, playlist, slave_players, ip_address):
    """Starts playing the playlist provided locally and on slaves"""
    self.synced = True
    self.ip_address = ip_address
    self.slave_players = slave_players
    self.playlist = playlist
    self.playlist_index = 0
    self.playlist_length = len(self.playlist)
    self._setup_synced_player()
    uri = self.playlist[self.playlist_index]
    self.player.set_property('uri', uri)
    base_time = self.clock.get_time()
    self.player.set_base_time(base_time)
    self.player.set_state(gst.STATE_PLAYING)
    self._play_slaves(base_time, uri)
    
  def _play_slaves(self, base_time, uri):
    """Starts synchronised playing with all slaves"""
    for slave_player in self.slave_players:
      #TODO: Catch errors here, log and pass
      slave_player.play_synced(uri, base_time, self.ip_address)
  
  def skip_forward_synced(self):
    """Skips forward then calls _play_slaves to play new track on slaves"""
    if self.playlist_index + 1 != self.playlist_length:
      self.player.set_state(gst.STATE_NULL)
      self.playlist_index += 1
      uri = self.playlist[self.playlist_index]
      self.player.set_property('uri', uri)
      base_time = self.clock.get_time()
      self.player.set_base_time(base_time)
      self.player.set_state(gst.STATE_PLAYING)
      self._play_slaves(base_time, uri)
    else:
      self.stop_synced()
  
  def skip_backward_synced(self):
    """Skips backward then calls _play_slaves to play new track on slaves"""
    if not self.playlist_index - 1 < 0:
      self.player.set_state(gst.STATE_NULL)
      self.playlist_index -= 1
      uri = self.playlist[self.playlist_index]
      self.player.set_property('uri', uri)
      base_time = self.clock.get_time()
      self.player.set_base_time(base_time)
      self.player.set_state(gst.STATE_PLAYING)
      self._play_slaves(base_time, uri)
    else:
      self.stop_synced()
      
  def stop_synced(self):
    """Stops all devices playing"""
    self.stop()
    for slave_player in self.slave_players:
      #TODO: Catch errors here, log and pass
      slave_player.stop()
  
  def set_volume_synced(self, new_volume):
    """Sets volume on devices playing"""
    self.player.set_property('volume', new_volume)
    for slave_player in self.slave_players:
      slave_player.set_volume(new_volume)
  
  def on_message(self, bus, message):
    """Handles messages on the player's bus"""
    t = message.type
    if t == gst.MESSAGE_EOS:
      if self.synced:
        self.skip_forward_synced()
      else:
        self.skip_forward()
    elif t == gst.MESSAGE_ERROR:
      self.skip_forward()
      #TODO: Handle: File descriptor in bad state
      print message
    
    
    