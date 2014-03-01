"""group_enroll.py: called the first time a Master starts up"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import urllib2
import random
import json
import time
import config


def enroll():
  """Completes enrollment with cloud server"""
  print 'As this is the first run, enrollment will now proceed'
  group_id,device_id,registration_code =  get_group_details()
  print 'Entering registration loop, please register this device at %s.' % config.BASE_URL
  print 'Registration code: %s' % registration_code
  start_registration_loop(group_id,registration_code)
  print 'Device successfully enrolled! Yay!'
  print 'Details:'
  print 'group_id: %s' % group_id
  print 'device_id: %s' % device_id
  #TODO: Save this is json config file under user's home dir
  
def get_group_details():
  """Sends a random number to server and if a conflict occurs, retries"""
  registration_code = str(random.randint(0, 999999)).zfill(6)
  json_string = json.dumps({'registration_code': registration_code})
  url = '%s/api/system_enroll' % config.BASE_URL
  req = urllib2.Request(url, json_string, {'Content-Type': 'application/json'})
  try:
    f = urllib2.urlopen(req)
  except urllib2.HTTPError as e:
    if e.code == 409:
      #TODO: Come back here at some point and ensure we don't DoS ourselves
      return get_group_id()
    else:
      #TODO: Log this properly when logging added!
      print e.read()
      raise e
  else:
    json_response = json.loads(f.read())
    group_id = json_response['group_id']
    device_id = json_response['device_id']
    f.close()
    return group_id,device_id,registration_code
    
def start_registration_loop(group_id, registration_code):
  """Loops until user registers the device"""
  i = 0
  while True:
    json_string = json.dumps({'group_id': group_id})
    url = '%s/api/system_enroll_status' % config.BASE_URL
    req = urllib2.Request(url, json_string, {'Content-Type': 'application/json'})
    #TODO: Add error handling for HTTP errors
    f = urllib2.urlopen(req)
    response = f.read()
    f.close()
    if json.loads(response)['registered']:
      break
    elif i == 1:
      print 'Please register this device at %s.' % config.BASE_URL
      print 'Registration code: %s' % registration_code
      i = 0
    else:
      i += 1
    time.sleep(5)
  
  
  