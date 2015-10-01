# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import logging
import netsvc
import xmlrpclib
import csv
import decimal_precision as dp
from osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from tools.translate import _
from tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    )
# TODO remove:
from parse_function import *

_logger = logging.getLogger(__name__)

class account_analytic_account(osv.osv):
    ''' Add schedule procedure for import invoice
    '''

    _inherit = 'account.analytic.line'
    
    # Schedule procedure:
    def schedule_import_invoice(self, cr, uid, path='~/ETL/servizi/', 
            file_filter='daticommoerp.SEE', header=0, separator=';', 
            general_code='150100', journal_code='SAL',
            verbose=True, context=None):
        ''' Import CSV file for invoice (year based)
            path: folder for get file list 
            file_filter: string that MUST be in the file format
            header: number of header line
            separator: column separator
            general_code: code used for account ledger in analytic line
            journal: journal code used for analytic line
            verbose: write log operation in openerp
            context: context
        '''
        # Start initializing elements:
        log_list = []
        log_error = []
        path_file = os.path.expanduser(path)
        
        # Pools:
        account_pool = self.pool.get('account.account')
        journal_pool = self.pool.get('account.analytic.journal')

        # Search element for analytic line:
        general_account_ids = account_pool.search(cr, uid, [
            ('code', '=', general_code)], context=context)
        if not general_account_ids:
            log_error.append('Account code not found, code: %s' % general_code)
            _logger.error(log_error[-1])
            return False

        journal_ids = account_pool.search(cr, uid, [
            ('code', '=', journal_code)], context=context)
        if not journal_ids:
            log_error.append('Journal not found, code: %s' % journal_code)
            _logger.error(log_error[-1])
            return False
            
           
        lines = csv.reader(open(sys.argv[1],'rb'),delimiter=separator)
        counter={'tot':-header_lines,'new':0,'upd':0,'err':0,'err_upd':0,'tot_add':0,'new_add':0,'upd_add':0,} # tot negative (jump N lines)

        tot_colonne = 0
        fattura_precedente = ''
        esporta = False


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
                           error = "ERRORE: data non presente, riga: %s"%(counter['tot'])
                           print error
                           file_log.write("%s"%(error,))
                           continue
                       ref = "%s-%s-(%s)"%(sigla,numero,data[:4])                           # ID fattura
                       ref_line = "%s-R%s"%(ref,numero_riga)      # ID riga
                       
                       if sigla in ("FT","NF"):
                          segno = +1
                       elif sigla in ("NC", "FF"):
                          segno = -1
                       else:
                          error = "[ERR] Sigla documento non trovata:", sigla
                          print error
                          file_log.write("%s"%(error,))

                       if descrizione: # if line to analytic account so there's the description
                           import_type = "L"    # L for single (L)ine
                           amount = importo_riga * segno
                           ref_id = ref_line
                       else:    
                           import_type = "I"    # I for all (I)nvoice
                           amount = importo * segno
                           ref_id = ref
                       
                       if not amount: # TODO per le linee come viene messo l'importo?***********************************************************
                           error = "[WARN] Amount not present:", ref, ref_line, "su commessa", commessa_testata, "importo:", amount
                           if verbose: print error
                           file_log.write("%s"%(error,))
           
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
                           error = "[ERR] Conto analitico non trovato:", commessa_testata 
                           print error
                           file_log.write("%s"%(error,))

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
                                   error = "[ERR] modified", ref_id, "su commessa", commessa_testata, "importo:", amount
                                   print error
                                   file_log.write("%s"%(error,))
                           else: # CREATE
                              try:
                                  create_id = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'create', data_account) 
                                  if verbose: print "[INFO] Account create: ", ref_id, "su commessa", commessa_testata, "importo:", amount
                              except:
                                  error = "[ERR] modified", ref_id, "su commessa", commessa_testata, "importo:", amount
                                  print error
                                  file_log.write("%s"%(error,))



