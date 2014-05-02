"""player.py: Provies gstreamer playing with controlling fucntions"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import logging
import os

from Pyro4.errors import PyroError
import pygst
pygst.require('0.10')
import gst

# Lots of attributes defined outside the __init__ methods in here
# pylint: disable=W0201

class Player(object):
  """Provides methods for playback on slave devices"""
  def __init__(self):
    self.playlist = []
    self.playlist_index = 0
    self.playlist_length = 0
    self.curr_artist = ''
    self.curr_title = ''
    self.curr_volume = 0.5
    self.synced = False
    # Player will be setup in reset_player
    self.player = None 
    self.reset_player()
    
  def reset_player(self):
    """Resets the player back to original state"""
    if self.player:
      # pylint: disable=E0203
      self.player.set_state(gst.STATE_NULL)
      # pylint: enable=E0203
    self.player = gst.element_factory_make('playbin2', 'player')
    self.player.set_property('volume', float(self.curr_volume))
    bus = self.player.get_bus()
    bus.add_signal_watch()
    bus.connect('message', self.on_message)
  
  def get_status(self):
    """Returns the status of the player"""
    curr_state = self.player.get_state()[1]
    if curr_state == gst.STATE_PLAYING: 
      state = 'playing'
    elif curr_state == gst.STATE_PAUSED:
      state = 'paused'
    else: 
      state = 'stopped'
    return {'alive': True, 'volume': self.curr_volume, 'state': state,
            'now_playing': '%s - %s' % (self.curr_title, self.curr_artist)}
    
  def play_list(self, playlist):
    """Starts playing the playlist provided"""
    if self.synced:
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
    self.curr_title = ''
    self.curr_artist = ''
  
  def skip_forward(self):
    """Stops the current audio and plays the next in the playlist"""
    self.player.set_state(gst.STATE_NULL)
    if self.playlist_index + 1 < self.playlist_length:
      self.curr_title = ''
      self.curr_artist = ''
      self.playlist_index += 1
      self.player.set_property('uri', self.playlist[self.playlist_index])
      self.player.set_state(gst.STATE_PLAYING)
  
  def skip_backward(self):
    """Stops the current audio and plays the previous in the playlist"""
    if self.player.get_state()[1] == gst.STATE_PLAYING:
      self.player.set_state(gst.STATE_NULL)
      if not self.playlist_index - 1 < 0:
        self.curr_title = ''
        self.curr_artist = ''
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
    self.player.set_property('volume', float(volume))
    if not self.synced:
      self.curr_volume = float(volume)
  
  def test_tone(self):
    """Plays the test tone"""
    if self.synced:
      self.reset_player()
      self.synced = False
    self.player.set_state(gst.STATE_NULL)
    self.playlist_length = 1
    self.playlist_index = 0
    path = os.path.abspath(__file__).rsplit('/', 2)[0] + '/mp3s'
    uri = 'file://%s/testtone.mp3' % path
    self.player.set_property('uri', uri )
    self.player.set_state(gst.STATE_PLAYING)
    
  def _handle_tag(self, message):
    """Handles a tag message on the bus"""
    tag = message.parse_tag()
    try:
      self.curr_title = tag['title']
    except KeyError:
      pass
    try:
      self.curr_artist = tag['artist']
    except KeyError:
      pass
    
  def handle_eos(self):
    """Handles eos event"""
    self.curr_title = ''
    self.curr_artist = ''
    if self.synced == False:
      self.skip_forward()
      
  def handle_error(self, message):
    """Handles gstreamer error"""
    error = message.parse_error()
    if 'error: Invalid Device' in error[1]:
      self.reset_player()
      if not self.synced:
        self.player.set_property('uri', self.playlist[self.playlist_index])
        self.player.set_state(gst.STATE_PLAYING)
    else:
      self.skip_forward()
    logging.error(error[1])
    
  def on_message(self, _, message):
    """Handles messages on the player's bus"""
    t = message.type
    if t == gst.MESSAGE_TAG:
      self._handle_tag(message)
    elif t == gst.MESSAGE_EOS:
      self.handle_eos()
    elif t == gst.MESSAGE_ERROR:
      self.handle_error(message)
      
      
class SlavePlayer(Player):
  """Adds ability to play audio synchronised with a master device"""
  def play_synced(self, uri, base_time, ip_address, volume):
    """Plays specified URI in sync with the master"""
    self.curr_sync_args = uri, base_time, ip_address, volume
    self.synced = True
    self.player.set_state(gst.STATE_NULL)
    self.player.set_new_stream_time(gst.CLOCK_TIME_NONE)
    clock = gst.NetClientClock(None, ip_address, 5637, base_time)
    self.player.use_clock(clock)
    self.player.set_property("uri", uri)
    self.player.set_base_time(base_time)
    self.player.set_property('volume', float(volume))
    self.player.set_state(gst.STATE_PLAYING)
    
  def handle_error(self, message):
    """Handles gstreamer errors"""
    error = message.parse_error()
    if 'error: Invalid Device' in error[1]:
      self.reset_player()
      if not self.synced:
        self.player.set_property('uri', self.playlist[self.playlist_index])
        self.player.set_state(gst.STATE_PLAYING)
      else:
        self.play_synced(*self.curr_sync_args)
    else:
      self.skip_forward()
    logging.error(error[1])
    
      
