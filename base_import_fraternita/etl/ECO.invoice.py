#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Modules required:
# from pyExcelerator import *
import xmlrpclib, csv, sys, time, string, ConfigParser, os, pdb
from parse_function import *

# Parameters:
path_file=os.path.expanduser("~/ETL/ecologia/")
cfg_file=path_file + "openerp.cfg"
header_lines = 0 # riga di intestazione

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
# Functions:
def get_account_account(sock, dbname, uid, pwd, code):
    # get code of general account
    return sock.execute(dbname, uid, pwd, 'account.account', 'search', [('code', '=', code),])[0]

def get_account_analytic_journal(sock, dbname, uid, pwd, code):
    # get code of journal
    return sock.execute(dbname, uid, pwd, 'account.analytic.journal', 'search', [('code', '=', code),])[0]
    
# XMLRPC connection for autentication (UID) and proxy 
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/common', allow_none=True)
uid = sock.login(dbname ,user ,pwd)
sock = xmlrpclib.ServerProxy('http://' + server + ':' + port + '/xmlrpc/object', allow_none=True)


if len(sys.argv)!=2:
   print """
         *** Syntax Error! ***
         *  Use the command with this syntax: python ./invoice.py daticommoerp.SEE
         *********************
         """ 
   sys.exit()
   
lines = csv.reader(open(sys.argv[1],'rb'),delimiter=separator)
counter={'tot':-header_lines,'new':0,'upd':0,'err':0,'err_upd':0,'tot_add':0,'new_add':0,'upd_add':0,} # tot negative (jump N lines)

tot_colonne=0
fattura_precedente=""
esporta=False

general_account_id = get_account_account(sock, dbname, uid, pwd, "150100")  # TODO parametrize default account 
journal_id= get_account_analytic_journal(sock, dbname, uid, pwd, "SAL")       # TODO parametrize journal (code = S, name = Sales) # TODO ora S?
#try:

