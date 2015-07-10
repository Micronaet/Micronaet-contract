# -*- encoding: utf-8 -*-
#!/usr/bin/python

# List field and first 5 element of table in argv
import xmlrpclib,ConfigParser,sys, os

# Set up parameters (for connection to Open ERP Database) ********************************************
# Set up parameters (for connection to Open ERP Database) ********************************************
path_file=os.path.expanduser("~/ETL/servizi/")
config = ConfigParser.ConfigParser()
config.read([path_file + 'openerp.cfg']) # if file is in home dir add also: , os.path.expanduser('~/.openerp.cfg')])
dbname=config.get('dbaccess','dbname')
user=config.get('dbaccess','user')
pwd=config.get('dbaccess','pwd')
server=config.get('dbaccess','server')
port=config.get('dbaccess','port')   # verify if it's necessary: getint
 
# For final user: Do not modify nothing below this line (Python Code) ********************************
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/common')
uid = sock.login(dbname ,user ,pwd)
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')

fields = sock.execute(dbname, uid, pwd, "hr.employee", 'check_consistency_employee_user_department') 

