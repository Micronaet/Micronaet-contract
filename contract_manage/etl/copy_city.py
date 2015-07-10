# -*- encoding: utf-8 -*-
import ConfigParser,sys, os, xmlrpclib

config = ConfigParser.ConfigParser()

config.read([os.path.expanduser("~/ETL/servizi/openerp.cfg")]) 
dbname=config.get('dbaccess','dbname')
user=config.get('dbaccess','user')
pwd=config.get('dbaccess','pwd')
server=config.get('dbaccess','server')
port=config.get('dbaccess','port')  
 
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/common', allow_none=True)
uid = sock.login(dbname ,user , pwd)
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object', allow_none=True)

esito = sock.execute(dbname, uid, pwd, "account.analytic.account", "copy_filtered_city_ids")
