"""automount.py: Provides methods for listening to and reacting to new drives"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"

import os
import logging
import subprocess

import dbus
from dbus.mainloop.glib import DBusGMainLoop

import base_config

UD_STRING = 'org.freedesktop.UDisks'
UD_DEV_STRING = 'org.freedesktop.UDisks.Device'


class NewDriveListener(object):
  """Class used to start listening for new devices. Uses gobject mainloop"""
  def __init__(self, callback):
    self.callback = callback
    DBusGMainLoop(set_as_default=True)
    self.bus = dbus.SystemBus()
    self.ud_object = self.bus.get_object(UD_STRING, '/org/freedesktop/UDisks')
    self.ud_interface = dbus.Interface(self.ud_object, UD_STRING)
    self.ud_interface.connect_to_signal('DeviceAdded', self.handle_event)
    
  def handle_event(self, dev):
    """Handles a new device inserted event"""
    dev_object = self.bus.get_object(UD_STRING, dev)
    dev_interface = dbus.Interface(dev_object, dbus_interface=UD_DEV_STRING)
    dev_properties = dbus.Interface(dev_object, dbus.PROPERTIES_IFACE)
    subprocess.call(['/sbin/udevadm', 'settle'])
    if dev_properties.Get(UD_DEV_STRING, 'DeviceIsPartition'):
      partition_num =  dev_properties.Get(UD_DEV_STRING, 'PartitionNumber')
      serial_num = dev_properties.Get(UD_DEV_STRING, 'DriveSerial')
      mountpoint = self.mount(dev_interface, dev_properties)
      if mountpoint:
        source_id = self.create_symlink(mountpoint, partition_num, serial_num)
        self.callback(source_id)
      
  def mount(self, dev_interface, dev_properties):
    """Attempts to mount a drive and return mountpoint"""
    logging.info('Mounting device')
    try:
      mountpoint = dev_interface.FilesystemMount('', [])
    except dbus.DBusException as e:
      mount_props = dev_properties.Get(UD_DEV_STRING, 'DeviceMountPaths')
      if len(mount_props) == 0:
        logging.error('Unable to mount drive, error message:')
        logging.error(str(e))
        return
      else:
        mountpoint = mount_props[0]
    return mountpoint
    
  def create_symlink(self, mountpoint, partition_num, serial_num):
    """Creates a symlink using the drive's serial number and partion number"""
    source_id = '%s_P%s' % (serial_num, partition_num)
    
    sources_dir_path = os.path.expanduser(base_config.SOURCES_DIR_PATH)
    if not os.path.exists(sources_dir_path):
      os.makedirs(sources_dir_path)
    symlink_path = '%s/%s' % (sources_dir_path, source_id)
    try:
      os.remove(symlink_path)
    except OSError as e:
      if e.errno != 2:
        raise e
    os.symlink(mountpoint, symlink_path)
    return source_id
    
    
    
    
    