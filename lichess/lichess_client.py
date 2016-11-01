import logging
import os
import sys
import time
import json
import pprint
import urllib
import getopt

_CACHE_DIR = os.path.join('.', '.cache')
_LOGGING_LEVEL = logging.INFO
_LOGGING_FILENAME = os.path.join('.', 'LichessClient.log')
_OUTPUT_FILENAME = 'out'

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
    _LOGGING_LEVEL = loggging.DEBUG
  def usage(value):
    sys.stdout.write(_GETOPT_USAGE)
    sys.exit(2)
  add_option('h', 'help', False, usage, 'print help')
  add_option('o', 'output', True, set_output_filename, 'sets output file', _OUTPUT_FILENAME)
  add_option('l', 'logfile', True, set_log_filename, 'sets log file', _LOGGING_FILENAME)
  add_option('', 'debug', False, enable_debug, 'enables debug logging')

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

def init():
  global _NEXT_QUERY_TIME, _QUERIES, _RECV_QUERIES, _RECV_BYTES
  _init_module_options()
  opts, args = getopt.getopt(sys.argv[1:], _GETOPT_SHORT, _GETOPT_LONG)
  _parse_options(opts, args)
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

def get_output_filename(): return _OUTPUT_FILENAME

def stats():
  logging.info('Received {0} bytes.'.format(_RECV_BYTES))
