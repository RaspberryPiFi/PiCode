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
import config
import traceback


class DeviceEnroll(object):
  """Provides methods allowing a device to enroll with cloud services"""
  def __init__(self,group_id):
    self.group_id = group_id
    
  def enroll(self):
    try:
      json_string = json.dumps({'group_id': self.group_id})
      url = '%s/api/device_enroll' % config.BASE_URL
      req = urllib2.Request(url, json_string, {'Content-Type': 'application/json'})
      #TODO: Add error handling for HTTP errors
      f = urllib2.urlopen(req)
      json_response = json.loads(f.read())
      f.close()
      return json_response['device_id']
    except:
      print traceback.print_exc()

def start_pyro(group_id):
  """Sets up Pyro sharing DeviceEnroll and starting the eventloop"""
  device_enroll=DeviceEnroll(group_id)
  
  #TODO: Seriously re-consider life as a programmer for using this workikaround
  ip_address = Pyro4.socketutil.getIpAddress('localhost',True)
  
  daemon=Pyro4.Daemon(host=ip_address)
  ns=Pyro4.locateNS()
  uri=daemon.register(device_enroll)
  ns.register("pisync.device_enroll", uri)
  
  print "Ready!"
  daemon.requestLoop()
  
def enroll_device():
  """runs device_enroll.enroll on Master enrolling the slave device"""
  device_enroll=Pyro4.Proxy("PYRONAME:pisync.device_enroll")
  print device_enroll.enroll()
  #TODO: Save this is json config file under user's home dir
  
  
  