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


import time 
from datetime import datetime
from osv import osv, fields
from tools.translate import _

# python represent weekday starting from 0 = Monday
week_days = [
    ('mo', 'Monday'),  
    ('tu', 'Tuesday'),     
    ('we', 'Wednesday'),     
    ('th', 'Thursday'),     
    ('fr', 'Friday'),     
    ('sa', 'Saturday'),     
    ('su', 'Sunday'),
    ]

class contract_employee_timesheet_tipology(osv.osv):
    ''' Contract tipology: contains a list of "day of a week" elements and the
        total amount of hour to be worked that day
    '''
    
    _name = 'contract.employee.timesheet.tipology'
    _description = 'Timesheet tipology'
    
    _columns = {
        'name': fields.char('Description', size=64),
    }
contract_employee_timesheet_tipology()

class contract_employee_timesheet_tipology_line(osv.osv):
    ''' Sub element of contract tipology: contains dow and tot. hours
    '''
    
    _name = 'contract.employee.timesheet.tipology.line'
    _description = 'Timesheet tipology line'
    
    _columns = {
        'name': fields.float('Tot. hours', required=True, digits=(4, 2)),
        'week_day':fields.selection(week_days,'Week day', select=True),
        'contract_tipology_id':fields.many2one(
            'contract.employee.timesheet.tipology', 'Contract tipology', 
            required=True, ondelete='cascade'),
    }
contract_employee_timesheet_tipology_line()

class contract_employee_timesheet_tipology(osv.osv):
    ''' Contract tipology: add relation 2many fields
    '''
    
    _inherit = 'contract.employee.timesheet.tipology'

    _columns = {
        'line_ids': fields.one2many(
            'contract.employee.timesheet.tipology.line', 
            'contract_tipology_id', 'Lines'),
    }
contract_employee_timesheet_tipology()

class contract_employee_festivity(osv.osv):
    ''' Festivity manage: 
        manage static festivity (also with from-to period)
        manage dynamic list of festivity (ex. Easter monday)
    '''
    
    _name = 'contract.employee.festivity'
    _description = 'Contract festivity'
    
    # TODO: function for compute festivity
    # TODO: function for validate: 
    #       static date (max day for day-month)
    #       from to period evaluation (no interference)
    #       no double comment in dynamic date 
    #          (2 Easter monday for ex. in the same year)
    
    def is_festivity(self, cr, uid, date, context=None):
        ''' Test if datetime element date is in festifity rules
        '''
        # Static festivity (periodic):
        date_ids = self.search(cr, uid, [
            ('static', '=', True), 
            ('periodic', '=', True), 
            ('day', '=', date.day),
            ('month', '=', date.month),
            ('periodic_from', '>=', date.year),
            ('periodic_to', '<=', date.year),
            ]) 
        if date_ids:
            return True

        # Static festivity not periodic:
        date_ids = self.search(cr, uid, [
            ('static', '=', True), 
            ('periodic', '=', False), 
            ('day', '=', date.day),
            ('month', '=', date.month),
            ]) 
        if date_ids:
            return True

        # Dinamic festivity:
        date_ids = self.search(cr, uid, [
            ('static', '=', False), 
            ('dynamic_date', '=', date.strftime("%Y-%m-%d")),
            ])
        if date_ids:
            return True
        
        return False
    
    _columns = {
        'name': fields.char('Description', size=64),

        # static festivity:
        'static': fields.boolean('Static festivity', 
            help="It means that every year this festivity is the same day (ex. Christmas = 25 of dec.), if not it's dynamic (ex. Easter monday)"),
        'day': fields.integer('Static day'),
        'month': fields.integer('Static month'),
        # static but periodic:
        'periodic': fields.boolean('Periodic festivity', 
            help="Festivity is only for a from-to period (ex.: Patronal festivity but for a period because of changing city)"),
        'periodic_from': fields.integer('From year'),
        'periodic_to': fields.integer('To year'),
        
        # dinamic festivity (no periodic is allowed):
        'dynamic_date': fields.date('Dynamic Date'),
        }

    _defaults = {
        'periodic_from': lambda *a: time.strftime('%Y'),
        'periodic_to': lambda *a: time.strftime('%Y'),
        }
contract_employee_festivity()

class hr_employee_extra(osv.osv):
    """ Employee extra fields for manage contract and working hours
        TODO: create a list of working hour contract (for history of elements)
    """    
    _inherit = 'hr.employee'
    
    def check_consistency_employee_user_department(
            self, cr, uid, context=None):
        ''' Procedure for xml-rpc call for check consistency of DB
            1. check if employee has user linked
            2. check if 
        '''
        #TODO finirla
        user_pool = self.pool.get("res.users")
        employee_proxy=self.browse(cr, uid, self.search(
            cr, uid, [], context=context))
        
        for employee in employee_proxy:
            if employee.user_id and employee.department_id:                
                update = user_pool.write(cr, uid, employee.user_id.id, {
                    'context_department_id': employee.department_id.id})
        return True
        
    _columns = {
        'contract_tipology_id':fields.many2one(
            'contract.employee.timesheet.tipology', 'Work time', 
            help="Working time for this employee, tipically a contract tipology, like: full time, part time etc. (for manage hour and presence)"),
    }
hr_employee_extra()

# -----------------------------------------------------------------------------
# Add importation hour cost for employee:
# -----------------------------------------------------------------------------

class product_product(osv.osv):
    """ Add extra info to manage product linked to employee:
    """    
    _inherit = 'product.product'

    _columns = {
        'product_employee_id': fields.many2one(
            'hr.employee', 'Employee linked', 
            help='Product as hour cost for selected employee'),
        }
    _defaults = {
        'product_employee_id': lambda *x: False,
        }
