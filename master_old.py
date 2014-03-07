"""master.py: Start up script for master device"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import os.path
import threading
import gobject
import json

from modules import group_enroll
from modules import player
from modules import poller_new

gobject.threads_init()

class Loader(object):
  def __init__(self):
    self.master_config = self.get_master_config()
    self.master_player = player.Player()
    
  def get_master_config(self):
    """Reads pisync.json file or enrolls and returns master config"""
    if os.path.isfile(os.path.expanduser("~/.pisync.json")):
      try:
        with open(os.path.expanduser("~/.pisync.json")) as f:
          master_config = json.loads(f.read())
          print "Configuration Loaded - Group ID: %s" % master_config['group_id']
      except IOError as e:
        print 'Error loading configuration file!'
        raise
    else:
      print 'No Configuration file found, enrolling with cloud server'
      group_id, device_id = group_enroll.enroll()
      master_config = {'group_id': group_id, 'device_id': device_id}
      json_string = json.dumps(master_config)
      with open(os.path.expanduser("~/.pisync.json"), "w") as f:
        f.write(json_string)
    return master_config
  
  def start(self):
    t = threading.Thread(target=poller_new.start_polling, args=(self.master_config,self.master_player))
    t.start()
    print 'Starting main_loop'
    gobject.MainLoop().run()

def main():
  Loader().start()


if __name__ == "__main__":
  main()