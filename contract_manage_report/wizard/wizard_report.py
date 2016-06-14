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

import logging
from osv import osv, fields
from tools.translate import _
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

month_list= [('01','January'),
             ('02','February'),
             ('03','March'),
             ('04','April'),
             ('05','Maj'),
             ('06','June'),
             ('07','July'),
             ('08','August'),
             ('09','September'),
             ('10','October'),
             ('11','November'),
             ('12','December'),
            ]

# WIZARD INTERVENT REPORT ######################################################
class contract_report_intervent_wizard(osv.osv_memory):
    ''' Middle window to choose intervent report parameter
    '''
    
    _name = 'contract.report.intervent.wizard'
    _description = 'Intervent report wizard'
    
    # Button events:
    def print_invoice(self, cr, uid, ids, context=None):
        ''' Redirect to intervent print passing parameters
        ''' 
        wiz_proxy = self.browse(cr, uid, ids)[0]

        datas = {}
        if wiz_proxy.all:
            datas['department_id'] = False
            datas['department_name'] = 'All'
        else:
            datas['department_id'] = wiz_proxy.department_id.id
            datas['department_name'] = wiz_proxy.department_id.name

        if wiz_proxy.absence_account_id:            
            datas['absence_account_id'] = wiz_proxy.absence_account_id.id 
            datas['absence_account_name'] = wiz_proxy.absence_account_id.name 
            
        datas['month'] = wiz_proxy.month
        datas['year'] = wiz_proxy.year
        
        # not_work report:
        datas['user_id'] = wiz_proxy.user_id.id
        datas['user_name'] = wiz_proxy.user_id.name
        datas['from_date'] = wiz_proxy.from_date
        datas['to_date'] = wiz_proxy.to_date
        datas['detailed'] = wiz_proxy.detailed        

        
        if wiz_proxy.mode == 'intervent':
            report_name = 'intervent_report'
        elif wiz_proxy.mode == 'absence':
            report_name = 'absence_report'
        else:    
            report_name = 'not_work_report'

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            }
        
    _columns = {
        'all': fields.boolean('All department', required=False),
        'department_id': fields.many2one('hr.department', 'Department', 
            required=False),
        'year': fields.integer('Year'),
        'month': fields.selection(month_list, 'Month', select=True),

        # For not_work:    
        'user_id': fields.many2one('res.users', 'Employee / User'),
        'from_date': fields.date('From date >='),
        'to_date': fields.date('To date <='),
        'detailed': fields.boolean('Detailed'),
        
        'mode': fields.selection([
            ('intervent','Intervent'),
            ('absence','Absence'),        
            ('not_work','Not work status'), # statistic on absence
        ], 'Mode', select=True, readonly=False, required=True),
        
        'absence_account_id': fields.many2one('account.analytic.account', 
            'Absence type', required=False, 
            help="If absence report is only for one type of account"),
        }    
        
    _defaults = {
        'all': lambda *a: True,
        'month': lambda *a: datetime.now().strftime('%m'),
        'year': lambda *a: datetime.now().strftime('%Y'),
        'mode': lambda *a: 'intervent',
        }
contract_report_intervent_wizard()

# WIZARD CONTRACT DEPT. REPORT ################################################
class contract_department_report_wizard(osv.osv_memory):
    ''' Middle window to choose intervent report parameter
    '''
    
    _name = 'contract.department.report.wizard'
    _description = 'Contract dept. report wizard'
    
    # Button events:
    def print_invoice(self, cr, uid, ids, context=None):
        ''' Redirect to contract dept. print passing parameters
        ''' 
        wiz_proxy = self.browse(cr, uid, ids)[0]

        datas = {}
        if wiz_proxy.mode == 'detailed': # Detailed report ####################
            # block:
            datas['hour'] = wiz_proxy.hour
            datas['cost'] = wiz_proxy.cost
            datas['invoice'] = wiz_proxy.invoice
            datas['balance'] = wiz_proxy.balance
            datas['supplier'] = wiz_proxy.supplier

            # date:
            datas['start_date'] = wiz_proxy.start_date
            datas['end_date'] = wiz_proxy.end_date

            datas['active_contract'] = wiz_proxy.active_contract

            datas['date_summary'] = (wiz_proxy.end_date or wiz_proxy.start_date) and wiz_proxy.date_summary # True if there's one date and set to true
            
            # report name
            report='contracts_report'
            
        elif wiz_proxy.mode == 'list':  # Simple list report ##################
            datas['active'] = wiz_proxy.active
            report = 'dept_contract_list_report'
            
        else: # Summary report ################################################
            #datas['department_id'] = wiz_proxy.department_id.id if wiz_proxy.department_id else False 
            datas['start_date'] = wiz_proxy.start_date
            datas['end_date'] = wiz_proxy.end_date

            report='dept_contract_summary' # TODO create report

        if wiz_proxy.all_contract:
            datas['contract_id'] = False
            if wiz_proxy.all:        
                datas['department_id'] = False
            else:
                datas['department_id'] = wiz_proxy.department_id.id
                datas['department_name'] = wiz_proxy.department_id.name
        else: # contract selected:
            datas['contract_id'] = wiz_proxy.contract_id.id
            datas['contract_name'] = wiz_proxy.contract_id.name
            datas['department_id'] = wiz_proxy.contract_id.department_id.id if wiz_proxy.contract_id.department_id else False
            datas['department_name'] = wiz_proxy.department_id.name
            
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report, #'dept_contract_list_report',
            'datas': datas,
        }
        
    _columns = {
        'all_contract': fields.boolean('All contract',),
        'active_contract': fields.boolean('Active contract',),
        'contract_id': fields.many2one('account.analytic.account', 'Contract', 
            required=False, 
            help="All 'working' contract in contract list (absence fake contract not visible)"),

        'all':fields.boolean('All department',),
        'active':fields.boolean('Only active', help='In open state'),
        'department_id':fields.many2one('hr.department', 'Department', 
            required=False),

        'mode':fields.selection([
            ('list','Short list'),
            ('detailed','Detailed'),            
            ('summary','Summary'),            
        ],'Mode', select=True, required=True),

        # Blocks:
        'hour':fields.boolean('With hours'),
        'cost':fields.boolean('With cost'),
        'invoice':fields.boolean('With invoice'),
        'balance':fields.boolean('With balance'),
        'supplier':fields.boolean('With supplier invoice'),
        
        'date_summary':fields.boolean('With date summary', required=False),
        'start_date': fields.date('Start date', help="Start date of period, for evaluate costs, intervent, invoice"),        
        'end_date': fields.date('End Date', help="End date of period, for evaluate cost, intervent, invoice"),        
        }    
        
    _defaults = {
        'mode': lambda *a: 'list',
        
        'all': lambda *a: True,
        'active': lambda *a: False,
        
        'all_contract': lambda *a: True,

        'hour': lambda *a: True,
        'cost': lambda *a: True,
        'invoice': lambda *a: True,
        'balance': lambda *a: True,
        'supplier': lambda *a: True,
        'date_summary': lambda *a: True,
        }
contract_department_report_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

