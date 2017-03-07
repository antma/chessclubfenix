#!/usr/bin/python3
# -*- coding: utf8 -*-

import lichess_client
import logging
import csv
import sys

#Chess Club Phoenix
TEAM='mXKFB7l2'
NB=50
ALL_VARIANTS = set('antichess,atomic,blitz,bullet,chess960,classical,correspondence,crazyhouse,horde,kingOfTheHill,opening,puzzle,racingKings,threeCheck'.split(','))
#VARIANT - comma separated list (antichess,atomic,blitz,bullet,chess960,classical,correspondence,crazyhouse,horde,kingOfTheHill,opening,puzzle,racingKings,threeCheck)
VARIANT='bullet,blitz,classical'

def parse_nb(value):
  global NB
  NB = int(value)

def parse_variants(value):
  global VARIANT
  a = value.split(',')
  for v in a:
    if not (v in ALL_VARIANTS):
      sys.stderr.write("Unknown variant name '" + v + "'\n")
      sys.stderr.write("List of known lichess variants: " + ', '.join(sorted(ALL_VARIANTS)) + '\n')
      sys.exit(1)
  VARIANT = value

def sandbox(value):
  global TEAM
  TEAM = 'bMJJlIcV'

lichess_client.add_option('n', 'nb', True, parse_nb, "sets number of users per API query", str(NB))
lichess_client.add_option('v', 'variants', True, parse_variants, "sets comma separated list of extracted variants ratings", VARIANT)
lichess_client.add_option('', 'sandbox', False, sandbox, 'Песочница')
lichess_client.init()
csv_file = open(lichess_client.get_output_filename(), 'w', newline='')
writer = csv.writer(csv_file)
variants = VARIANT.split(',')
page = 1
while True:
  d = lichess_client.perform_query('user?team={0}&nb={1}&page={2}'.format(TEAM, NB, page))
  p = d['paginator']
  r = p['currentPageResults']
  for u in r:
    row = []
    row.append(u['username'])
    logging.debug(u['username'])
    perfs = u['perfs']
    engine = u.get('engine', False)
    eliminate = 'Eliminating this player from rating list.'
    if engine:
      logging.info('{0} uses chess computer assistance. {1}'.format(u['username'], eliminate))
      continue
    booster = u.get('booster', False)
    if booster:
      logging.info('{0} artificially increases/decreases their rating. {1}'.format(u['username'], eliminate))
      continue
    for v in variants:
      rat = perfs[v]
      rate = 0
      if not rat['prov']: rate = rat['rating']
      row.append(rate)
    writer.writerow(row)
  page = p['nextPage']
  if page == None: break
csv_file.close()
lichess_client.stats()
