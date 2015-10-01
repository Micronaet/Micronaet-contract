# -*- encoding: utf-8 -*-
# List field and first 5 element of table in argv
import xmlrpclib,ConfigParser,sys, os

# Set up parameters (for connection to Open ERP Database) ********************************************
# Set up parameters (for connection to Open ERP Database) ********************************************
config = ConfigParser.ConfigParser()
config_file=os.path.expanduser("~/ETL/servizi/openerp.cfg")
config.read([config_file]) # if file is in home dir add also: , os.path.expanduser('~/.openerp.cfg')])
dbname=config.get('dbaccess','dbname')
user=config.get('dbaccess','user')
pwd=config.get('dbaccess','pwd')
server=config.get('dbaccess','server')
port=config.get('dbaccess','port')   # verify if it's necessary: getint
 
# For final user: Do not modify nothing below this line (Python Code) ********************************
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/common')
uid = sock.login(dbname ,user ,pwd)
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object')

contract_ids=sock.execute(dbname, uid, pwd, 'account.analytic.account', 'search', [('code','!=',False),])#[('code','=',False)])
con_codice= [contratto['code'] for contratto in sock.execute(dbname, uid, pwd, 'account.analytic.account', 'read', contract_ids)]

print "CORREGGERE:"
contract_ids=sock.execute(dbname, uid, pwd, 'account.analytic.account', 'search', [('code','=',False),('line_ids','=',False)])
senza_codice= ["Nome: %s Codice: %s"%(contratto['name'], contratto['code']) for contratto in sock.execute(dbname, uid, pwd, 'account.analytic.account', 'read', contract_ids) if contratto['name'][:7] in con_codice]
id_eliminare= [contratto['id'] for contratto in sock.execute(dbname, uid, pwd, 'account.analytic.account', 'read', contract_ids) if contratto['name'][:7] in con_codice]
print senza_codice

print "ELIMINO:"
contract_elimare_ids=sock.execute(dbname, uid, pwd, 'account.analytic.account', 'unlink', id_eliminare)
print "eliminati", id_eliminare

#contract_read=sock.execute(dbname, uid, pwd, 'account.analytic.account', 'read', contract_ids)
#totale=0

#print "CONTRATTI DA CANCELLARE!"
#for contract in contract_read:
#   print "***** CODICE RICAVATO: %s NOME: %s Lista rapportini: %s"%(contract['name'][:7],contract['name'],contract['line_ids'])
#   totale += len(contract['line_ids'])
   
#print "TOTALE", totale
#tabella='account.analytic.line'
#tabella_id = sock.execute(dbname, uid, pwd, tabella, 'search', []) 

