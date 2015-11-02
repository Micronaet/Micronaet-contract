###############################################################################
#
# Copyright (c) 2008-2010 SIA "KN dati". (http://kndati.lv) All Rights Reserved.
#                    General contacts <info@kndati.lv>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class HrAnalyticTimesheet(orm.orm):
    ''' Add utility to timesheet for calculare month elements
    '''
    _inherit = 'hr.analytic.timesheet'
    
    # -------------------------------------------------------------------------
    #                             Utility:
    # -------------------------------------------------------------------------
    def get_employee_worked_hours(self, cr, uid, user_ids, from_date, to_date, 
            worked, not_worked, not_worked_recover, context=None):
        ''' Search in analytic account line all employee_id.user_id that 
            has worked hour for the period
            compile worked and not worked dict with: 
                   {user_id: {day_of_month: worked}
                   {user_id: {day_of_month: not worked}
        '''
        res = {}
        
        # ---------------------------------------
        # only this user_id in the from-to period
        # ---------------------------------------
        line_ids = self.search(cr, uid, [
            ('user_id', 'in', user_ids),
            ('date', '>=', from_date.strftime("%Y-%m-%d")),
            ('date', '<=', to_date.strftime("%Y-%m-%d"))],
            )
                                              
        # -----------------------------------
        # loop all lines for totalize results                                      
        # -----------------------------------
        for line in self.browse(cr, uid, line_ids): 
            month_day = int(line.date[8:10])
            amount = line.unit_amount or 0.0
            
            
            if line.account_id.is_recover: 
                # recover:
                dict_ref = not_worked_recover
            elif line.account_id.not_working: 
                # absence: 
                dict_ref = not_worked
            else: 
                # presence
                dict_ref = worked

            if line.user_id.id not in dict_ref:
                dict_ref[line.user_id.id] = {}
                dict_ref[line.user_id.id][month_day] = amount
            else:    
                if month_day in dict_ref[line.user_id.id]:
                    dict_ref[line.user_id.id][month_day] += amount
                else:    
                    dict_ref[line.user_id.id][month_day] = amount
                    
            # total column:
            if 32 in dict_ref[line.user_id.id]: 
                dict_ref[line.user_id.id][32] += amount
            else:    
                dict_ref[line.user_id.id][32] = amount
            # TODO update total!!!! (worked and not worked)
        return 

    def force_update_product_analytic_line(self, cr, uid, context=None):
        ''' Schedule function (ex called via XMLRPC) to update description in 
            analytic line
            (ex import procedure now automate launched from master schedule)
        ''' 
        # Pool used:
        journal_pool = self.pool.get('account.analytic.journal')
        line_pool = self.pool.get('account.analytic.line')
        product_pool = self.pool.get('product.product')
                
        _logger.info("Start update!")
        att_ids = journal_pool.search(cr, uid, [
            ('code', '=', 'ATT')], context=context)

        line_ids = line_pool.search(cr, uid, [
            ('journal_id', '=', att_ids[0]),
            ], context=context)

        i = 0          
        _logger.info('Found %s line!' % len(line_ids))  
        for line in line_pool.browse(cr, uid, line_ids, context=context):
            i += 1
            if not line.product_id:
                _logger.error('Product not found (null in line)')
                continue

            # Hour cost need to change also product:
            if line.product_id.is_hour_cost:
                try:
                    # Change product_id and after set name of product
                    product_ids = product_pool.search(cr, uid, [
                        ('name', '=', line.name)], context=context)

                    if not product_ids:
                        _logger.error('Product name not found in database')
                        continue

                    if len(product_ids) > 1:
                        _logger.warning('More than one record (take first)!')
                        continue

                    product_proxy = product_pool.browse(
                        cr, uid, product_ids, context=context)[0]

                    _logger.info(
                        '%s. %s Update product: %s [%s] in %s>%s [%s]' % (
                            line.id,
                            line.date,
                            line.product_id.name_template,
                            line.product_id.standard_price,
                            product_proxy.name,
                            product_proxy.name_template,
                            product_proxy.standard_price,
                            )) 

                    line_pool.write(cr, uid, line.id, {
                        'name': product_proxy.name_template,            
                        'product_id': product_proxy.id,
                        'amount': -(
                            line.unit_amount * product_proxy.standard_price),
                        }, context=context)
                    continue    
                except:
                    _logger.error('Error')
                    _logger.error('%s' % (sys.exc_info(), ))
                    continue
        
            # other line check only name
            if line.product_id.name != line.product_id.name_template:
                try:
                    _logger.info("%s. Change name %s > %s" % ( 
                        line.id,
                        line.product_id.name,
                        line.product_id.name_template,
                        ))
                    line_pool.write(cr, uid, line.id, {
                        'name': line.product_id.name_template,
                        }, context=context)
                except:
                    _logger.error('Error')
                    _logger.error('%s' % (sys.exc_info(), ))
                    
            else:
                _logger.warning('Not updated: %s' % line.name)
                       
        _logger.info("End update!")
        return True

    # --------------------
    # Schedule operations:
    # --------------------
    # Master function for scheduled importation:
    def schedule_importation_cost(self, cr, uid, path='~/etl/employee', 
            bof='cost', separator=';', context=None):
        ''' Loop on cost folder searching file that start with bof
        '''
        from os.path import isfile, join
        path = os.path.expanduser(path)
        cost_file = [
            filename for filename in listdir(path) if 
                    isfile(join(path, filename)) and filename.startswith(bof) 
                    and len(filename) == (len(bof) + 8)] # YYAA.csv = 8 char

        cost_file.sort() # for have last price correct
        _logger.info("Start auto import of file cost")
        for filename in cost_file:        
            try:
                _logger.info("Load and import file %s" % filename)
                error = []                             
                # -------------------------------------------------------------
                #                             Load
                # -------------------------------------------------------------
                self.load_one_cost(cr, uid, path=path, filename=filename, 
                    separator=separator, error=error, context=context)
                    
                # -------------------------------------------------------------
                #                            Import
                # -------------------------------------------------------------
                # Parse date
                file_date = os.path.splitext(filename)[0][-4:]
                from_year = int(file_date[:2])
                from_month = int(file_date[2:])
                
                # Next value
                if from_month == 12:
                    next_month = 1
                    next_year = from_year + 1
                else:    
                    next_month = from_month + 1
                    next_year = from_year

                from_date = '20%02d-%02d-01' % (from_year, from_month)
                to_date = '20%02d-%02d-01' % (next_year, next_month)

                name = _('Auto import [month: %s-%s]') % (
                    from_month, from_year)

                self.import_one_cost(cr, uid, name=name, from_date=from_date, 
                    to_date=to_date, error=error, context=context)
                
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
        _logger.info("End auto import of file cost")
        return True

    # --------
    # Utility:        
    # --------
    def load_one_cost(self, cr, uid, path, filename, separator,
            from_wizard=False, error=None, context=None):
        ''' Import one file, used from import procedure (usually scheduled)
        '''
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

        tot_col = 5 # TODO change if file will be extended
        if error is None:
            error = []

        fullname = os.path.join(os.path.expanduser(path), filename)
        domain = []
        force_cost = {}
       
        # Load from file employee:
        employee_pool = self.pool.get('hr.employee')            
        item_ids = [] # employee list
        
        # Check file present (for wizard but used alse for sched.)?
        try: 
            f = open(os.path.expanduser(fullname), 'rb')
        except:
            error.append(_('No file found for import: %s') % fullname)
            _logger.error(error[-1])

        i = 0
        for line in f:
            try:
                i += 1
                
                line = line.strip()
                if not line:
                    error.append(_('%s. Empty line (jumped)') % i)
                    _logger.warning(error[-1])
                    continue
                record = line.split(separator)
                
                if len(record) != tot_col:
                    error.append(_(
                        '%s. Record different format: %s (col.: %s)') % (
                            i, 
                            tot_col,
                            len(record),
                            ))
                    _logger.error(error[-1])
                    continue

                code = format_string(record[0], False)
                name = format_string(record[1]).title()
                surname = format_string(record[2]).title()
                cost = format_float(record[3])
                total = format_float(record[4])

                if not cost:
                    error.append(_('%s. Error no hour cost: %s %s [%s]') % (
                        i, name, surname, code))
                    _logger.error(error[-1])
                    continue
                    
                # Search first for code
                # TODO search also in deactivated users?
                employee_ids = [] # TODO not necessary
                update_code = False
                if code:
                    employee_ids = employee_pool.search(cr, uid, [
                        ('identification_id', '=', code),
                        ], context=context)
                        
                if not employee_ids:
                    update_code = True
                    employee_ids = employee_pool.search(cr, uid, [
                        '|',
                        ('name', '=', "%s %s" % (name, surname)),
                        ('name', '=', "%s %s" % (surname, name)),
                        ], context=context)

                if len(employee_ids) == 1:
                    if update_code: # Save code for next use
                        employee_pool.write(cr, uid, employee_ids, {
                            'identification_id': code,
                            }, context=context)
                    employee_id = employee_ids[0]
                    if employee_id in item_ids:
                        error.append(
                            _('%s. Double in CSV file: %s %s [%s]') % (
                                i, surname, name, code))
                        _logger.error(error[-1])
                    else:
                        item_ids.append(employee_id)
                        force_cost[employee_id] = cost # save cost
                elif len(employee_ids) > 1:
                    error.append(_('%s. Fount more employee: %s %s [%s]') % (
                        i, surname, name, code))
                    _logger.error(error[-1])                   
                else:
                    error.append(_('%s. Employee not found: %s %s [%s]') % (
                        i, surname, name, code))
                    _logger.error(error[-1])

            except:
                error.append("%" % (sys.exc_info(), ))
                _logger.error('%s. Generic error line:' % i)
                _logger.error(error[-1])

        f.close() # for rename
        domain.append(('id', 'in', item_ids))
                
        # Load in object for check:
        self.pool.get('hr.employee.hour.cost').load_all_employee(
            cr, uid, domain, force_cost, context=context)
            
        # Open view:    
        if from_wizard:
            return {
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.employee.hour.cost', # obj linked to the view
                #'views': [(view_id, 'form')],
                'view_id': False,
                'type': 'ir.actions.act_window',
                #'target': 'new',
                #'res_id': res_id, # ID selected
                }
        else:
            return True
    
    def import_one_cost(self, cr, uid, name='', from_date=False, to_date=False,
            from_wizard=False, error=None, context=None):
        ''' Import previous loaded list of employee costs
            name: for log description
            from_date: from date update analytic line
            from_wizard: for return operation 
        '''
        # Pools used:
        cost_pool = self.pool.get('hr.employee.hour.cost')
        product_pool = self.pool.get('product.product')
        employee_pool = self.pool.get('hr.employee')
        line_pool = self.pool.get('account.analytic.line')
        journal_pool = self.pool.get('account.analytic.journal')
        log_pool = self.pool.get('hr.employee.force.log')
        
        # ---------------
        # Log operations:
        # ---------------
        # Note: Logged before for get ID
        timesheet_journal_ids = journal_pool.search(cr, uid, [
            ('code', '=', 'TS')], context=context)
        if not timesheet_journal_ids:
            _logger.error('Timesheet (TS) journal not found!')
            return False
        _logger.info('Get Timesheet (code TS) journal for filter')
            
             
        update_log_id = log_pool.log_operation(
            cr, uid, name, from_date, error, context=context)

        cost_ids = cost_pool.search(cr, uid, [], context=context)
        for cost in cost_pool.browse(cr, uid, cost_ids, context=context):
            try:
                standard_price = cost.hour_cost_new # new standard price
                
                # ----------------------------------------------
                # Force product to employee (for new creations):
                # ----------------------------------------------
                # TODO optimize for create update only new product
                employee_pool.write(cr, uid, cost.employee_id.id, {
                    'product_id': cost.product_id.id,
                    }, context=context)

                # -----------------------------
                # Force new product hour costs:
                # -----------------------------        
                # test if the update date is greater than:
                current_date = cost.product_id.update_price_date
                if not current_date or from_date > current_date:                
                    product_pool.write(cr, uid, cost.product_id.id, {
                        'standard_price': standard_price,
                        'update_price_date': from_date, 
                        }, context=context)
                    
                # ------------------------------------------------
                # Update analytic lines save log operation parent:
                # ------------------------------------------------
                domain = [
                    ('journal_id', '=', timesheet_journal_ids[0]), # only
                    ('user_id', '=', cost.employee_id.user_id.id),
                    ('date', '>=', from_date),
                    ]
                if to_date: # for schedule update only
                    domain.append(
                        ('date', '<', to_date),
                        )
                line_ids = line_pool.search(cr, uid, domain, context=context)
                    
                # loop for total calculation:
                for line in line_pool.browse(
                        cr, uid, line_ids, context=context):    
                    line_pool.write(cr, uid, line.id, {
                        'amount': -(standard_price * line.unit_amount),
                        'update_log_id': update_log_id,
                        'product_id': cost.product_id.id, 
                        }, context=context)
            except:
                _logger.error('Employee update: %s' % cost.employee_id.name)
                _logger.error(sys.exc_info(), )
                continue

        if from_wizard:
            return {'type': 'ir.actions.act_window_close'}
        else:    
            return True
HrAnalyticTimesheet()        
