"""device_enroll.py: Called by new devices joining the network"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import urllib2
import json
import Pyro4
import base_config
import traceback


class DeviceEnrollHandler(object):
  """Provides methods allowing a device to enroll with cloud services"""
  def __init__(self,group_id):
    self.group_id = group_id
    
  def enroll(self):
    try:
      json_string = json.dumps({'group_id': self.group_id})
      url = '%s/api/device_enroll' % base_config.BASE_URL
      req = urllib2.Request(url, json_string, {'Content-Type': 'application/json'})
      #TODO: Add error handling for HTTP errors
      f = urllib2.urlopen(req)
      config = json.loads(f.read())
      f.close()
      print 'Successfully enrolled! device_id: %s' % config['device_id']
      return config
    except:
      print traceback.print_exc()