# -*- encoding: utf-8 -*-
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

tabella=sys.argv[1]
#import pdb; pdb.set_trace()
fields = sock.execute(dbname, uid, pwd, tabella, 'fields_get', []) 

for key in fields.keys():
    print key, "*"*20
    for key2 in fields[key]:
        print "\t\t",key2, fields[key][key2]

#for key in fields.keys():
#    print 'Field: %25s    Label: %20s    Type: %20s'%(key, fields[key]['string'], fields[key]['type'])

