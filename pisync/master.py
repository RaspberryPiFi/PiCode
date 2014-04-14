"""master.py: Start up script for master device"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import threading
import logging
import urllib2
import select
import json
import os

from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor
# pylint: disable=F0401
import gobject
import Pyro4
# pylint: enable=F0401

import base_config
from pisync.core import cloudpoller
from pisync.core import deviceenroll
from pisync.core import musicscan
from pisync.core import automount
from pisync.core import player


gobject.threads_init()

class Master(object):
  """Provides methods needed by a master device"""
  def __init__(self, config):
    self.config = config
    self.master_player = player.MasterPlayer()
    ip_address = Pyro4.socketutil.getIpAddress('localhost', True)
    self.pyro_daemon = Pyro4.Daemon(host=ip_address)
    
  def install_poller_event_callback(self):
    """Add a callback to the gobject event loop to handle poller events."""
    poller = cloudpoller.Poller(self.config, self.master_player)
    gobject.timeout_add(base_config.POLL_INTERVAL, poller.poll_for_updates)

  def install_pyro_event_callback(self):
    """Add a callback to the gobject event loop to handle Pyro requests."""
    def pyro_event():
      """Handles any pyro events that need handling"""
      while True:
        s, _, _ = select.select(self.pyro_daemon.sockets, [], [], 0.01)
        if s:
          self.pyro_daemon.events(s)
        else:
          break
      return True
    gobject.timeout_add(20, pyro_event)
  
  def setup_pyro(self):
    """Sets up Pyro, sharing DeviceEnrollHandler"""
    handler = deviceenroll.DeviceEnrollHandler(self.config)
    ns = Pyro4.locateNS()
    uri = self.pyro_daemon.register(handler)
    #TODO: Handle NS not found error
    ns.register("pisync.device_enroll", uri)
    
    
  def setup_drive_listener(self):
    """Sets up new drive listener to handle new drives inserted"""
    #TODO: Consider moving this out of master.py
    media_scanner = musicscan.MediaScanner()
    lock = threading.Lock()
    def scan_drive(source_id):
      """Starts a scan on mounted device and send the results to the cloud"""
      lock.acquire()
      logging.info('Scanning starting on: %s' % source_id)
      # In some situations this can be in unicode
      media_scanner.run_scan(str(source_id))
      logging.info('Scanning completed')
      if media_scanner.songs:
        json_string = json.dumps({'group_id': self.config['group_id'],
                                  'artists':media_scanner.artists,
                                  'albums':media_scanner.albums,
                                  'songs':media_scanner.songs})
        url = '%s/api/group/library' % base_config.BASE_URL
        headers = {'Content-Type': 'application/json'}
        req = urllib2.Request(url, json_string, headers)
        #TODO: Add error handling for HTTP errors
        f = urllib2.urlopen(req)
        f.close()
      lock.release()
    def start_scan_thread(source_id):
      """calls scan_drive in a new thread"""
      t = threading.Thread(target=scan_drive, args=(source_id,))
      t.start()
    automount.NewDriveListener(start_scan_thread)
    
    
  def start_web_server(self):
    """Starts webserver for sharing media from attatched drives"""
    #TODO: Secure using basicauth over ssl
    #TODO: Use a better method of serving the files!
    def web_server(path, port):
      """Serves the static files via HTTP"""
      resource = File(path)
      factory = Site(resource)
      reactor.listenTCP(port, factory)
      reactor.run(installSignalHandlers=0)
    sources_path = os.path.expanduser(base_config.SOURCES_DIR_PATH)
    if not os.path.exists(sources_path):
      os.makedirs(sources_path)
    port = base_config.FILE_SERVE_PORT
    t = threading.Thread(target=web_server, args=(sources_path, port))
    t.daemon = True
    t.start()

  
  def start(self):
    """Calls the event callback setup methods and starts the MainLoop"""
    self.start_web_server()
    self.setup_pyro()
    self.install_pyro_event_callback()
    self.install_poller_event_callback()
    self.setup_drive_listener()
    logging.info('Starting Main Loop')
    gobject.MainLoop().run()