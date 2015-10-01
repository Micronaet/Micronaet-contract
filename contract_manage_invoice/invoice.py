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
from os import listdir
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
            file_filter='daticommoerp.SEE', header=0, delimiter=';', 
            general_code='150100', journal_code='SAL',
            verbose=True, context=None):
        ''' Import CSV file for invoice (year based)
            path: folder for get file list 
            file_filter: string that MUST be in the file format
            header: number of header line
            delimiter: column separator
            general_code: code used for account ledger in analytic line
            journal: journal code used for analytic line
            verbose: write log operation in openerp
            context: context
        '''
        from os.path import isfile, join
        # Start initializing elements:
        log_list = []
        log_error = []
        
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
        
        # Read file in folder:
        path = os.path.expanduser(path)
        invoice_file = [
            filename for filename in listdir(path) if 
                    isfile(join(path, filename)) and file_filter in filename]

        invoice_file.sort() # for have last price correct
        for csv_file in invoice_file:
            lines = csv.reader(
                open(csv_file, 'rb'), delimiter=delimiter)

            # Reset element for import:
            cols = 0
            fattura_precedente = ''
            i = -header
            for line in lines:
                i += 1
                if not cols:
                    cols = len(line)
                    _logger.info(_('Total column found: %s') % cols)

                if i <= 0:  # jump n lines of header
                    continue

                if len(line) and cols == len(line): 
                   document = prepare(line[0]).upper() # Type, ex.: FT 
                   number = prepare(line[1]) # Number of invoice
                   date = prepare_date_ISO(line[2]) # Invoice date
                   item_code = prepare(line[3]).upper() # Code item
                   item_description = prepare(line[4]) # Description item
                   quantity = prepare_float(line[5]) # Quantity
                   amount_row = prepare_float(line[6]) # Total line
                   amount = prepare_float(line[7]) # Total invoice
                   contract = prepare(line[8]) # Header: contract
                   period = prepare_date_ISO(line[9]) # End val. 20120331
                   sequence = prepare(line[10]) # Num. row in invoice
                   addendum1 = prepare(line[11]) # Row: contract year ex. 2012
                   addendum2 = prepare(line[12]) # Row: Number ex.: 097
                   addendum3 = prepare(line[13]) # Row: day/month ex.: 23/12
                   addendum4 = prepare(line[14]) # Row: year ex. 2011
                   series = prepare(line[15]) # Series ex. 2

                   # Computed
                   if not date[:4]:
                       log_error.append(_('Date not present, row: %s') % i)
                       _logger.error(log_error[-1])
                       continue
                       
                   # Key ref:
                   ref = "%s/%s-%s-(%s)" % (document, series, number, date[:4])                   
                   ref_line = "%s-R%s" % (ref, sequence) # row
                   
                   if document in ("FT","NF"):
                      segno = +1
                   elif document in ("NC", "FF"):
                      segno = -1
                   else:
                      error = "[ERR] Sigla documento non trovata:", sigla
                      print error
                      file_log.write("%s"%(error,))

                   if item_description: # if line to analytic account so there's the description
                       import_type = "L"    # L for single (L)ine
                       amount = amount_row * segno
                       ref_id = ref_line
                   else:    
                       import_type = "I"    # I for all (I)nvoice
                       amount = amount * segno
                       ref_id = ref
                   
                   if not amount: # TODO per le linee come viene messo l'importo?***********************************************************
                       error = "[WARN] Amount not present:", ref, ref_line, "su commessa", contract, "importo:", amount
                       if verbose: print error
                       file_log.write("%s"%(error,))
       
                       continue # jump line

                   unit_amount = 1.0 # TODO vedere se è il caso di mettere il totale elementi o tenere 1 come per fattura

                   period = period or data    # prendo la data fattura se non è indicata
                   

                   # Ricerca conto analitico:
                   # TODO IMPORTANTE: vedere poi per le sottovoci come comporsi: eventualmente commessa + numero sottovoce
                   account_ids = sock.execute(dbname, uid, pwd, 'account.analytic.account', 'search', [('code', '=', contract),]) # TODO tolto ('parent_id','=',False)
                   
                   if not account_ids: 
                       error = "[ERR] Conto analitico non trovato:", contract 
                       print error
                       file_log.write("%s"%(error,))

                   else: # TODO segnalare errore se len(account_ids) è >1
                       # Creazione voce giornale analitico
                       line_id = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'search', [('ref', '=', ref_id),('import_type', '=', import_type)])   # for I: ref=FT-2-12345 for L: ref=FT-2-12345-1
                       
                       data_account = {
                                     'name': "%s %s"%(contract, ref_id) ,#'2010001 FERIE',
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
                                     'date': period, #'2012-07-09',
                                     #'extra_analytic_line_timesheet_id': False,
                                     #'amount_currency': 0.0,
                                     'ref': ref_id,   # TODO or ref_line
                                     #'move_id': False,
                                     'account_id': account_ids[0], #[257, '2010001 FERIE']
                                 }

                       if line_id: # UPDATE:
                           try:
                               item_mod = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'write', line_id, data_account) 
                               if verbose: print "[INFO] Account already exist, updated:", ref_id, "su commessa", contract, "importo:", amount
                           except:
                               error = "[ERR] modified", ref_id, "su commessa", contract, "importo:", amount
                               print error
                               file_log.write("%s"%(error,))
                       else: # CREATE
                          try:
                              create_id = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'create', data_account) 
                              if verbose: print "[INFO] Account create: ", ref_id, "su commessa", contract, "importo:", amount
                          except:
                              error = "[ERR] modified", ref_id, "su commessa", contract, "importo:", amount
                              print error
                              file_log.write("%s"%(error,))



