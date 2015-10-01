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

        # --------
        # Utility:
        # --------
        def prepare(value):  
            #value = value.decode('cp1252')
            #value = value.encode('utf-8')
            return value.strip()
            
        def prepare_date_ISO(value):
            ''' Calcolo data (formato 1900/01/01)
            ''' 
            value = value.strip()
            if value and len(value) == 8:
               return '%s-%s-%s' % (value[:4], value[4:6], value[-2:])
            return False   

        def prepare_float(value):
            if value:
                try:
                   value = value.strip().replace(",", ".")
                   return float(value)
                except:
                    pass
            return 0.0

        # ----------------------------
        # Start initializing elements:
        # ----------------------------
        _logger.info(_('Start import invoice elements'))
        log_list = []
        log_error = []
        
        # Pools:
        account_pool = self.pool.get('account.account')
        journal_pool = self.pool.get('account.analytic.journal')
        contract_pool = self.pool.get('account.analytic.account')
        line_pool = self.pool.get('account.analytic.line')

        # Search element for analytic line:
        general_account_ids = account_pool.search(cr, uid, [
            ('code', '=', general_code)], context=context)
        if not general_account_ids:
            log_error.append('Account code not found, code: %s' % general_code)
            _logger.error(log_error[-1])
            return False

        journal_ids = journal_pool.search(cr, uid, [
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
        import pdb; pdb.set_trace()
        for csv_file in invoice_file:
            _logger.info(_('Import invoice file: %s') % csv_file)
            lines = csv.reader(
                open(join(path, csv_file), 'rb'), delimiter=delimiter)

            # Reset element for import:
            cols = 0
            i = -header
            for line in lines:
                i += 1
                if not cols:
                    cols = len(line)
                    _logger.info(_('Total column found: %s') % cols)

                if i <= 0:  # jump n lines of header
                    continue

                if not(len(line) and cols == len(line)): 
                       log_error.append(_(
                           '%s: Empty row or cols different!') % i)
                       _logger.error(log_error[-1])
                       continue
                    
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
                
                if document in ('FT', 'NF'):
                    operator = +1
                elif document in ('NC', 'FF'):
                    operator = -1
                else:
                    log_error.append(_(
                        'Document type not found: %s') % operator)
                    _logger.error(log_error[-1])
                    continue
 
                if item_description: # if analytic row there's description
                    import_type = "L"    # L for single (L)ine
                    amount = amount_row * operator
                    ref_id = ref_line
                else:    
                    import_type = "I"    # I for all (I)nvoice
                    amount = amount * operator
                    ref_id = ref
                
                if not amount: # TODO amount for line??
                    log_error.append(_(
                        'No amount: %s %s contract %s amount %s') % (
                            ref, ref_line, contract, amount))
                    _logger.error(log_error[-1])        
                    continue # jump line
 
                # TODO vedere se è il caso di mettere il totale elementi o 
                # tenere 1 come per fattura
                unit_amount = 1.0 
 
                period = period or data # Invoice date if not present
 
                # Get analytic account:
                account_ids = contract_pool.search(cr, uid, [
                    ('code', '=', contract)], context=context)
                    
                if not account_ids: 
                    log_error.append(_(
                        'Analytic account not found: %s') % contract)
                    _logger.error(log_error[-1])
                    continue
                elif len(account_ids) > 1:
                    log_error.append(_(
                        'More analytic account found: %s') % contract)
                    _logger.error(log_error[-1])
                    continue
                   
                data = {
                    'name': "%s %s" % (contract, ref_id),
                    'import_type': import_type,
                    'general_account_id': general_account_ids[0],
                    'journal_id': journal_ids[0],
                    'amount': amount,
                    'unit_amount': unit_amount,
                    'date': period,
                    'ref': ref_id,
                    'account_id': account_ids[0],
                    'user_id': uid,
                    #'code': False,
                    #'product_uom_id': False,
                    #'company_id': 1,
                    #'currency_id': False,
                    #'to_invoice': 1,
                    #'product_id': False,
                    #'invoice_id': False,
                    #'extra_analytic_line_timesheet_id': False,
                    #'amount_currency': 0.0,
                    #'move_id': False,
                    }
 
                # I: ref=FT-2-12345 
                # L: ref=FT-2-12345-1
                line_ids = line.pool.search(cr, uid, [
                    ('ref', '=', ref_id),
                    ('import_type', '=', import_type)
                    ], context=context) 
 
                if line_ids: # Update:
                    try:
                        line_pool.write(cr, uid, line_ids, data, 
                            context=context) 
                        log_list.append(_(
                            'Update %s contract %s amount %s') % (
                                ref_id, contract, amount))
                        if verbose:
                            _logger.info(log_list[-1])                                      
                    except:
                        log_error.append(_(
                            'Error modify: %s, contract %s, amount %s') % (
                                ref_id, contract, amount))
                        _logger.error(log_error[-1])                                
                else: # Create
                    try:
                        line_pool.craete(cr, uid, data, context=context) 
                        log_list.append(_(
                            'Create %s contract %s amount %s') % (
                                ref_id, contract, amount))
                        if verbose:
                            _logger.info(log_list[-1])                                     
                    except:
                        log_error.append(_(
                            'Error create: %s, contract %s, amount %s') % (
                                ref_id, contract, amount))
                        _logger.error(log_error[-1])                                  
        _logger.info(_('End import invoice elements'))                           
        return True
account_analytic_account()        
