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
    #                                Scheduled
    # -------------------------------------------------------------------------
    def schedule_csv_accounting_transport_movement_import(
            self, cr, uid, path='~/etl/transport', separator=';', header=0, 
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
                fullpath = join(path, filename)
                f = open(fullpath, 'rb')
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
                    self.create(cr, uid, {
                        'account_id': account_ids[0],
                        'km': km,
                        'month': year_month,
                        }, context=context)                      
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
    def get_transport_splitted_account(self, cr, uid, amount=0, month=0, 
            context=None):
        ''' Function to be written, for now is overrided with module
            contract_manage_transport for temporary phase 
            Costs will be calculated depend on Km for every contract
        '''
        res = {}

        if not amount or not month:
            _logger.error(_('Amount or month equal to zero!'))            
            return res

        km_pool = self.pool.get('account.analytic.expense.km')

        km_ids = km_pool.search(cr, uid, [
            ('month', '>=', date_from),  # TODO
            ])

        total = 0.0    
        for item in km_pool.browse(cr, uid, km_ids, context=context):
            res[item.account_id.id] = item.km
            total += item.km
        
        if not total:
            _logger.error(_('Sum of total Km is 0!'))
            return {}

        rate = amount / total
        for item in res:
            res[item] *= rate
        return res
account_analytic_expense()

class account_analytic_account(osv.osv):
    ''' *many relation fields
    '''
    _name = 'account.analytic.account'
    _inherit = 'account.analytic.account'
    
    _columns =  {
        'km_ids': fields.one2many('account.analytic.expense.km', 'account_id',
            'Cost Km')
        }
account_analytic_account()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
