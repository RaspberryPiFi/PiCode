"""poller.py: Handles polling the cloud server."""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import urllib2
import base_config
import json
import traceback

import Pyro4


#TODO: Decide whether or not to make this into a class
def poll_for_updates(master_config, master_player):
  """Polls the server and calls appropriate action with response"""
  print 'Polling...'
  response = make_request(master_config['group_id'])
  if 'actions' in response:
    for action in response['actions']:
      print 'Handling Action'
      handle_action(action, master_player, master_config['device_id'])
  
def make_request(group_id):
  json_string = json.dumps({'group_id': group_id})
  url = '%s/api/group/update' % base_config.BASE_URL
  req = urllib2.Request(url, json_string, {'Content-Type': 'application/json'})
  #TODO: Add error handling for HTTP errors
  f = urllib2.urlopen(req)
  response = json.loads(f.read())
  f.close()
  return response

def handle_action(action, master_player, master_device_id):
  if 'party_mode' in action:
    handle_party_action(action, master_player, master_device_id)
  else:
    if action['device_id'] == master_device_id:
      player = master_player
    else:
      player = Pyro4.Proxy('PYRONAME:pisync.slave.%s' % action['device_id'])
    #TODO: Handle security here, this is not too safe right now
    if action['type'] in ['play_list','set_volume']:
      getattr(player, action['type'])(action['arg'])
    elif hasattr(player, action['type']):
        getattr(player, action['type'])()
    else:
      print 'Invalid action provided'
      
def handle_party_action(action, master_player, master_device_id):
  """Currently only plays one track on all devices, need to sort playlists"""
  if action['type'] == 'play_list':
    slave_players = []
    ip_address = Pyro4.socketutil.getIpAddress('localhost',True)
    for device_id in action['device_ids']:
      if device_id != master_device_id:
        try:
          slave_player = Pyro4.Proxy('PYRONAME:pisync.slave.%s' % device_id)
          slave_players.append(slave_player)
        except:
          traceback.print_exc()
    
    master_player.play_list_synced(action['arg'], slave_players, ip_address)
  elif action['type'] == 'set_volume':
      master_player.set_volume_synced(action['arg'])
  elif hasattr(master_player, '%s_synced' % action['type']):
    getattr(master_player, '%s_synced' % action['type'])()
  else:
    print 'Invalid action provided'
  

  


  