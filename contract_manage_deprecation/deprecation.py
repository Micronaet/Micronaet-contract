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
import csv
import decimal_precision as dp
from os import listdir
from osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from tools.translate import _
from tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    )

_logger = logging.getLogger(__name__)

class account_analytic_expense_deprecation(osv.osv):
    ''' Add schedule method and override split method
    '''
    _name = 'account.analytic.expense.deprecation'
    _description = 'Monthly deprecation split'
    _rec_name = 'account_id'
    _order = 'period'

    # -------------------------------------------------------------------------
    #                          XMLRPC function
    # -------------------------------------------------------------------------
    def schedule_csv_accounting_transport_movement_import(
            self, cr, uid, path='~/etl/deprecation', separator=';', header=0, 
            force=False, general_code='410100', context=None):
        ''' Import function that read in:
            path: folder where all transport Km file are
            separator: csv file format have this column separator
            header: and total line header passed
            force: delete previous elements
            general_code: general account code for create analytic line
            context: context for this function
            
            Note: file period are coded in filename
        '''
        from os.path import isfile, join

        # pools used:
        csv_pool = self.pool.get('csv.base')
        account_pool = self.pool.get('account.account')
        contract_pool = self.pool.get('account.analytic.account')
        line_pool = self.pool.get('account.analytic.line')
        journal_pool = self.pool.get('account.analytic.journal')

        # Read parameters for write analytic enytry:
        # Purchase journal:
        journal_id = journal_pool.get_journal_purchase(
            cr, uid, context=context)

        # Code for entry (ledger) operation:
        general_id = account_pool.get_account_id(
            cr, uid, general_code, context=context)
        if not general_id:
            _logger.error(_('Cannot create analytic line, no ledge!'))
            return False

        # Get file list:
        path = os.path.expanduser(path)
        trans_file = [
            filename for filename in listdir(path) if
                isfile(join(path, filename)) and filename[-3:] == 'csv']

        if not trans_file:
            _logger.warning(
                _('File not found in transport folder: %s') % path)
            return True

        trans_file.sort() # for have last price correct
        
        # Load previous importation:
        previous_db = {}
        previous_ids = self.search(cr, uid, [], context=context)
        for previous in self.browse(cr, uid, previous_ids, context=context):
            previous_db[previous.period] = previous.id
        
        _logger.info('Start auto import of file deprecation')        
        error = [] # from here log error              
        for filename in trans_file:
            try:
                _logger.info('Load and import file %s' % filename)
                period_to_update = {}
                year = filename.split('.')[0]
                if len(year) != 4 or not year.isdigit():    
                    error.append(
                        _('%s. Filename syntax error YYYY.csv: %s ') % (
                            filename))
                    _logger.error(error[-1])
                    continue
                
                # Check which month are present:
                for month in range(1, datetime.now().month) # all previous month
                    key = '%s-%02d' % (year, month)
                    if key not in previous_db: # create month if not present
                        period_to_update[key] = previous_db[key] # save ID
                
                # Delete previous log (and all analytic lines under
                self.unlink(
                    cr, uid, period_to_update.values(), context=context)

                # Create DB for department with year costs:
                costs = {} # for department
                
                i = -header
                fullpath = join(path, filename)
                f = open(fullpath, 'rb')
                #TODO period_to_update
                for line in f:
                    i += 1
                    if i <= 0: # jump header line
                        continue
                    line = line.strip().split(separator)

                    # Parse columns: 
                    if len(line) != 2:
                        error.append(_('%s. Cols != 2') % i)
                        _logger.error(error[-1])
                        continue

                    code = csv_pool.decode_string(line[0]) # department:
                    amount = csv_pool.decode_float(line[1])

                    if not code:
                        error.append(_('%s. Contract code empty') % i)
                        _logger.error(error[-1])
                        continue
                f.close()
                
                for month in 
                # Create lof element:
                parent_id = self.create(cr, uid, {
                    'name': _('Import file: %s') % filename,
                    'period': '',# TODO
                    }, context=context)                    

                        
                # Search contract
                contract_ids = contract_pool.search(cr, uid, [
                    ('code', '=', code)], context=context)

                if not contract_ids:
                    error.append(
                        _('%s. Contract not found on OpenERP: %s') % (
                            i, code))
                    _logger.error(error[-1])
                    continue
            
                elif len(contract_ids) > 1:
                    error.append(
                        _('%s. More than one contract found (%s): %s') % (
                            i, len(contract_ids), code))
                    _logger.error(error[-1])
                    continue
                
                line_pool.create(cr, uid, {
                    'amount': -amount,
                    'user_id': uid,
                    'name': _('Import: %s') % filename,
                    'unit_amount': 1.0,
                    'account_id': contract_ids[0],
                    'general_account_id': general_id,
                    'journal_id': journal_id, 
                    'date': period_date,

                    # Link to import record:
                    'km_import_id': parent_id,
                    'csv_filename': filename, # key for deletion

                    # Not used:
                    #'company_id', 'code', 'currency_id', 'move_id',
                    #'product_id', 'product_uom_id', 'amount_currency',
                    #'ref', 'to_invoice', 'invoice_id', 
                    # 'extra_analytic_line_timesheet_id', 'import_type',
                    ##'activity_id', 'mail_raccomanded', 'location',
                    }, context=context)
                
                # History file:
                os.rename(
                    os.path.join(path, filename),
                    os.path.join(path, 'history', '%s.%s' % (
                        datetime.now().strftime('%Y%m%d.%H%M%S'),
                        filename, )),
                    )
                    
                # TODO write error in file
                if error:
                    self.write(cr, uid, parent_id, {
                        'error': '\n'.join(error)}, context=context)
            except:
                _logger.error('No correct file format: %s' % filename)
                error.append('%s' % ((sys.exc_info(), )))
                _logger.error(error[-1])
                
        _logger.info('End auto import of file transport')
        return True

    _columns = {
        'name': fields.char('Import', size=120, required=True), 
        'period': fields.char('YYYY-MM', size=6, required=True), 
        'datetime': fields.date('Import date'),
        'error': fields.text('Error'),
         }
    
    _defaults = {
        'datetime': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
        }     
account_analytic_expense_deprecation()

class account_analytic_line(osv.osv):
    ''' Extra fields for analytic line
    '''
    _inherit = 'account.analytic.line'
    
    _columns = {
        'deprecation_import_id': fields.many2one(
            'account.analytic.expense.deprecation', 'Import deprecation', 
            ondelete='cascade'),
        }
account_analytic_line()

class account_analytic_expense_deprecation(osv.osv):
    ''' Add schedule method and override split method
    '''
    _inherit = 'account.analytic.expense.deprecation'

    _columns = {
        'line_ids': fields.one2many(
            'account.analytic.line', 'deprecation_import_id', 'Analytic line'),
        }

account_analytic_expense_deprecation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
