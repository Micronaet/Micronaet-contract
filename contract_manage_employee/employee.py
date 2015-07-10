# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>) 
#    
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
#############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
import time 
from tools.translate import _

week_days = [('mo','Monday'),  # python represent weekday starting from 0 = Monday
             ('tu','Tuesday'),     
             ('we','Wednesday'),     
             ('th','Thursday'),     
             ('fr','Friday'),     
             ('sa','Saturday'),     
             ('su','Sunday'),]
             
class contract_employee_timesheet_tipology(osv.osv):
    ''' Contract tipology: contains a list of "day of a week" elements and the
        total amount of hour to be worked that day
    '''
    
    _name = 'contract.employee.timesheet.tipology'
    _description = 'Timesheet tipology'
    
    _columns = {
        'name':fields.char('Description', size=64, required=False, readonly=False),
    }
contract_employee_timesheet_tipology()

class contract_employee_timesheet_tipology_line(osv.osv):
    ''' Sub element of contract tipology: contains dow and tot. hours
    '''
    
    _name = 'contract.employee.timesheet.tipology.line'
    _description = 'Timesheet tipology line'
    
    _columns = {
        'name': fields.float('Tot. hours', required=True, digits=(4, 2)),
        'week_day':fields.selection(week_days,'Week day', select=True, readonly=False),
        'contract_tipology_id':fields.many2one('contract.employee.timesheet.tipology', 'Contract tipology', required=True, ondelete='cascade'),
    }
contract_employee_timesheet_tipology_line()

class contract_employee_timesheet_tipology(osv.osv):
    ''' Contract tipology: add relation 2many fields
    '''
    
    _name = 'contract.employee.timesheet.tipology'
    _inherit = 'contract.employee.timesheet.tipology'

    _columns = {
        'line_ids':fields.one2many('contract.employee.timesheet.tipology.line', 'contract_tipology_id', 'Lines', required=False),
    }
contract_employee_timesheet_tipology()

class contract_employee_festivity(osv.osv):
    ''' Festivity manage: 
        manage static festivity (also with from-to period)
        manage dynamic list of festivity (ex. Easter monday)
    '''
    
    _name = 'contract.employee.festivity'
    _description = 'Contract festivity'
    
    import time
    # TODO: function for compute festivity
    # TODO: function for validate: 
    #       static date (max day for day-month)
    #       from to period evaluation (no interference)
    #       no double comment in dynamic date (2 Easter monday for ex. in the same year)
    
    def is_festivity(self, cr, uid, date, context=None):
        ''' Test if datetime element date is in festifity rules
        '''
        # Static festivity (periodic):
        date_ids = self.search(cr, uid, [('static','=',True), 
                                         ('periodic','=',True), 
                                         ('day','=',date.day),
                                         ('month','=',date.month),
                                         ('periodic_from','>=',date.year),
                                         ('periodic_to','<=',date.year),
                                        ]) 
        if date_ids:
            return True

        # Static festivity not periodic:
        date_ids = self.search(cr, uid, [('static','=',True), 
                                         ('periodic','=',False), 
                                         ('day','=',date.day),
                                         ('month','=',date.month),
                                        ]) 
        if date_ids:
            return True

        # Dinamic festivity:
        date_ids = self.search(cr, uid, [('static','=',False), 
                                         ('dynamic_date','=',date.strftime("%Y-%m-%d")),
                                         ])
        if date_ids:
            return True
        
        return False
    
    _columns = {
        'name':fields.char('Description', size=64, required=False, readonly=False),

        # static festivity:
        'static':fields.boolean('Static festivity', help="It means that every year this festivity is the same day (ex. Christmas = 25 of dec.), if not it's dynamic (ex. Easter monday)"),
        'day': fields.integer('Static day'),
        'month': fields.integer('Static month'),
        # static but periodic:
        'periodic':fields.boolean('Periodic festivity', help="Festivity is only for a from-to period (ex.: Patronal festivity but for a period because of changing city)"),
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
    _name = 'hr.employee'
    
    def check_consistency_employee_user_department(self, cr, uid, context=None):
        ''' Procedure for xml-rpc call for check consistency of DB
            1. check if employee has user linked
            2. check if 
        '''
        #TODO finirla
        user_pool = self.pool.get("res.users")
        employee_proxy=self.browse(cr, uid, self.search(cr, uid, [], context=context))
        
        for employee in employee_proxy:
            if employee.user_id and employee.department_id:                
                update=user_pool.write(cr, uid, employee.user_id.id, {'context_department_id': employee.department_id.id})
                
        return True
        
    _columns = {
        'contract_tipology_id':fields.many2one('contract.employee.timesheet.tipology', 'Work time', required=False, help="Working time for this employee, tipically a contract tipology, like: full time, part time etc. (for manage hour and presence)"),
    }
hr_employee_extra()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
