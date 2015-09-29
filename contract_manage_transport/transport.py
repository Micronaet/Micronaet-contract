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

    # -------------------------------------------------------------------------
    #                                 Scheduled
    # -------------------------------------------------------------------------
    def schedule_csv_accounting_transport_movement_import(
            self, cr, iud, path='~/etl/transport', separator=';', header=0, 
            verbose=100, bof='transport', context=None):
        ''' Import function that read in:
            path: folder where all transport Km file are
            separator: csv file format have this column separator
            header: and total line header passed
            verbose: every x record log event of importation
            bof: the input file must start with this string, after:
                YYMM.csv for get also the ref. month
            context: context for this function
        '''
        from os.path import isfile, join
        account_pool = self.pool.get('account.analytic.account')

        # --------------------------------
        # Utility: function for procedure:
        # --------------------------------
        def format_string(value, default=''):
            try:
                return value.strip() or default
            except:
                return default

        def format_date(value):
            return value

        def format_float(value):        
            try:
                value = value.replace(',', '.')
                return float(value)
            except:
                return 0.0
        
        path = os.path.expanduser(path)
        trans_file = [
            filename for filename in listdir(path) if 
                    isfile(join(path, filename)) and filename.startswith(bof) 
                    and len(filename) == (len(bof) + 8)]

        trans_file.sort() # for have last price correct
        _logger.info("Start auto import of file transport")
        for filename in trans_file:        
            try:
                _logger.info("Load and import file %s" % filename)
                error = []
                year_month = os.path.splitext(filename)[0][-4:]
                
                # --------------------------------
                # Remove all line for that period:
                # --------------------------------
                item_ids = self.search(cr, uid, [
                    ('month', '=', year_month),
                    ], context=context)
                self.unlink(cr, uid, item_ids, context=context)
                
                # ---------------
                # Load from file:
                # ---------------
                i = -header
                f = open(filename, 'rb')
                for line in f:
                    i += 1
                    if i <= 0: # jump header line
                        continue

                    line = line.strip().split(separator)
                    
                    # Parse file:                    
                    code = format_string(line[0])
                    km = format_float(line[1])
                    
                    # Check contract:
                    if not code or not km:
                        _logger.warning(_('%s. Code or Km not found') % i)
                        continue
                    
                    account_ids = account_pool.search(cr, uid, [
                        ('code', '=', code)], context=context)

                    if not account_ids:
                        _logger.error(
                            _('%s. Code not found on OpenERP: %s') % (i, code))
                        continue
                    elif len(account_ids) > 1:
                        _logger.error(
                            _('%s. More than one code found (%s): %s') % (
                                i, len(account_ids), code))
                        continue                    
                f.close()
                
                # History file:
                os.rename(
                    os.path.join(path, filename),
                    os.path.join(path, 'history', '%s.%s' % (
                        datetime.now().strftime('%Y%m%d.%H%M%S'),
                        filename, )),
                    )

            except:
                _logger.error('No correct file format: %s' % filename)
                _logger.error((sys.exc_info(), ))
        _logger.info("End auto import of file transport")
        return True
    
    _columns = {
         'account_id': fields.many2one('account.analytic.account', 'Account',
             required=True),
         'km': fields.float('Km', digits=(16, 2),
             required=True), 
         'month': fields.char('Month', size=4, help='Format YYMM',
             required=True), 
         }    
account_analytic_expense_km()    

class account_analytic_expense(osv.osv):
    ''' Add schedule method and override split method
    '''
    _name = 'account.analytic.expense'
    _inherit = 'account.analytic.expense'

    # Utility:
    def get_transport_splitted_account(self, cr, uid, context=None):
        ''' Function to be written, for now is overrided with module
            contract_manage_transport for temporary phase 
            Costs will be calculated depend on Km for every contract
        '''
        # TODO change all:
        data = {}

        intervent_pool = self.pool.get('hr.analytic.timesheet')
        employee_pool = self.pool.get('hr.employee')
        account_pool = self.pool.get('account.analytic.account')
        
        if not department_id: # TODO all? 
            _logger.error(
                _('Cannot split voucher if department is not present!'))

        # ------------------------------
        # List of user that has voucher:
        # ------------------------------
        employee_ids = employee_pool.search(cr, uid, [
            ('has_voucher', '=', True),
            # TODO Note: employee should work for other account, so no filter:
            #('department_id', '=', department_id), 
            ], context=context)
        voucher_user_ids = [
            item.user_id.id for item in employee_pool.browse(
                cr, uid, employee_ids, context=context) if item.user_id]
        if not voucher_user_ids: 
            _logger.error(
                _('Cannot find active user in dep. selected [%s:%s] (lim. %s)'
                ) % (date_from, date_to, limit, limit))
            return {}

        # ------------------------------
        # Account not cancel and :
        # ------------------------------
        # TODO check date for closing ?
        account_ids = account_pool.search(cr, uid, [
            ('department_id', '=', department_id),
            ('state', '!=', 'cancel'), # Active (or closed) # TODO necessary?
            ('not_working', '=', False), # Working account
            ('is_recover', '=', False), # Not recover account
            ('is_contract', '=', True), # Is contract
            ], context=context)
        if not account_ids: 
            _logger.error(
                _('Cannot find active account [%s:%s]') % (
                    date_from, date_to, limit))
            return {}

        # ------------------------------------------------------
        # List of intervent in period for user that has voucher:    
        # ------------------------------------------------------
        intervent_ids = intervent_pool.search(cr, uid, [
            ('date', '>=', date_from), 
            ('date', '<', date_to), 
            ('user_id', 'in', voucher_user_ids),       
            ('account_id', 'in', account_ids)     
            ])

        # -------------------------------------------------------------
        # Load database for populate limit elements and account + hours    
        # -------------------------------------------------------------
        for intervent in intervent_pool.browse(
                cr, uid, intervent_ids, context=context):
            key = (intervent.date, intervent.user_id.id)
            if key not in data:
                data[key] = [0, {}] # day hours, dict of ID int: hour
            
            data[key][0] += intervent.unit_amount # update duration
            if intervent.account_id in data[key][1]:
                data[key][1][intervent.account_id.id] += intervent.unit_amount
            else:    
                data[key][1][intervent.account_id.id] = intervent.unit_amount

        # -------------------------------------
        # Loop for clean database (test limit):
        # -------------------------------------
        res = {}        
        total = 0.0
        for item in data:
            if data[item][0] < limit:
                continue # jump, no dinner
            for account_id in data[item][1]:
                if account_id not in res:
                    res[account_id] = 0
                    
                res[account_id] += data[item][1][account_id] # total hours
                total += data[item][1][account_id]
        
        # -----------------------------------
        # Update with amount splitted (rate):
        # -----------------------------------
        if not total:
            _logger.error(_(
                'Total = 0 cannot split voucher amount: %s!') % amount)
            return {}
        rate = amount / total
        for item in res:
            res[item] *= rate
        # TODO keep line with amount 0?    
        return res
        return {}
account_analytic_expense()    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
