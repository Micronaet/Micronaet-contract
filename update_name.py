#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import os
import sys
import xmlrpclib


# XMLRPC connection for autentication (UID) and proxy 
server = '192.168.1.21' #'localhost'
port = 8069
dbname = 'fratservizi'
user = 'admin'
pwd = 'password'

sock = xmlrpclib.ServerProxy(
    'http://%s:%s/xmlrpc/common' % (server, port), allow_none=True)
uid = sock.login(dbname, user, pwd)
sock = xmlrpclib.ServerProxy(
    'http://%s:%s/xmlrpc/object' % (server, port), allow_none=True)

item_ids = sock.execute( # search current ref
   dbname, uid, pwd, 'hr.employee.force.hour.wizard', 
   'force_update_product_analytic_line')

