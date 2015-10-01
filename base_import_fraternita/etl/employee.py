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
file_xls=path_file + "ANAGRAFICA_DIP.xls"
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

code_from=192  # NOTE import ID access from >= code_from

# Start main code *************************************************************
def create_employee(sock, dbname, uid, pwd, data):
    ''' Creazione di un impiegato:
        1. Creazione res.partner
        2. Creazione res.partner.address per il partner (default)
        3. Creazione res.users
        4. Creazione hr.employee con link ai 3 dati precedenti
        TODO Department, responsabile, prodotto ecc.

        Campi di data:'ref', 
                      'settore', 
                      'stato', 
                      'cognome', 
                      'nome', 
                      'birth_date', 
                      'birth_place', 
                      'province_birth', 
                      'address', 
                      'number', 
                      'zip', 
                      'city', 
                      'phone_personal', 
                      'phone_cell',
                      'photo', 
                      'data_assunzione', 
                      'data_dimission', 
                      'mansione', 
                      'curricula', 
                      'patente', 
                      'orario_di_lavoro', 
                      'selezionato', 
                      'codice_fiscale', 
                      'tipo_contratto',
                      'data_fine_contratto'
    '''
    
    # res.partner: *************************************************************
    # Controlli precreazione:
    #lang_id=getItalian(sock, dbname, uid, pwd, "Italian / Italiano")
    if 'ref' not in data:
       print "[ERR] Riferimento non trovato!", data
       return False
       
    if data['ref'] < code_from:
       return True # not imported
       
    if 'cognome' not in data:
       print "[ERR] Cognome non trovato!", data
       return False

    if 'nome' not in data:
       print "[ERR] Nome non trovato!", data
       return False
    
    # campi generici calcolati per tutti
    name = "%s %s"%(data['cognome'].title(), data['nome'].title())
    address = 'address' in data and data['address']
    active = True if 'stato' in data and data['stato']!=0 else False

    if 'number' in data:
       address+=", " + data['number']
       
    data_partner={
                 'is_employee': True,
                 'import': True,
                 'customer': True,
                 'ref': int(data['ref']), # per togliere il .0 finale
                 'name': name,
                 'fiscal_id_code': data['codice_fiscale'] if 'codice_fiscale' in data else False,
                 }
    
    item = sock.execute(dbname, uid, pwd, 'res.partner', 'search', [('ref', '=', data_partner['ref']), ('import','=',True), ('is_employee','=', True)])
    partner_id = 0
    if item: # UPDATE:
       try:
           item_mod = sock.execute(dbname, uid, pwd, 'res.partner', 'write', item, data_partner) 
           partner_id=item[0] 
           if verbose: print "[INFO] Partner already exist: ", data_partner['ref'], data_partner['name']
       except:
           print "[ERR] modified", data_partner['ref'], data_partner['name']
    else: # CREATE
       try:
           partner_id = sock.execute(dbname, uid, pwd, 'res.partner', 'create', data_partner) 
           if verbose: print "[INFO] Partner create: ", data_partner['ref'], data_partner['name']
       except:
           print "[ERR] modified", data_partner['ref'], data_partner['name']
    
    if partner_id: # Creazione res.partner.address *****************************
        data_address={
             'city': 'city' in data and data['city'].title(), # modify first import address
             'zip': 'zip' in data and data['zip'], # modify first import address
             #'country_id': getCountryFromCode(sock,dbname,uid,pwd,country_international_code), 
             'phone': 'phone_personal' in data and data['phone_personal'],
             'mobile': 'phone_cell' in data and data['phone_cell'],
             #'fax': fax,
             'street': address, 
             #'email': 'email' in data and data['email'].lower(),
             'type': 'default',
             'import': True, # TODO non necessario (si potrebbe togliere)
             'partner_id': partner_id,
             }

        item_address = sock.execute(dbname, uid, pwd, 'res.partner.address', 'search', [('partner_id','=', partner_id),('type', '=', 'default'), ])  #('import','=',True) solo sul default
        address_id=0
        if item_address: # UPDATE:
           try:
               item_mod = sock.execute(dbname, uid, pwd, 'res.partner.address', 'write', item_address, data_address) 
               address_id=item_address[0]
               if verbose: print "[INFO] Address already exist: ", data_address
           except:
               print "[ERR] Modified address", data_address

        else:    # NEW
           try:
               address_id = sock.execute(dbname, uid, pwd, 'res.partner.address', 'create', data_address) 
               if verbose: print "[INFO] Address create: ", data_address
           except:
               print "[ERR] Address modified", data_address

           
        if address_id: # Creazione utente **************************************
            login=data['cognome'].lower() + data['nome'][:3].lower()
            login=login.replace(" ", "")
            data_user = {
                        'signature': name,
                        'name': name,
                        'menu_tips': False,
                        'login': login,
                        'email': 'email' in data and data['email'].lower(),
                        'password': '1234',
                        'address_id': address_id,
                        'context_lang': 'it_IT',
                        'view': 'extended',
                        #'user_email': ,
                        'active': active,
                       }

            item_user = sock.execute(dbname, uid, pwd, 'res.users', 'search', [('login','=', login)])
            user_id=0
            if item_user: # UPDATE:
               try:
                   item_mod = sock.execute(dbname, uid, pwd, 'res.users', 'write', item_user, data_user) 
                   user_id = item_user[0]
                   if verbose: print "[INFO] User already exist: ", data_user
               except:
                   print "[ERR] Modified user", data_user

            else: # NEW
               try:
                   user_id = sock.execute(dbname, uid, pwd, 'res.users', 'create', data_user) 
                   if verbose: print "[INFO] User created: ", data_user
               except:
                   print "[ERR] User modified", data_user
            
            if user_id: # Creazione dipentente *********************************  
                data_employee={
                     'active': active,
                     'code': data['ref'],
                     'address_id': False,
                     'address_home_id': address_id,
                     'name': name,
                     'department_id': crea_department(sock, dbname, uid, pwd, data['settore']) if 'settore' in data else False,
                     #'ssnid':,
                     'sinid': data['codice_fiscale'] if 'codice_fiscale' in data else False,
                     #'passport_id':,
                     #'identification_id':,
                     'mobile_phone': data['phone_cell'] if 'phone_cell' in data else False, # TODO doppione!!! lasciare in address
                     #'work_phone': 
                     #'work_location':,
                     #'work_email': ,
                     'birthday': prepare_date_xls(data['birth_date']) if 'birth_date' in data else False,
                     'birth_place': "%s %s"%(data['birth_place'] if 'birth_place' in data else "", "(" + data['province_birth'] + ")" if 'province_birth' in data else ""),
                     #'gender':,
                     #'state':,
                     #'notes':,
                     'user_id': user_id,

                     'date_recruitment': prepare_date_gg_mm_aaaa(data['data_assunzione']) if 'data_assunzione' in data else False,            
                     'date_retired': prepare_date_xls(data['data_dimission']) if 'data_dimission' in data else False,     
                     'curricula': data['curricula'] if 'curricula' in data else False,
                     'patent_type':data['patente'] if 'patente' in data else False,
                     # mansione               
                     # orario di lavoro
                     # tipo contratto 
                     'date_end_contract': prepare_date_gg_mm_aaaa(data['data_fine_contratto']) if 'data_fine_contratto' in data else False,
                     }
                                          
                item_employee = sock.execute(dbname, uid, pwd, 'hr.employee', 'search', [('code','=', data_employee['code'])])  #('import','=',True) solo sul default
                employee_id=0
                if item_employee: # UPDATE:
                   try:
                       item_mod = sock.execute(dbname, uid, pwd, 'hr.employee', 'write', item_employee, data_employee) 
                       employee_id=item_employee[0]
                       if verbose: print "[INFO] Employee already exist: ", data_employee
                   except:
                       print "[ERR] modified employee", data_employee

                else:   
                   try:
                       employee_id = sock.execute(dbname, uid, pwd, 'hr.employee', 'create', data_employee) 
                       if verbose: print "[INFO] Employee create: ", data_employee
                   except:
                       print "[ERR] employee modified", data_employee
        print " "           
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
    header = ['ref', 'settore', 'stato', 'cognome', 'nome', 'birth_date', 'birth_place', 'province_birth', 'address', 'number', 
              'zip', 'city', 'phone_personal', 'phone_cell','photo', 'data_assunzione', 'data_dimission', 'mansione', 'curricula', 
              'patente', 'orario_di_lavoro', 'selezionato', 'codice_fiscale', 'tipo_contratto', 'data_fine_contratto']

    for row_idx, col_idx in sorted(values.keys()):
        if not row_idx: continue # jump first header lines
        if old_row==-1: old_row = row_idx
        if row_idx != old_row: # su rottura di codice scrivo la riga
            create_employee(sock, dbname, uid, pwd, data)
            old_row=row_idx
            data={}
           
        v = values[(row_idx, col_idx)]
        if isinstance(v, unicode):
            riga = v.encode('cp866', 'backslashreplace')
        else:
            riga = str(v)
        data[header[col_idx]] = v

    if data:  # ultima scrittura
       create_employee(sock, dbname, uid, pwd, data)

