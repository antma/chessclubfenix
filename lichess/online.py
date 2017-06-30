#!/usr/bin/python3
# -*- coding: utf8 -*-

import lichess_client
import logging
import sys
import gi
import time

USER='buk2001'

def parse_user(value):
  global USER
  USER = value

lichess_client.add_option('u', 'user', True, parse_user, "sets username", USER)
lichess_client.init()

while True:
  d = lichess_client.perform_query('user/' + USER)
  o = d['online']
  if o:
    gi.require_version('Notify', '0.7')
    from gi.repository import Notify
    Notify.init("Lichess")
    Hello=Notify.Notification.new("Lichess",
                                   "User {0} is online".format(USER),
                                   "dialog-information")
    Hello.show()
    print("\a")
    break
  time.sleep(5*60)
lichess_client.stats()
