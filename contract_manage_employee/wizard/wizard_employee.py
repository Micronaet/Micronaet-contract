# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>) and the
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
#    ########################################################################
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
##############################################################################

from osv import osv, fields
from datetime import datetime


class hr_employee_force_hour(osv.osv_memory):
    ''' Load elements and force hour cost in employee update analytic lines
    '''
    
    _name = 'hr.employee.force.hour.wizard'
    _description = 'Employee force hour cost'
    
    # Button events:
    def load_button(self, cr, uid, ids, context=None):
        ''' Load all active employee and his product, create if not present
            After open view with the list
        '''
        return self.pool.get('hr.employee.hour.cost').load_all_employee(
            cr, uid, context=context)

    def force_button(self, cr, uid, ids, context=None):
        ''' Force button update records
        ''' 
        wiz_proxy = self.browse(cr, uid, ids)[0]
        
        # Pools used:
        cost_pool = self.pool.get('hr.employee.hour.cost')
        product_pool = self.pool.get('product.product')
        employee_pool = self.pool.get('hr.employee')
        line_pool = self.pool.get('account.analytic.line')
        log_pool = self.pool.get('hr.employee.force.log')

        # ---------------
        # Log operations:
        # ---------------
        # Note: Logged before for get ID
        update_log_id = log_pool.log_operation(
            cr, uid, wiz_proxy.from_date, context=context)

        cost_ids = cost_pool.search(cr, uid, [], context=context)
        # TODO filter new = old?
        for cost in cost_pool.browse(cr, uid, cost_ids, context=context):
            # ---------------------------------------------
            # Force product to employee (for new creations):
            # ---------------------------------------------
            # TODO optimize for crete update only new product
            employee_pool.write(cr, uid, cost.employee.id, {
                'product_id': cost.product_id.id,
                }, context=context)            

            # -----------------------------
            # Force new product hour costs:
            # -----------------------------        
            if cost.hour_cost != cost.hour_cost_new:
                # if different update product record
                product_pool.write(cr, uid, cost.product_id.id, {
                    'standard_price': cost.hour_cost_new
                    }, context=context)
                    
                # ------------------------------------------------
                # Update analytic lines save log operation parent:
                # ------------------------------------------------
                line_ids = line_pool.search(cr, uid, [
                    ('user_id', '=', cost.employee_id.user_id.id), # TODO test
                    ('date', '>=', cost.from_date),
                    ], context=context)
                # loop cause total calculation value:
                for line in line_pool.browse(
                        cr, uid, line_ids, context=context):    
                    line_pool.write(cr, uid, line_ids, {
                        'unit_amount': cost.hour_cost_new,
                        'amount': cost.hour_cost_new * line.unit_amount,
                        'update_log_id': update_log_id,
                        # total?
                        }, context=context)
        # ------------------
        # Remove all record:
        # ------------------
        current_ids = cost_pool.search(cr, uid, [], context=context)
        cost_pool.unlink(cr, uid, current_ids, context=context)
            
        return True # or view?

    _columns = {
        'date': fields.date('From date', 
            help='Choose the date, every intervent from that date take costs'),
        'operation': fields.selection([
            ('load', 'Load current'),
            ('absence', 'Force update'),
            ], 'Operation', select=True, required=True),
        }    
        
    _defaults = {
        'operation': lambda *a: 'load',
        }
hr_employee_force_hour()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
