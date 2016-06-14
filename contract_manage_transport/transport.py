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

class account_analytic_expense_km(osv.osv):
    ''' Add schedule method and override split method
    '''
    _name = 'account.analytic.expense.km'
    _description = 'Monthly transport km'
    _rec_name = 'account_id'
    _order = 'month'

    # -------------------------------------------------------------------------
    #                          XMLRPC function
    # -------------------------------------------------------------------------
    def schedule_csv_accounting_transport_movement_import(
            self, cr, uid, path='~/etl/transport', separator=';', header=0, 
            general_code='410100', context=None):
        ''' Import function that read in:
            path: folder where all transport Km file are
            separator: csv file format have this column separator
            header: and total line header passed
            general_code: general account code
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
        _logger.info('Start auto import of file expences')
        for filename in trans_file:
            try:            
                _logger.info('Load and import file %s' % filename)
                error = [] # from here log error              
                
                # ----------------------------------
                # Remove previous import if present:
                # ----------------------------------
                unlink_ids = line_pool.search(cr, uid, [
                    ('csv_filename', '=', filename),
                    ], context=context)
                if unlink_ids:
                    line_pool.unlink(cr, uid, unlink_ids, context=context)
                    _logger.info(
                        'Removed previous costs: %s (file: %s)' % (
                            len(unlink_ids),
                            filename,
                            ))
                
                # ------------------------------
                # Get data period from filename:
                # ------------------------------                
                # Format file: COST|YY|MM|.|csv
                period = filename[-8:-4]
                if not period.isdigit():    
                    error.append(
                        _('%s. Filename syntax error COSTYYMM.csv: %s') % (
                            filename))
                    _logger.error(error[-1])
                    continue

                period_date = '20%s-%s-01' % (
                    period[:2],
                    period[2:],
                    )
                    
                i = -header
                fullpath = join(path, filename)
                f = open(fullpath, 'rb')

                parent_id = self.create(cr, uid, {
                    'name': _('Import file: %s') % filename,
                    }, context=context)                    
                for line in f:
                    i += 1
                    if i <= 0: # jump header line
                        continue
                    line = line.strip().split(separator)

                    # Parse columns: 
                    if len(line) < 2:
                        error.append(_('%s. Cols < 2') % i)
                        _logger.error(error[-1])
                        continue
                        
                    code = csv_pool.decode_string(line[0])
                    amount = csv_pool.decode_float(line[1])
                    
                    if not code:
                        error.append(_('%s. Contract code empty') % i)
                        _logger.error(error[-1])
                            
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
                        'import_filename': filename, # key for deletion

                        # Not used:
                        #'company_id', 'code', 'currency_id', 'move_id',
                        #'product_id', 'product_uom_id', 'amount_currency',
                        #'ref', 'to_invoice', 'invoice_id', 
                        # 'extra_analytic_line_timesheet_id', 'import_type',
                        ##'activity_id', 'mail_raccomanded', 'location',
                        }, context=context)
                f.close()
                
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

    # XXX OLD PROCEDURE FOR IMPORT MOVEMENT FILES NOW REPLATED WITH 
    # FILENAME WITH PERIOD CODED
    """    
    def schedule_csv_accounting_transport_movement_import(
            self, cr, uid, path='~/etl/transport', separator=';', header=0, 
            general_code='410100', from_month=9, context=None):
        ''' Import function that read in:
            path: folder where all transport Km file are
            separator: csv file format have this column separator
            header: and total line header passed
            general_code: general account code
            from_month: number of colum for import extra discount
            context: context for this function
        '''
        from os.path import isfile, join

        # pools used:
        csv_pool = self.pool.get('csv.base')
        account_pool = self.pool.get('account.account')
        contract_pool = self.pool.get('account.analytic.account')
        line_pool = self.pool.get('account.analytic.line')
        journal_pool = self.pool.get('account.analytic.journal')

        # Read paramters for write analytic enytry:
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
            _logger.warning(_('File not found in transport folder: %s') % path)
            return True

        trans_file.sort() # for have last price correct
        _logger.info("Start auto import of file transport")            
        for filename in trans_file:
            try:            
                _logger.info("Load and import file %s" % filename)
                error = []
                
                i = -header
                fullpath = join(path, filename)
                f = open(fullpath, 'rb')

                parent_id = self.create(cr, uid, {
                    'name': _('Import file: %s') % filename,
                    }, context=context)
                for line in f:
                    i += 1
                    if i <= 0: # jump header line
                        continue
                    line = line.strip().split(separator)

                    code = csv_pool.decode_string(line[0])
                    # Search contract
                    contract_ids = contract_pool.search(cr, uid, [
                        ('code', '=', code)], context=context)

                    if not contract_ids:
                        _logger.error(
                            _('%s. Code not found on OpenERP: %s') % (i, code))
                        continue
                
                    elif len(contract_ids) > 1:
                        _logger.error(
                            _('%s. More than one code found (%s): %s') % (
                                i, len(contract_ids), code))
                        continue
                    
                    for i in range(from_month, len(line)):
                        amount = csv_pool.decode_float(line[i])
                        
                        line_pool.create(cr, uid, {
                            'amount': -amount,
                            'user_id': uid,
                            'name': _('Import: %s') % filename, # TODO
                            'unit_amount': 1.0,
                            'account_id': contract_ids[0],
                            'general_account_id': general_id,
                            'journal_id': journal_id, 
                            'date': '2015-%02d-01' % i, # TODO

                            # Link to import record:
                            'km_import_id': parent_id,

                            # Not used:
                            #'company_id', 'code', 'currency_id', 'move_id',
                            #'product_id', 'product_uom_id', 'amount_currency',
                            #'ref', 'to_invoice', 'invoice_id', 
                            # 'extra_analytic_line_timesheet_id', 'import_type',
                            ##'activity_id', 'mail_raccomanded', 'location',
                            }, context=context)
                f.close()
                
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
                _logger.error((sys.exc_info(), ))
                
        _logger.info("End auto import of file transport")
        return True"""

    _columns = {
        'name': fields.char('Import', size=120, required=True), 
        'datetime': fields.date('Import date'),
        'error': fields.text('Error'), 
         }
    
    _defaults = {
        'datetime': lambda *x: datetime.now().strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
        }     
account_analytic_expense_km()    

class account_analytic_line(osv.osv):
    ''' Extra fields for analytic line
    '''
    _inherit = 'account.analytic.line'
    
    _columns = {
        'km_import_id': fields.many2one(
            'account.analytic.expense.km', 'Import Km', ondelete='cascade'),
        'csv_filename': fields.char('CSV filename', size=80),     
        }
account_analytic_line()

class account_analytic_expense_km(osv.osv):
    ''' Add schedule method and override split method
    '''
    _inherit = 'account.analytic.expense.km'

    _columns = {
        'line_ids': fields.one2many(
            'account.analytic.line', 'km_import_id', 'Analytic line'),
        }

account_analytic_expense_km()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
