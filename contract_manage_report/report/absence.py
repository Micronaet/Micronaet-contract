##############################################################################
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
##############################################################################

from report import report_sxw
from report.report_sxw import rml_parse

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        ''' Parser init
        '''
        if context is None:
            context = {}
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_employee': self.get_employee,
            'get_employee_absence': self.get_employee_absence,
            'get_filter_description': self.get_filter_description,
        })

    def get_filter_description(self, data = None):
        ''' Return string that describe wizard filter elements (from data passed)
        '''
        if data is None:
            data = {}
            
        if not data:
            return "Nessun filtro"
        else:
            return "Dipartimento: %s - Periodo: %s-%s - Tipo di assenza: %s"%(data.get('department_name',"Tutti"),
                                                                              data.get('month',"00"), 
                                                                              data.get('year',"0000"),
                                                                              data.get('absence_account_name',"Tutte"))
            
    def get_employee_absence(self, employee_id, data = None):
        ''' Return employee list of intervent that is not working
        '''        
        ts_pool = self.pool.get('hr.analytic.timesheet')
        
        # Create filter:
        if data is None:
            data = {}
        # generic:    
        domain=[('user_id','=',employee_id),('account_id.not_working','=',True)]
        # check contract selected:
        absence_account_id = data.get('absence_account_id', False)
        if absence_account_id:
            domain.append(('account_id','=',absence_account_id))
        # check period
        month = data.get('month', False)
        year = data.get('year',False)
        if month and year:        
           month = int(month)
           start = "%04d-%02d-01"%(year, month)
           end = "%04d-%02d-01"%(year + 1 if month == 12 else year, month + 1 if month < 12 else 1)
           domain.append(('date','>=',start))
           domain.append(('date','<',end))           

        ts_ids = ts_pool.search(self.cr, self.uid, domain, order='date')
        return ts_pool.browse(self.cr, self.uid, ts_ids)
        
    def get_employee(self, data = None):
        ''' Get employee list of absence
        '''
        #employee_pool = self.pool.get('hr.employee')
        employee_pool = self.pool.get('res.users')
        domain=[]
        if data is None:
            data = {}
        if data.get('department_id', False):
            domain.append(('context_department_id','=',data.get('department_id', 0)))
         
        employee_ids = employee_pool.search(self.cr, self.uid, domain)
        return employee_pool.browse(self.cr, self.uid, employee_ids)
