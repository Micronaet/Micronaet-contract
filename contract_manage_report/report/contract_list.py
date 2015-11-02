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
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_contract': self.get_contract,
            'get_department': self.get_department,
        })

    def get_department(self, data=None):
        ''' Get department list with wizard parameter
        '''    
        # TODO interface with wizard (for department Id or all)
        if data is None: 
            data={}
        filter_dept=[]
        if data:
            
            dept=data.get('department_id', False)
            if dept:
                filter_dept=[('id','=',dept)]

        dept_pool = self.pool.get('hr.department')
        dept_ids = dept_pool.search(self.cr, self.uid, filter_dept, 
            order='name')
        return dept_pool.browse(self.cr, self.uid, dept_ids)
        
    def get_contract(self, department_id, data=None):
        ''' Get list of contract with passed department
        '''    

        if data is None: 
            data={}

        domain = [('department_id','=',department_id)]
        if data.get('active', False):
            domain.append(('state', 'in', ['open']))
        
        contract_id = data.get('contract_id', False)
        if contract_id:
           domain.append(('id','=',contract_id))
        
        contract_pool = self.pool.get('account.analytic.account')
        contract_ids = contract_pool.search(self.cr, self.uid, domain, 
            order='code,name')
        return contract_pool.browse(self.cr, self.uid, contract_ids)