class MasterPlayer(Player):
  """Adds synchronised playing, providing the clock to and controlling slaves"""
  def __init__(self):
    self.synced_volume = 0.5
    super(MasterPlayer, self).__init__()
    
  def _setup_synced_player(self):
    """Sets up clock and provides it over the network"""
    self.player.set_state(gst.STATE_NULL)
    # May need to create a new player here, we'll see!
    self.clock = self.player.get_clock()
    self.player.use_clock(self.clock)
    self.clock_provider = gst.NetTimeProvider(self.clock, None, 5637)
    self.player.set_new_stream_time(gst.CLOCK_TIME_NONE)
    self.player.set_property('volume', float(self.synced_volume))
    
  def get_status(self):
    """Returns the status of the player"""
    curr_state = self.player.get_state()[1]
    if self.synced:
      curr_volume = self.synced_volume
    else: 
      curr_volume = self.curr_volume
    if curr_state == gst.STATE_PLAYING:
      state = 'playing'
    elif curr_state == gst.STATE_PAUSED:
      state = 'paused'
    else:
      state = 'stopped'
    return {'alive': True, 'volume': curr_volume, 'state': state,
            'now_playing': '%s - %s' % (self.curr_title, self.curr_artist)}
    
    
  def _play_synced(self):
    """Starts synchronised playing with all slaves"""
    self.player.set_state(gst.STATE_NULL)
    master_uri = self.playlist[self.playlist_index]
    slave_uri = self.slave_playlist[self.playlist_index]
    self.player.set_property('uri', master_uri)
    base_time = self.clock.get_time()
    self.player.set_base_time(base_time)
    self.player.set_state(gst.STATE_PLAYING)
    volume = self.synced_volume
    for slave_player in self.slave_players:
      try:
        slave_player.play_synced(slave_uri, base_time, self.ip_address, volume)
      except PyroError:
        logging.error('Could not contact a device')
    
  def play_list_synced(self, slave_players, ip_address, 
                       slave_playlist, master_playlist, index=0):
    """Starts playing the playlist provided locally and on slaves"""
    self.synced = True
    self.ip_address = ip_address
    self.slave_players = slave_players
    self.playlist = master_playlist
    self.slave_playlist = slave_playlist
    self.playlist_index = index
    self.playlist_length = len(self.playlist)
    self._setup_synced_player()
    self._play_synced()
  
  def skip_forward_synced(self):
    """Skips forward then calls _play_slaves to play new track on slaves"""
    if self.synced:
      if self.player.get_state()[1] == gst.STATE_PLAYING:
        if self.playlist_index + 1 != self.playlist_length:
          self.curr_title = ''
          self.curr_artist = ''
          self.playlist_index += 1
          self._play_synced()
        else:
          self.stop_synced()
  
  def skip_backward_synced(self):
    """Skips backward then calls _play_slaves to play new track on slaves"""
    if self.synced:
      self.curr_title = ''
      self.curr_artist = ''
      if not self.playlist_index - 1 < 0:
        self.playlist_index -= 1
      self._play_synced()
      
  def stop_synced(self):
    """Stops all devices playing"""
    if self.synced:
      self.synced = False
      self.curr_title = ''
      self.curr_artist = ''
      self.stop()
      for slave_player in self.slave_players:
        try:
          slave_player.stop()
        except PyroError:
          logging.error('Could not contact a device')
      self.reset_player()
  
  def set_volume_synced(self, new_volume):
    """Sets volume on devices playing"""
    if self.synced:
      self.set_volume(new_volume)
      self.synced_volume = float(new_volume)
      for slave_player in self.slave_players:
        try:
          slave_player.set_volume(new_volume)
        except PyroError:
          logging.error('Could not contact a device')
          
  def handle_eos(self):
    """Handles eos event"""
    self.curr_title = ''
    self.curr_artist = ''
    if self.synced:
      self.skip_forward_synced()
    else:
      self.skip_forward()
      
  def handle_error(self, message):
    """Handles gstreamer error"""
    error = message.parse_error()
    # This current section attempts to workaround the alsa: file descriptor in bad state issue
    if ('error: Invalid Device' in error[1] or
       'streaming stopped, reason not-negotiated' in error[1]):
      self.reset_player()
      if self.synced:
        self.play_list_synced(self.slave_players, self.ip_address, self.slave_playlist,
                              self.playlist, self.playlist_index)
      else:
        self.player.set_property('uri', self.playlist[self.playlist_index])
        self.player.set_state(gst.STATE_PLAYING)
    else:
      if self.synced:
        self.skip_forward_synced()
      else:
        self.skip_forward()
    logging.error(error[1])
    
    
    