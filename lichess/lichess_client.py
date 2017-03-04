# -*- coding: utf8 -*-

import email
import email.utils
import getopt
import glob
import gzip
import json
import logging
import os
import pickle
import pprint
import sys
import time
import urllib
import urllib.request

_CACHE_DIR = os.path.join('.', '.cache')
_LOGGING_LEVEL = logging.INFO
_LOGGING_FILENAME = os.path.join('.', 'LichessClient.log')
_OUTPUT_FILENAME = 'out'
_QUERIES_DELAY = 2.0

_GETOPT_SHORT = "l:o:"
_GETOPT_LONG = ['debug']
_GETOPT_FUNC = {}
_GETOPT_USAGE = ''

def add_option(short_option, long_option, has_argument, func, help_str, default_value = None):
  global _GETOPT_SHORT, _GETOPT_LONG,  _GETOPT_FUNC, _GETOPT_USAGE
  name = ''
  if len(short_option) == 1:
    _GETOPT_SHORT += short_option
    if has_argument: _GETOPT_SHORT += ':'
    name = '-' + short_option
    _GETOPT_FUNC[name] = func
  if len(long_option) > 0:
    e = ''
    if has_argument: e = '='
    _GETOPT_LONG.append(long_option + e)
    if len(name) > 0: name += '/'
    else: name += ' ' * 3
    name += '--' + long_option
    _GETOPT_FUNC['--' + long_option] = func
  if isinstance(default_value, str): help_str += ". Default value is '" + default_value + "'."
  _GETOPT_USAGE += name + '\t' + help_str + '\n'

def _init_module_options():
  def set_log_filename(value):
    global _LOGGING_FILENAME
    _LOGGING_FILENAME = value
  def set_output_filename(value):
    global _OUTPUT_FILENAME
    _OUTPUT_FILENAME = value
  def enable_debug(value):
    global _LOGGING_LEVEL
    _LOGGING_LEVEL = logging.DEBUG
  def set_delay(value):
    global _QUERIES_DELAY
    _QUERIES_DELAY = float(value)
    if _QUERIES_DELAY < 1.0:
      sys.stdout.write('Delay is too small (must be at least one second)\n')
      usage(value)
  def usage(value):
    sys.stdout.write(_GETOPT_USAGE)
    sys.exit(2)
  add_option('h', 'help', False, usage, 'print help')
  add_option('o', 'output', True, set_output_filename, 'sets output file', _OUTPUT_FILENAME)
  add_option('l', 'logfile', True, set_log_filename, 'sets log file', _LOGGING_FILENAME)
  add_option('', 'debug', False, enable_debug, 'enables debug logging')
  add_option('d', 'delay', True, set_delay, 'sets delay between queries', str(_QUERIES_DELAY))

def _parse_options(opts, args):
  if len(args) > 0:
    _GETOPT_FUNC['-h'](None)
    sys.stderr.write('Unparsed args ' + str(args) + '\n')
    sys.exit(1)
  for option, value in opts:
    func = _GETOPT_FUNC.get(option)
    if func == None:
      _GETOPT_FUNC['-h'](None)
      sys.stderr.write('Unknown option ' + option + '\n')
      sys.exit(1)
    func(value)

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

class _CacheFileInfo:
  def __init__(self, path):
    self.path = path
    self.info_path = path + '.info'
    f = open(self.info_path, 'rb')
    self.url = pickle.load(f)
    self.headers = pickle.load(f)
    f.close()
  def expired(self):
    expired_date = self.headers.get('Expires')
    if isinstance(expired_date, str):
      logging.debug(self.path + ' expired at ' + expired_date)
      date_tuple = email.utils.parsedate_tz(expired_date)
      if date_tuple:
        et = email.utils.mktime_tz(date_tuple)
        ct = time.time()
        if et >= ct:
          logging.debug('Valid ' + str(et - ct) + ' seconds.')
          return False
    return True

def _rescan_cache():
  for fn in glob.glob(os.path.join(_CACHE_DIR, '*.info')):
    logging.debug('Found cache file ' + fn)
    cfi = _CacheFileInfo(fn[:-5])
    if cfi.expired():
      logging.info(cfi.url + ' was expired.')
      logging.info('Removing ' + cfi.path)
      if os.path.lexists(cfi.path): os.unlink(cfi.path)
      if os.path.lexists(fn): os.unlink(fn)

def init():
  global _NEXT_QUERY_TIME, _QUERIES, _RECV_QUERIES, _RECV_BYTES
  _init_module_options()
  opts, args = getopt.getopt(sys.argv[1:], _GETOPT_SHORT, _GETOPT_LONG)
  _parse_options(opts, args)
  _logging_init()
  _cache_dir_init()
  _rescan_cache()
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
  try:
     req = urllib.request.Request(url)
     req.add_header('Accept-Encoding', 'gzip')
     response = urllib.request.urlopen(req)
  except urllib.error.HTTPError as err:
    if err.code == 429:
      logging.warn('429 error was received. Waiting full minute.')
      _NEXT_QUERY_TIME = time.time() + 60.0 * 1.05
      return None
    else: raise
  code = response.getcode()
  logging.debug('{0} status was received.'.format(code))
  if code == 429:
    logging.warn('429 status was received. Waiting full minute.')
    _NEXT_QUERY_TIME = time.time() + 60.0 * 1.05
    return None
  _NEXT_QUERY_TIME = time.time() + _QUERIES_DELAY * 1.05
  return response

def perform_query(query):
  global _QUERIES, _RECV_QUERIES, _RECV_BYTES
  url = 'http://en.lichess.org/api/' + query
  sha512 = _url_sha512(url)
  cache_filename = os.path.join(_CACHE_DIR, sha512)
  if not os.path.lexists(cache_filename):
    logging.info('Query: ' + url)
    response = None
    while response == None:
      response = _send_query(url)
    f = open(cache_filename + '.info', 'wb')
    pickle.dump(url, f)
    pickle.dump(response.headers, f)
    f.close()
    logging.info('Creating ' + cache_filename)
    f = open(cache_filename, 'wb')
    s = response.read()
    response.close()
    _RECV_QUERIES += 1
    _RECV_BYTES += len(response.headers) + len(s)
    f.write(s)
    f.close()
  else:
    logging.info('Use cached copy for query ' + url)
  cbf = _CacheFileInfo(cache_filename)
  logging.debug(cbf.headers)
  f = open(cache_filename, 'rb')
  s = f.read()
  f.close()
  if cbf.headers.get('Content-Encoding') == 'gzip':
    compressed_size = len(s)
    s = gzip.decompress(s)
    logging.debug('{0} compressed ratio = {1:.3f}%'.format(cbf.url, (100.0 * compressed_size) / len(s)))
  charset = cbf.headers.get_content_charset()
  logging.debug('Response charset is ' + charset)
  s = s.decode(charset)
  j = json.loads(s)
  logging.debug('Parsed JSON:\n' + pprint.pformat(j, indent=2))
  _QUERIES += 1
  return j

def get_output_filename(): return _OUTPUT_FILENAME

def stats():
  logging.info('Received {0} bytes.'.format(_RECV_BYTES))
