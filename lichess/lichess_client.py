
import logging
import os
import sys
import time
import json
import pprint
import urllib

_CACHE_DIR = os.path.join('.', '.cache')
_LOGGING_LEVEL = logging.INFO
_LOGGING_FILENAME = os.path.join('.', 'LichessClient.log')

def _cache_dir_init():
  if not os.path.lexists(_CACHE_DIR):
    os.mkdir(_CACHE_DIR)

def _logging_init():
  fmt = '%(asctime)s %(levelname)s %(message)s'
  logging.basicConfig(level=_LOGGING_LEVEL,format=fmt,filename=_LOGGING_FILENAME,filemode='a')
  console = logging.StreamHandler(sys.stdout)
  formatter = logging.Formatter(fmt)
  console.setFormatter(formatter)
  logging.getLogger('').addHandler(console)

def _module_init():
  global _NEXT_QUERY_TIME, _QUERIES, _RECV_QUERIES, _RECV_BYTES
  _logging_init()
  _cache_dir_init()
  _NEXT_QUERY_TIME = time.time()
  _QUERIES = _RECV_QUERIES = _RECV_BYTES = 0

def _url_sha512(url):
  import hashlib
  m = hashlib.sha512()
  m.update(url.encode('ascii'))
  return m.hexdigest()

def _send_query(url):
  global _NEXT_QUERY_TIME
  # To respect the API servers and avoid an IP ban, please wait 1 second between requests.
  # If you receive an HTTP response with a 429 status, please wait a full minute before resuming API usage.
  t = time.time()
  if _NEXT_QUERY_TIME > t:
    st = _NEXT_QUERY_TIME - t
    logging.debug('Sleep {0:.3f} seconds'.format(st))
    time.sleep(st)
  logging.debug('Sending query ' + url)
  response = urllib.request.urlopen(url)
  code = response.getcode()
  logging.debug('{0} status was received.'.format(code))
  if code == 429:
    logging.warn('429 status was received. Waiting full minute.')
    _NEXT_QUERY_TIME = time.time() + 60.5
    return None
  _NEXT_QUERY_TIME = time.time() + 1.1
  return response

def perform_query(query):
  global _QUERIES, _RECV_QUERIES, _RECV_BYTES
  if not ('_QUERIES' in globals()):
    _module_init()
  url = 'http://en.lichess.org/api/' + query
  logging.info('Query: ' + url)
  sha512 = _url_sha512(url)
  cache_filename = os.path.join(_CACHE_DIR, sha512)
  if not os.path.lexists(cache_filename):
    logging.info('Creating ' + cache_filename)
    f = open(cache_filename, 'wb')
    response = None
    while response == None:
      response = _send_query(url)
    s = response.read()
    f.write(s)
    f.close()
    _RECV_QUERIES += 1
    _RECV_BYTES += len(s)
  f = open(cache_filename, 'r')
  s = f.read()
  f.close()
  j = json.loads(s)
  logging.debug('Received:\n' + pprint.pformat(j, indent=2))
  _QUERIES += 1
  return j

def stats():
  logging.info('Received {0} bytes.'.format(_RECV_BYTES))
