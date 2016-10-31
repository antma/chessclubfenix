#!/usr/bin/python3

import lichess_client
import logging
import csv

#Chess Club Phoenix
TEAM='mXKFB7l2'
NB=50
VARIANT='bullet,blitz,classical'
CSV_OUT_FILENAME = 'out.csv'

csv_file = open(CSV_OUT_FILENAME, 'w', newline='')
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
