"""group_enroll.py: called the first time a Master starts up"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import logging
import urllib2
import random
import json
import os

import gobject

import base_config
from pisync.core import player


class GroupEnrollHandler(object):
  """Provides methods allowing a group to enroll with cloud services"""
  def __init__(self):
    self.player = player.Player()
    self.mainloop = gobject.MainLoop()
    self.registered = False
  
  def enroll(self):
    """Completes enrollment with cloud server"""
    config, registration_code =  self.get_group_details()
    logging.info('Entering group registration loop')
    self.start_registration_loop(config['group_id'], registration_code)
    logging.info('Device successfully enrolled!')
    logging.info('group_id: %s' % config['group_id'])
    logging.info('device_id: %s' % config['device_id'])
    return config
    
  def get_group_details(self):
    """Sends a random number to server and if a conflict occurs, retries"""
    registration_code = str(random.randint(0, 999999)).zfill(6)
    json_string = json.dumps({'registration_code': registration_code})
    url = '%s/api/system_enroll' % base_config.BASE_URL
    headers = {'Content-Type': 'application/json'}
    req = urllib2.Request(url, json_string, headers)
    try:
      f = urllib2.urlopen(req)
    except urllib2.HTTPError as e:
      if e.code == 409:
        #TODO: Come back here at some point and ensure we don't DoS ourselves
        return self.get_group_details()
      else:
        #Rather than logging here, raising should cause it to be elsewhere
        raise e
    else:
      config = json.loads(f.read())
      f.close()
      return config, registration_code
      
  def check_if_registered(self, group_id):
    """Checks if registered and if so stops the mainloop"""
    json_string = json.dumps({'group_id': group_id})
    url = '%s/api/system_enroll_status' % base_config.BASE_URL
    headers = {'Content-Type': 'application/json'}
    req = urllib2.Request(url, json_string, headers)
    #TODO: Add error handling for HTTP errors
    f = urllib2.urlopen(req)
    response = f.read()
    f.close()
    if json.loads(response)['registered'] and self.mainloop.is_running:
      self.mainloop.quit()
      self.registered = True
      return False
    else:
      return True
      
  def play_intro(self, registration_code):
    """Plays the registration number and welcome message"""
    if self.registered:
      self.player = None
      return False
    registration_string = str(registration_code)
    path = 'file://%s/mp3s' % os.path.abspath(__file__).rsplit('/', 2)[0]
    playlist = ['%s/intro.mp3' % path]
    playlist += ['%s/%s.mp3' % (path, number) for number in registration_string]
    self.player.play_list(playlist)
    return True
      
  def start_registration_loop(self, group_id, registration_code):
    """Loops until user registers the device"""
    gobject.timeout_add(30000, self.play_intro, registration_code)
    gobject.timeout_add(5000, self.check_if_registered, group_id)
    self.play_intro(registration_code)
    self.mainloop.run()
    
  
  
  
  