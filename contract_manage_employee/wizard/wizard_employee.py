# -*- encoding: utf-8 -*-
###############################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>) and the
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
#    ##########################################################################
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
import logging
from os import listdir
from tools.translate import _
from osv import osv, fields
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class hr_employee_force_hour(osv.osv_memory):
    ''' Load elements and force hour cost in employee update analytic lines
    '''
    
    _name = 'hr.employee.force.hour.wizard'
    _description = 'Employee force hour cost'
    
    # --------------------
    # Schedule operations:
    # --------------------
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
        ''' Import one file 
        '''
        # Utility: function for procedure:
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
                        error.append(_('%s. Double in CSV file: %s %s [%s]') % (
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

    # --------------
    # Button events:
    # --------------
    # TODO Remove wizard? vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
    def load_button(self, cr, uid, ids, context=None):
        ''' Load all active employee and his product, create if not present
            After open view with the list
        '''
        # ----------------------
        # Import file parameters
        # ----------------------
        # TODO load parameter from scheduled importation
        path = '~/etl/servizi/employee/'
        separator = ';'
        bof = 'costi' # begin of file

        return self.load_one_cost(cr, uid, path, filename, separator, 
            from_wizard=True, context=context)

    def force_button(self, cr, uid, ids, context=None):
        ''' Force button update records
        ''' 
        wiz_proxy = self.browse(cr, uid, ids)[0]
        
        # NOTE: no to_date from wizard:
        return self.import_one_cost(cr, uid, wiz_proxy.name, 
            wiz_proxy.from_date, False, from_wizard=True, context=context)
    # TODO Remove wizard? ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    _columns = {
        'name': fields.char('Description', size=80),
        'from_date': fields.date('From date', 
            help='Choose the date, every intervent from that date take costs'),
        #'to_date': fields.date('To date', 
        #    help='Choose the date, every intervent from that date take costs'),
        'operation': fields.selection([
            ('load', 'Load current'),
            ('absence', 'Force update'),
            ], 'Operation', select=True, required=True),
        'department_id': fields.many2one('hr.department', 'Department'),
        'mode': fields.selection([
            ('file', 'From file'),
            ('employee', 'From employee list'),
            ], 'Mode'),
        }    
        
    _defaults = {
        'from_date': lambda *x: datetime.now().strftime('%Y-%m-%d'),
        #'to_date': lambda *x: datetime.now().strftime('%Y-%m-%d'),
        'operation': lambda *a: 'load',
        'mode': lambda *a: 'file',
        }
hr_employee_force_hour()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

