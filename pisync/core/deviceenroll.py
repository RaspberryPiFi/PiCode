"""device_enroll.py: Called by new devices joining the network"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import os
import urllib2
import logging
import json

import base_config


class DeviceEnrollHandler(object):
  """Provides methods allowing a device to enroll with cloud services"""
  def __init__(self, config):
    self.config = config
    
  def enroll(self):
    """Enrolls with the cloud server and returns the new device ID"""
      json_string = json.dumps({'group_id': self.config['group_id']})
      url = '%s/api/device_enroll' % base_config.BASE_URL
      headers = {'Content-Type': 'application/json'}
      req = urllib2.Request(url, json_string, headers)
      #TODO: Add error handling for HTTP errors
      f = urllib2.urlopen(req)
      slave_config = json.loads(f.read())
      f.close()
      self._update_config(slave_config['device_id'])
      logging.info('Device enrolled, ID: %s' % slave_config['device_id'])
      return slave_config
  
  def _update_config(self, new_device_id):
    """Updates the config object and config file with the new device info"""
    self.config['slave_device_ids'].append(new_device_id)
    with open(os.path.expanduser(base_config.CONFIG_FILE_PATH), 'w') as f:
      f.seek(0)
      f.write(json.dumps(self.config))
      f.truncate()
    