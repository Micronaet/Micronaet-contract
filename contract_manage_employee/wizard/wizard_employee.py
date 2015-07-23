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

    def force_button(self, cr, uid, ids, context=None):
        ''' Force button
        ''' 
        wiz_proxy = self.browse(cr, uid, ids)[0]

        datas = {}
        if wiz_proxy.all:
            datas['department_id'] = False
            datas['department_name'] = "All"
        else:
            datas['department_id'] = wiz_proxy.department_id.id
            datas['department_name'] = wiz_proxy.department_id.name

        if wiz_proxy.absence_account_id:            
            datas['absence_account_id'] = wiz_proxy.absence_account_id.id 
            datas['absence_account_name'] = wiz_proxy.absence_account_id.name 
            
        datas['month'] = wiz_proxy.month
        datas['year'] = wiz_proxy.year
        
        if wiz_proxy.mode == 'intervent':
            report_name = 'intervent_report'
        else:    
            report_name = 'absence_report'

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
        }
        
    _columns = {
        'date': fields.date('From date', 
            help='Choose the date, every intervent from that date take costs'),
        'month':fields.selection(month_list, 'Month', select=True, readonly=False, required=True),
        'operation':fields.selection([
            ('load', 'Load current'),
            ('absence', 'Force update'),
            ], 'Operation', select=True, readonly=False, required=True),
        }    
        
    _defaults = {
        'all': lambda *a: True,
        'month': lambda *a: datetime.now().strftime('%m'),
        'year': lambda *a: datetime.now().strftime('%Y'),
        'mode': lambda *a: 'intervent',
        }
hr_employee_force_hour()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

