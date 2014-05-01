"""music_scan.py: Provides music scanner class"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"


import os
import json
import urllib2
import logging
import time

import eyed3

import base_config


class MediaScanner(object):
  """Provides functions that scan a directory of MP3s for their metadata"""
  def __init__(self):
    # Musicbrainz url
    self.mb_url = 'http://musicbrainz.org/ws/2'
    # User Agent for Musicbrainz
    self.mb_user_agent = 'Pisync/0.1 +http://github.com/raspberrypifi'
    #The following variables will be setup in setup_primary_lists
    self.artists = None
    self.albums = None
    self.songs = None
    self.errors = None
    self.setup_primary_lists()
    self._mb_albums = {'Unknown Album': 'Unknown Album'}
    self._mb_artists = {'Unknown Artist': 'Unknown Artist'}
    # MusicBrainz limits to 1 request per second
    self._last_request_time = 0
    
  def setup_primary_lists(self):
    """Sets up the lists to be used throughout the process"""
    self.artists = set()
    self.artists.add(tuple({'name':'Unknown Artist'}.items()))
    self.albums = set()
    self.albums.add(tuple({'name':'Unknown Album', 'artist': ''}.items()))
    self.songs = []
    self.errors = []
      
  def search_mb(self, tag_type, name):
    """Searches the musicbrainz database for the tag_type with name"""
    while time.time() - self._last_request_time < 1:
      time.sleep(0.2)
    self._last_request_time = time.time()
    name = name.replace('"', '')
    try:
      name = urllib2.quote(name)
    except Exception:
      name = urllib2.quote(name.encode('utf8'))
    url_params = {'url':self.mb_url, 'type':tag_type, 'name':name}
    url = '%(url)s/%(type)s?query=%(type)s:"%(name)s"&fmt=json' % url_params
    request = urllib2.Request(url)
    request.add_header('User-Agent', self.mb_user_agent)
    try:
      response = urllib2.urlopen(request)
    except urllib2.HTTPError as e:
      #TODO: Deal with annoying 503s that musicbrainz gives from time to time
      logging.error('Musicbrainz HTTP Error: %s' % e.code)
      return
    response_dict = json.load(response)
    if tag_type in response_dict and response_dict[tag_type]:
      mb_result = response_dict[tag_type]
    elif tag_type + 's' in response_dict and response_dict[tag_type + 's']:
      mb_result = response_dict[tag_type+'s']
    else:
      return 
    return self._make_type_dict(tag_type, mb_result)

  def _make_type_dict(self, tag_type, mb_result):
    """Makes a dict from the result provided by musicbrainz"""
    if tag_type == 'artist':
      type_dict = {'name': mb_result[0]['name']}
    elif tag_type == 'release':
      mb_release = mb_result[0]
      release_artist = mb_release['artist-credit'][0]['artist']['name']
      type_dict = {'name': mb_release['title'], 'artist': release_artist}
    return type_dict

  def run_scan(self, source_id):
    """Starts running a scan on the source provided"""
    sources_path = os.path.expanduser(base_config.SOURCES_DIR_PATH)
    path = '%s/%s' % (sources_path, source_id)
    self.setup_primary_lists()
    for dirname, _, filenames in os.walk(path):
      for filename in (f for f in filenames if f.split('.')[-1] == 'mp3'):
        filepath = os.path.join(dirname, filename)
        try:
          audio = eyed3.load(filepath)
        except Exception:
          self.errors.append(filename)
        else:
          audio_tag = audio.tag
          audio_info = audio.info
          if not audio.info:
            self.errors.append(filename)
            continue
          if audio_tag:
            if not audio_tag.artist: 
              audio_tag.artist = u'Unknown Artist'
            if not audio_tag.album:
              audio_tag.album = u'Unknown Album'
            
            try:
              artist = self._mb_artists[audio_tag.artist]
            except KeyError:
              mb_result = self.search_mb('artist', audio_tag.artist)
              if mb_result:
                artist = mb_result
              else:
                artist = {'name': audio_tag.artist}
              self._mb_artists[audio_tag.artist] = artist
            
            self.artists.add(tuple(artist.items()))

            try:
              album = self._mb_albums[audio_tag.album]
            except KeyError:
              mb_result = self.search_mb('release', audio_tag.album)
              if mb_result:
                album = mb_result
              else:
                album = {'name':audio_tag.album, 'artist':audio_tag.artist}
              self._mb_albums[audio_tag.album] = album
              
            self.albums.add(tuple(album.items()))

            track_num, _ = audio_tag.track_num
            
            mins, secs = divmod(audio_info.time_secs, 60)
            length = '%s:%s' % (mins, str(secs).zfill(2))
              
            short_path = filepath.replace(path, '')
            self.songs.append({'name': audio_tag.title,
                          'track': track_num,
                          'album': album['name'],
                          'artist': artist['name'],
                          'source': source_id,
                          'path': short_path,
                          'length': length})

    self.albums = [dict(t) for t in self.albums]
    self.artists = [dict(t) for t in self.artists]
    if self.errors:
      logging.error('Could not scan the following files: %s' % self.errors)