for line in lines:
    if counter['tot']<0:  # jump n lines of header 
       counter['tot']+=1
    else: 
       if not tot_colonne:
          tot_colonne=len(line)
          print "Colonne presenti: %d"%(tot_colonne)
       if len(line): # jump empty lines
           if tot_colonne == len(line): # tot colums equal to column first line                   
               counter['tot']+=1 
               print counter['tot'],") ",
               # campi rilevati dall'importazione CSV:
               csv_id=0
               sigla = prepare(line[csv_id]).upper()                # 1. FT 
               csv_id+=1
               numero = prepare(line[csv_id])                       # 2. numero fattura
               csv_id+=1
               data = prepare_date_ISO(line[csv_id])                # 3. data fattura
               csv_id+=1
               codice = prepare(line[csv_id]).upper()               # 4. codice articolo
               csv_id+=1
               descrizione = prepare(line[csv_id])                  # 5. descrizione articolo
               csv_id+=1
               quantita = prepare_float(line[csv_id])               # 6. quantità
               csv_id+=1
               importo_riga = prepare_float(line[csv_id])           # 7. importo totale riga
               csv_id+=1
               importo = prepare_float(line[csv_id])                # 8. importo totale fattura
               csv_id+=1
               commessa_testata = prepare(line[csv_id])             # 9. commessa per la fattura (tutta)
               csv_id+=1
               data_periodo = prepare_date_ISO(line[csv_id])        # 10. fine periodo di validità, es.: 20120331
               csv_id+=1
               numero_riga = prepare(line[csv_id])                  # 11. numero riga all'interno della fattura (per l'ID)
               csv_id+=1
               vid_agg_1 = prepare(line[csv_id])                    # 12. riga: anno commessa, es.: 2012
               csv_id+=1
               vid_agg_2 = prepare(line[csv_id])                    # 13. riga: numero. es.: 097
               csv_id+=1
               vid_agg_3 = prepare(line[csv_id])                    # 14. riga: giorno / mese, es.: 23/12
               csv_id+=1 
               vid_agg_4 = prepare(line[csv_id])                    # 15. riga: anno, es.: 2011

               # campi calcolati:
               if not data[:4]:
                   print "ERR data non presente, riga: %s"%(counter['tot'])
                   continue
               ref = "%s-%s-(%s)"%(sigla,numero,data[:4])                           # ID fattura
               ref_line = "%s-R%s"%(ref,numero_riga)      # ID riga
               
               if sigla in ("FT","NF"):
                  segno = +1
               elif sigla in ("NC", "FF"):
                  segno = -1
               else:
                  print "[ERR] Sigla documento non trovata:", sigla

               if descrizione: # if line to analytic account so there's the description
                   import_type = "L"    # L for single (L)ine
                   amount = importo_riga * segno
                   ref_id = ref_line
               else:    
                   import_type = "I"    # I for all (I)nvoice
                   amount = importo * segno
                   ref_id = ref
               
               if not amount: # TODO per le linee come viene messo l'importo?***********************************************************
                   if verbose: print "[WARN] Amount not present:", ref, ref_line, "su commessa", commessa_testata, "importo:", amount
                   continue # jump line

               unit_amount = 1.0 # TODO vedere se è il caso di mettere il totale elementi o tenere 1 come per fattura

               data_periodo = data_periodo or data    # prendo la data fattura se non è indicata
               
               #if not fattura_precedente or fattura_precedente != ref: # prima fattura o diversa dalla precedente
               #   esporta = True
               #   fattura_precedente = ref
               #else:
               #   esporta = False 

               #if esporta: # salto le righe da non esportare:

               # Ricerca conto analitico:
               # TODO IMPORTANTE: vedere poi per le sottovoci come comporsi: eventualmente commessa + numero sottovoce
               account_ids = sock.execute(dbname, uid, pwd, 'account.analytic.account', 'search', [('code', '=', commessa_testata),]) # TODO tolto ('parent_id','=',False)
               
               if not account_ids: 
                   print "[ERR] Conto analitico non trovato:", commessa_testata 
               else: # TODO segnalare errore se len(account_ids) è >1
                   # Creazione voce giornale analitico
                   line_id = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'search', [('ref', '=', ref_id),('import_type', '=', import_type)])   # for I: ref=FT-2-12345 for L: ref=FT-2-12345-1
                   
                   data_account = {
                                 'name': "%s %s"%(commessa_testata, ref_id) ,#'2010001 FERIE',
                                 'import_type': import_type,
                                 #'code': False,
                                 #'user_id': [419, 'Moletta Giovanni'],
                                 'general_account_id': general_account_id, #[146, '410100 merci c/acquisti '],
                                 #'product_uom_id': False,
                                 #'company_id': [1, u'Franternit\xe0 Servizi'],
                                 'journal_id': journal_id, #[2, 'Timesheet Journal'],
                                 #'currency_id': False,
                                 #'to_invoice': [1, 'Yes (100%)'],
                                 'amount': amount,
                                 #'product_id': False,
                                 'unit_amount': unit_amount, #10.5,
                                 #'invoice_id': False,
                                 'date': data_periodo, #'2012-07-09',
                                 #'extra_analytic_line_timesheet_id': False,
                                 #'amount_currency': 0.0,
                                 'ref': ref_id,   # TODO or ref_line
                                 #'move_id': False,
                                 'account_id': account_ids[0], #[257, '2010001 FERIE']
                             }

                   if line_id: # UPDATE:
                       try:
                           item_mod = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'write', line_id, data_account) 
                           if verbose: print "[INFO] Account already exist, updated:", ref_id, "su commessa", commessa_testata, "importo:", amount
                       except:
                           print "[ERR] modified", ref_id, "su commessa", commessa_testata, "importo:", amount
                   else: # CREATE
                      try:
                          create_id = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'create', data_account) 
                          if verbose: print "[INFO] Account create: ", ref_id, "su commessa", commessa_testata, "importo:", amount
                      except:
                          print "[ERR] modified", ref_id, "su commessa", commessa_testata, "importo:", amount
#except:
#   print "[ERR] General error importing"
