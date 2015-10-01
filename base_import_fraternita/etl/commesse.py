#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Modules required:
from pyExcelerator import *
import xmlrpclib, csv, sys, time, string, ConfigParser, os, pdb
from parse_function import *

'''
# File TIPO_ASSUNZIONE:
tipo_assunzione= {1:"CONTRATTO TEMPO DETERMINATO", 
                  2:"PROROGA CONTRATTO DETERMINATO", 
                  3:"TEMPO INDETERMINATO"}

# File TIPO_CDC:
tipo_cdc= {1: "Letture",
           2: "Postalizzazione",
           5: "Segnaletica",
           10: "Cartografia e rilievi",
           40: "Generale",
           #50: "Logistica",
           60: "Acqua",
           #80: "Letture Italia",
}

# File TP_MANSIONE:
tp_mansione= {
            1: "LETTURISTA",
            2: "POSTINO",
            3: "CAPOSQUADRA_SEGNALETICA",
            4: "OPERAIO SEGNALETICA",
            5: "IMPIEGATO AMMINISTRATIVO",
            6: "RESPONSABILE DI SETTORE",
            7: "RESPONSABILE DI COMMESSA",
            8: "DIRIGENTE",
            9: "GEOMETRA",
            10: "TECNICO CARTOGRAFO",
            11: "AUSIALIRE DELLA SOSTA/TRAFFICO",
}

# File TP_STATO:
tp_stato= {
        0: "DIMESSO",
        1: "COLLABORATORE",
        2: "COPRO",
        3: "DIPENDENTE",
        4: "TIROCIONO",
        5: "STAGISTA",
        6: "VOLONTARIO",
        }

# File RESPONSABILI:
responsabili= {
            0: "QUARTINI",
            1: "MOLETTA",
            2: "RASORI",
            3: "FEDELI",
            4: "PANCHIERI",
            5: "STOFLER",
            6: "POLLIO",
}
'''

# Parameters:
path_file=os.path.expanduser("~/ETL/servizi/")
cfg_file=path_file + "openerp.cfg"
file_xls=path_file + "COMMESSE.xls"
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

code_from="2012052" # NOTE update only code > code_from

# Start main code *************************************************************
def create_contract(sock, dbname, uid, pwd, data):
    ''' Creazione commessa:
        1. Creazione conto analitico senza padre= commessa
        2. Creazione voce figlio con unico centro di costo
    '''
    # account.analytic.account: ************************************************
    if 'CONSIDERO' not in data or not data['CONSIDERO']: # Jump line
       print "[INFO] Riga saltata!", data       
       return False 
       
    # Controlli precreazione:
    if 'ref' not in data:
       print "[ERR] Riferimento non trovato!", data
       return False

    # campi generici calcolati per tutti
    ref= data['ref']
    description = "%s\n%s"%("name" in data and data['name'], "note" in data and data['note'] or "")

    #header = ['ref','name','RESPONSABILE','partner_id','date','CDC','ID_AZIENDA','note','GRUPPO','total_amount','DETERMINA','IMAGECONTRATTO','CONSIDERO','DA_ECLUDERE_RECUPERI','PERMESSI','FERIE','MALATTIA']
    #header = ['ref','name','RESPONSABILE','partner_id','date','attiva','CDC','note','GRUPPO','total_amount','DETERMINA','IMAGECONTRATTO','CONSIDERO','DA_ECLUDERE_RECUPERI','TIPO_GIORNALIERA','ATTIVITA_PRED']
    header = ['ref','name','RESPONSABILE','partner_id','date','ATTIVA','CDC','note','GRUPPO','total_amount','DETERMINA','IMAGECONTRATTO','CONSIDERO','DA_ECLUDERE_RECUPERI','PERMESSI','FERIE','MALATTIA']
    
    data_account={
                 'code': ref,
                 #'contact_id'
                 #'currency_id'
                 'partner_id': getPartner_not_employee(sock, dbname, uid, pwd, data['partner_id']) if 'partner_id' in data else False,
                 #'to_invoice', # per le fatture automatiche (oggetto:  hr_timesheet_invoice.factor)
                 #'user_id'
                 'date': False, # TODO fine commessa
                 'date_start': prepare_date_xls(data['date']) if 'date' in data else False, #TODO format ISO
                 #'company_id'
                 'parent_id': False,
                 #'pricelist_id': False,
                 'type': 'normal',
                 'description': description.strip(),
                 'name': (ref + " " + description).strip(), # NOTE: name=code for contract
                 'quantity': 0.0,
                 'total_amount': data['total_amount'] if 'total_amount' in data else 0.0,
                 'department_id': get_department(sock, dbname, uid, pwd, data['CDC'])
                 }
    
    item = sock.execute(dbname, uid, pwd, 'account.analytic.account', 'search', [('code', '=', ref),('parent_id','=',False)])
    account_id = 0
    if item: # UPDATE:
       try:
           if ref >= code_from:
              item_mod = sock.execute(dbname, uid, pwd, 'account.analytic.account', 'write', item, data_account) 
              account_id=item[0] 
              if verbose: print "[INFO] Account already exist, updated: ", data_account['code']
           else:   
              if verbose: print "[INFO] Account already exist, not updated (<", code_from, "): ", data_account['code']
       except:
           print "[ERR] modified", data_account['code']
    else: # CREATE
       try:
           account_id = sock.execute(dbname, uid, pwd, 'account.analytic.account', 'create', data_account) 
           if verbose: print "[INFO] Account create: ", data_account['code']
       except:
           #import pdb; pdb.set_trace()
           print "[ERR] modified", data_account['code']
    return True

# XMLRPC connection for autentication (UID) and proxy 
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/common', allow_none=True)
uid = sock.login(dbname ,user ,pwd)
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object', allow_none=True)

# Open CSV passed file (see arguments) mode: read / binary, delimiation char 
#lang_id=getLanguage(sock,dbname,uid,pwd,"Italian / Italiano")    # TODO check in country (for creation not for update)

for sheet_name, values in parse_xls(file_xls, 'cp1251'): # apro il file di excel
    old_row = -1
    data = {}
    header = ['ref','name','RESPONSABILE','partner_id','date','ATTIVA','CDC','note','GRUPPO','total_amount','DETERMINA','IMAGECONTRATTO','CONSIDERO','DA_ECLUDERE_RECUPERI','PERMESSI','FERIE','MALATTIA']
    #header = ['ref','name','RESPONSABILE','partner_id','date','attiva','CDC','note','total_amount','DETERMINA','IMAGECONTRATTO','DA_ECLUDERE_RECUPERI','TIPO_GIORNALIERA','ATTIVITA_PRED']
 
    for row_idx, col_idx in sorted(values.keys()):
        if not row_idx: continue # jump first header lines
        if old_row==-1: old_row = row_idx
        if row_idx != old_row: # su rottura di codice scrivo la riga
            create_contract(sock, dbname, uid, pwd, data)
            old_row=row_idx
            data={}
           
        v = values[(row_idx, col_idx)]
        if isinstance(v, unicode):
            riga = v.encode('cp866', 'backslashreplace')
        else:
            riga = str(v)
        data[header[col_idx]] = v

    if data:  # ultima scrittura
       create_contract(sock, dbname, uid, pwd, data)
