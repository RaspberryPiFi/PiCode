"""poller.py: Handles polling the cloud server."""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import os. path
import urllib2
import logging
import json

import Pyro4

import base_config

# Requred to access protected function
# pylint: disable=W0212


#TODO: Deal with the timeout issues without blocking!
PYRO_PARTY_TIMEOUT = 1
PYRO_STATUS_TIMEOUT = 2

class Poller(object):
  """Provides functions to poll the cloud server and handle any actions"""
  def __init__(self, config, master_player):
    self.config = config
    self.master_player = master_player
    
  def poll_for_updates(self):
    """Polls the server and calls appropriate action with response""" 
    response = self.make_request()
    if response and 'actions' in response:
      for action in response['actions']:
        logging.info('Handling Action')
        if 'party_mode' in action:
          self.handle_party_action(action)
        else:
          self.handle_action(action)
    return True
    
  def make_request(self):
    """Makes a request for updates to the cloud api"""
    statuses = self.get_device_statuses()
    json_string = json.dumps({'group_id': self.config['group_id'],
                              'statuses': statuses})
    url = '%s/api/group/update' % base_config.BASE_URL
    headers = {'Content-Type': 'application/json'}
    req = urllib2.Request(url, json_string, headers)
    #TODO: Add error handling for HTTP errors
    try:
      f = urllib2.urlopen(req)
    except Exception as e:
      logging.error('Error encountered when attempting to poll: %s' % str(e))
    else:
      response = json.loads(f.read())
      f.close()
      return response
    
  def get_device_statuses(self):
    """Returns the status of all devices"""
    if self.master_player.synced:
      statuses = {'party_mode': True}
      statuses['party'] = self.master_player.get_status()
    else:
      statuses = {'party_mode': False}
      statuses[self.config['device_id']] = self.master_player.get_status()
      for device_id in self.config['slave_device_ids']:
        try:
          slave_player = Pyro4.Proxy('PYRONAME:pisync.slave.%s' % device_id)
          slave_player._pyroTimeout = PYRO_STATUS_TIMEOUT
          status = slave_player.get_status()
        except Pyro4.errors.PyroError:
          status = {'alive': False}
        statuses[device_id] = status
    return statuses
  
  def handle_action(self, action):
    """Handles standard action"""
    master_device_id = self.config['device_id']
    if action['device_id'] == master_device_id:
      player = self.master_player
      if action['type'] == 'play_list':
        action['arg'] = self.generate_master_uris(action['arg'])
    else:
      #TODO: Handle errors when device offline
      player = Pyro4.Proxy('PYRONAME:pisync.slave.%s' % action['device_id'])
      if action['type'] == 'play_list':
        action['arg'] = self.generate_slave_uris(action['arg'])
    #TODO: Handle security here, this is not too safe right now
    if action['type'] in ['play_list','set_volume']:
      getattr(player, action['type'])(action['arg'])
    elif hasattr(player, action['type']):
      getattr(player, action['type'])()
    else:
      logging.error('Invalid action provided')
        
  def handle_party_action(self, action):
    """Handles a party mode action"""
    if action['type'] == 'play_list':
      slave_players = []
      ip_address = Pyro4.socketutil.getIpAddress('localhost', True)
      for device_id in self.config['slave_device_ids']:
        try:
          slave_player = Pyro4.Proxy('PYRONAME:pisync.slave.%s' % device_id)
          slave_player._pyroTimeout = PYRO_PARTY_TIMEOUT
          slave_players.append(slave_player)
        except Pyro4.errors.PyroError:
          logging.error('Unable to contact device: %s' % device_id)
      master_uris = self.generate_master_uris(action['arg'])
      slave_uris = self.generate_slave_uris(action['arg'])
      self.master_player.play_list_synced(slave_players, ip_address,
                                          slave_uris, master_uris)
    elif action['type'] == 'set_volume':
      self.master_player.set_volume_synced(action['arg'])
    #TODO: Handle security here, this is not too safe right now
    elif hasattr(self.master_player, '%s_synced' % action['type']):
      getattr(self.master_player, '%s_synced' % action['type'])()
    else:
      logging.error('Invalid action provided')
      
  def generate_slave_uris(self, song_locs):
    """Generates the uris for a list of songs for playing on a slave"""
    song_uris = []
    ip_address = Pyro4.socketutil.getIpAddress('localhost', True)
    base_uri = 'http://%s:8080/' % ip_address
    for song_loc in song_locs:
      song_uris.append(base_uri + song_loc['source'] + song_loc['path'])
    return song_uris
    
  def generate_master_uris(self, song_locs):
    """Generates the uris for a list of songs for playing on a master"""
    song_uris = []
    base_path = os.path.expanduser('~/.pisync/sources/')
    base_uri = 'file://%s' % base_path
    for song_loc in song_locs:
      song_uris.append(base_uri + song_loc['source'] + song_loc['path'])
    return song_uris
    
  
    
  
  
    