product_product()        

class hr_employee_hour_cost(osv.osv):
    """ Temporary zone for create a list of employee, set product and force 
        update of product on OpenERP and analytic line value
    """    
    _name = 'hr.employee.hour.cost'
    _description = 'Employee load hour cost'
    _rec_name = 'product_id'

    
    def load_all_employee(self, cr, uid, domain=None, force_cost=None,
            context=None):
        ''' Load all active employee, during operazion create if not present
            Reference product (or linked) without associate, after a wizard do
            the magic
            domain = filter for hr.emploee
            force_cost: dict with key = employee ID, value = new price
        '''
        # Remove current list:
        if domain is None: # domain passed (file list or wizard list)
            domain = []

        if force_cost is None: # list of user pre-passed (file)
            force_cost = {}

        # Remove all previous elements:
        current_ids = self.search(cr, uid, [], context=context)
        self.unlink(cr, uid, current_ids, context=context)

        # ---------------------------------------------------------------------
        # Load new list:
        # ---------------------------------------------------------------------
        if not force_cost: # for wizard load only (file admitted):
            domain.append(('active', '=', True))

        # Load before all product employee list (to know if need do be created)    
        employee_pool = self.pool.get('hr.employee')
        product_pool = self.pool.get('product.product')
            
        # Create dict from personal product-employee
        products = {} # ID product for employee 
        costs = {} # standard price for employee

        # Pre-load cost and products:
        employee_ids = employee_pool.search(cr, uid, domain, context=None)
        product_ids = product_pool.search(cr, uid, [
            ('product_employee_id', '!=', False)], context=None)
        for product in product_pool.browse(
                cr, uid, product_ids, context=context):    
            # Save id and price:
            products[product.product_employee_id.id] = product.id
            costs[product.product_employee_id.id] = product.standard_price 

        # Loop on selected employee:
        for employee in employee_pool.browse(
                cr, uid, employee_ids, context=context):
            hour_id = 4 # TODO
            categ_id = 1 # TODO
            cost_old = employee.product_id.standard_price or 0.0
            data = {
                'name': _('Hour cost: %s') % employee.name,
                'type': 'service',
                'procure_method': 'make_to_stock',
                'supply_method': 'buy',
                'uom_id': hour_id,
                'uom_po_id': hour_id,
                'cost_method': 'standard',
                'standard_price': cost_old,
                'uos_coeff': 1.0,
                'mes_type': 'fixed',
                'categ_id': categ_id,
                'product_employee_id': employee.id,
                'sale_ok': True,
                'purchase_ok': True,
                'is_hour_cost': True,
                }
            
            if employee.id in products: # employee has yet a product:
                new = False
                product_pool.write( # TODO remove?
                    cr, uid, products[employee.id], data, context=context)
            else:
                new = True                
                # Create product element (not associate)
                costs[employee.id] = cost_old
                products[employee.id] = product_pool.create(
                    cr, uid, data, context=context)

            cost_new = (force_cost.get(employee.id, False) or 
                costs[employee.id] or 
                0.0) # 0 not a sort of default value!

            # Pre-load list:
            data = {
                'employee_id': employee.id,
                'product_id': products[employee.id],
                'current_product_id': employee.product_id.id,
                'new': new,
                'hour_cost': cost_old,
                'hour_cost_new': cost_new,
                }   
            self.create(cr, uid, data, context=context)        
        return {}
        
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'current_product_id': fields.many2one('product.product', 
            'Current product'),
        'product_id': fields.many2one('product.product', 'Product'),
        'new': fields.boolean('New product'),
        'hour_cost': fields.float('Current hour cost', digits=(16, 2)),
        'hour_cost_new': fields.float('New hour cost', digits=(16, 2)),
        }
hr_employee_hour_cost()

class hr_employee_force_log(osv.osv):
    """ Object that log all force operations
    """    
    
    _name = 'hr.employee.force.log'
    _description = 'Employee force log'
    _rec_name = 'name'

    def log_operation(self, cr, uid, name, from_date, context=None):    
        ''' Create new record with log of new price se for employee and date
            of intervent update (in analytic lines)
            Return line (to save in analytic modification)
        '''
        cost_pool = self.pool.get('hr.employee.hour.cost')
        cost_ids = cost_pool.search(cr, uid, [], context=context)
        note = ''
        for cost in cost_pool.browse(cr, uid, cost_ids, context=context):
            note += _('%s hour cost %s >> %s\n') % (
                cost.employee_id.name,
                cost.hour_cost,
                cost.hour_cost_new,
                )
        return self.create(cr, uid, {
            #date
            'name': name or _(
                'Forced costs from date: %s') % from_date,
            'from_date': from_date,
            'note': note,
            }, context=context)        
        
    _columns = {
        'name': fields.char('Description', size=80),
        'date': fields.datetime('Date operation'),
        'from_date': fields.date('From date',
            help='All intervent from this date will use new value'),
        'note': fields.text('Note'),
        }

    _defaults = {
        'date': lambda *x: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'from_date': lambda *x: datetime.now().strftime('%Y-%m-%d'),
        }
hr_employee_force_log()

class account_analytic_line(osv.osv):
    """ Auto update record (save element for get list)
    """    
    
    _inherit = 'account.analytic.line'

    _columns = {
        'update_log_id': fields.many2one(
            'hr.employee.force.log', 'Auto update', ondelete='set null'),        
        }
account_analytic_line()

class hr_employee_force_log(osv.osv):
    """ Update log with *many relation fileds
    """    
    
    _inherit = 'hr.employee.force.log'
    
    _columns = {
        'line_ids': fields.one2many('account.analytic.line', 'update_log_id',
            'Line update from this log'),
        }
hr_employee_force_log()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
