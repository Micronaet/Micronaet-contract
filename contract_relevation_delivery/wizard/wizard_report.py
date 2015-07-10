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

# WIZARD INTERVENT REPORT ######################################################
class etl_relevation_header_wizard(osv.osv_memory):
    ''' Middle window to choose intervent report parameter
    '''    
    _name = 'etl.relevation.header.wizard'
    _description = 'Relevation wizard'
    
    # Button events:
    def print_invoice(self, cr, uid, ids, context=None):
        ''' Redirect to intervent print passing parameters
        ''' 
        wiz_proxy = self.browse(cr, uid, ids)[0]
        datas = {}

        if wiz_proxy.all:
            datas['department_id'] = False
            datas['department_name'] = "Tutti"
        else:
            datas['department_id'] = wiz_proxy.department_id.id
            datas['department_name'] = wiz_proxy.department_id.name

        datas['start_date'] = wiz_proxy.start_date
        datas['end_date'] = wiz_proxy.end_date

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'report_hr_analytic_timesheet',
            'datas': datas,
            'context' : context,            
            #'active_ids': [1],
            #'active_id': 1,
        }
        
    _columns = {
        'all':fields.boolean('All department', required=False),
        'department_id':fields.many2one('hr.department', 'Department', required=False),
        'start_date': fields.date('Start date'),        
        'end_date': fields.date('End Date'), 
        }    
        
    _defaults = {
        'all': lambda *a: True,
        }
etl_relevation_header_wizard()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

