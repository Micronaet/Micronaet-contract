#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Modules required:
from pyExcelerator import *
import xmlrpclib, csv, sys, time, string, ConfigParser, os, pdb

# Parameters:
path_file=os.path.expanduser("~/ETL/servizi/")
cfg_file=path_file + "openerp.cfg"
file_xls=path_file + "Clienti.xls"
header_lines = 1 # riga di intestazione

# Set up parameters (for connection to Open ERP Database) ********************************************
config = ConfigParser.ConfigParser()
config.read([cfg_file]) # if file is in home dir add also: , os.path.expanduser('~/.openerp.cfg')])
dbname=config.get('dbaccess','dbname')
user=config.get('dbaccess','user')
pwd=config.get('dbaccess','pwd')
server=config.get('dbaccess','server')
port=config.get('dbaccess','port')   # verify if it's necessary: getint
separator=config.get('dbaccess','separator') # test
verbose=eval(config.get('import_mode','verbose'))  # for info message

# SMTP config read
smtp_server=config.get('smtp','server') 
verbose_mail=eval(config.get('smtp','verbose_mail'))  # for info mail
smtp_log=config.get('smtp','log_file') 
smtp_sender=config.get('smtp','sender') 
smtp_receiver=config.get('smtp','receiver') 
smtp_text=config.get('smtp','text') 
smtp_subject=config.get('smtp','subject') 

# Start main code *************************************************************
def create_partner(sock, dbname, uid, pwd, data):
    ''' Controllo se e' gia' stato inserito un partner con il ref come da codice
        in base a quello lo creo (torno False se non trovo il ref)
        Creo l'address abbinato al partner appena creato (predefinito)
        Se le tue operazioni vanno a buon fine torna True altrimenti False
    '''
    import parse_function    
    if 'ref' not in data:
       print "[ERR] Riferimento non trovato!", data
       return False
    if 'name' not in data:
       print "[ERR] Nome non trovato!", data
       return False

    data_partner={
                   'ref': str(data['ref']),
                   'name': data['name'].title(),
                   #'city',
                   #'vat',
                   #'phone',
                   #'fax',
                   'fiscal_id_code': data['fiscal_code'] if 'fiscal_code' in data else False,
                   'comment': data['note'] if 'note' in data else False,
                   #'email',
                   'import': True,
                   'customer': True,
                   'is_employee': False,                   
               }


    if 'vat' in data and len(data['vat'])==11:
          data_partner['vat'] = "IT" + data['vat'] # TODO verificare il codice nazione per metterlo davanti al VAT se non c'è

    extra_phone=""
    if 'phone1' in data: extra_phone+=data['phone1']+ "\n"
    if 'phone2' in data: extra_phone+=data['phone2']+ "\n"
    if 'phone3' in data: extra_phone+=data['phone3']+ "\n"

    item = sock.execute(dbname, uid, pwd, 'res.partner', 'search', [('ref', '=', data_partner['ref']), ('import','=',True), ('is_employee','=',False)]) 
    partner_id=0
    if item: # UPDATE:
       try:
           item_mod = sock.execute(dbname, uid, pwd, 'res.partner', 'write', item, data_partner) 
           partner_id=item[0] 
           if verbose: print "[INFO] Partner already exist: ", data_partner['ref'], data_partner['name']
       except:
           try: # scrivo senza VAT
               if 'vat' in data_partner: del data_partner['vat']
               item_mod = sock.execute(dbname, uid, pwd, 'res.partner', 'write', item, data_partner) 
               partner_id=item[0] 
               if verbose: print "[WARN] Partner already exist: ", data_partner['ref'], data_partner['name'], "** SENZA VAT **"
           except:     
               print "[ERR] modified", data_partner['ref'], data_partner['name']
    else:  # NEW
       try:
           partner_id = sock.execute(dbname, uid, pwd, 'res.partner', 'create', data_partner) 
           if verbose: print "[INFO] Create partner: ", data_partner['ref'], data_partner['name'], "** SENZA VAT **"
       except:
           try:
               if 'vat' in data_partner: del data_partner['vat']
               partner_id = sock.execute(dbname, uid, pwd, 'res.partner', 'create', data_partner) 
               if verbose: print "[WARN] Create partner: ", data_partner['ref'], data_partner['name'], "** SENZA VAT **"
           except:
               print "[ERR] modified", data_partner['ref'], data_partner['name']
    
    if partner_id:   
        # Creazione res.partner.address   
        data_address={
             'city': data['city'].title() if 'city' in data else False, # modify first import address
             #'zip': zipcode, 
             #'country_id': getCountryFromCode(sock,dbname,uid,pwd,country_international_code), 
             'phone': data['phone'] if 'phone' in data else False,
             'fax': data['fax'] if 'fax' in data else False,
             'street': data['address'] if 'address' in data else False, 
             'email': data['email'].lower() if 'email' in data else False,
             'type': 'default',
             'import': True,
             'partner_id': partner_id,
             'extra_phone': extra_phone,
             }

        item_address = sock.execute(dbname, uid, pwd, 'res.partner.address', 'search', [('partner_id','=', partner_id),('type', '=', 'default'), ])  #('import','=',True) solo sul default
        if item_address: # UPDATE:
           try:
               item_mod = sock.execute(dbname, uid, pwd, 'res.partner.address', 'write', item_address, data_address) 
           except:
               print "[ERR]    Modified address", data_address

           if verbose: print "[INFO]    Address already exist: ", data_address
        else:  # NEW
           try:
               partner_id = sock.execute(dbname, uid, pwd, 'res.partner.address', 'create', data_address) 
           except:
               print "[ERR]    Address modified", data_address

           if verbose: print "[INFO]    Create address exist: ", data_address
   
    return True

# XMLRPC connection for autentication (UID) and proxy 
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/common', allow_none=True)
uid = sock.login(dbname ,user ,pwd)
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object', allow_none=True)

#import pdb; pdb.set_trace()
for sheet_name, values in parse_xls(file_xls, 'cp1251'): # apro il file di excel
    old_row = -1
    data = {}
    header = ['ref','name','address','city','vat','fiscal_code','phone','fax','note','phone1','phone2','phone3','email',]

    for row_idx, col_idx in sorted(values.keys()):
        if not row_idx: continue # jump first header lines
        if old_row==-1: old_row = row_idx # primo record
        if row_idx != old_row: # su rottura di codice scrivo la riga
            create_partner(sock, dbname, uid, pwd, data)
            old_row=row_idx
            data={}
           
        v = values[(row_idx, col_idx)]
        if isinstance(v, unicode):
            riga = v.encode('cp866', 'backslashreplace')
        else:
            riga = str(v)
        data[header[col_idx]] = v

    if data:  # ultima scrittura
       create_partner(sock, dbname, uid, pwd, data)
