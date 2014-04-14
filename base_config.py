"""config.py: Some static configuration options"""

__author__ = "Tom Hanson"
__copyright__ = "Copyright 2014"
__credits__ = ["Tom Hanson"]

__license__ = "GPL"
__maintainer__ = "Tom Hanson"
__email__ = "tom@aporcupine.com"


BASE_URL = 'http://pi-sync.appspot.com'
CONFIG_DIR = '~/.pisync'
CONFIG_FILE_NAME = 'config.json'
LOG_FILE_NAME = 'pisync.log'
SOURCES_DIR_NAME = 'sources'
LOG_FILE_PATH = '%s/%s' % (CONFIG_DIR, LOG_FILE_NAME)
CONFIG_FILE_PATH = '%s/%s' % (CONFIG_DIR, CONFIG_FILE_NAME)
SOURCES_DIR_PATH = '%s/%s' % (CONFIG_DIR, SOURCES_DIR_NAME)
FILE_SERVE_PORT = 8080
POLL_INTERVAL = 2000