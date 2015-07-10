##############################################################################
#
# Copyright (c) 2008-2011 Alistek Ltd (http://www.alistek.com) All Rights Reserved.
#                    General contacts <info@alistek.com>
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
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This module is GPLv3 or newer and incompatible
# with OpenERP SA "AGPL + Private Use License"!
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

totals={'ore':0.0, 'operazioni':0.0,'cost':0.0,'revenue':0.0}

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'user_list':self.user_list,
            'user_intervent': self.user_intervent,
            'get_total': self.get_total,
            'get_filter_description': self.get_filter_description,
        })

    def get_filter_description(self, data = None):
        ''' Descrizione filtro da wizard
        '''
        if data is None:
            data={}

        start_date = data.get('start_date',False)
        end_date = data.get('end_date',False)

        return "Dipartimento: %s - Dalla data: %s - Alla data: %s"%(data.get('department_name',''), 
                                                                    start_date if start_date else "Non impostata", 
                                                                    end_date if end_date else "Non impostata", )
        
    def get_total(self, value):
        ''' return a browse object for intervent for user passed
        '''
        global totals
        
        return totals.get(value,0.0)
        
    def user_intervent(self, user_id, data = None):
        ''' return a browse object for intervent for user passed
        '''
        global totals
        # TODO filter intervent to get user list (not all)
        if data is None:
            data={}
                    
        ts_pool=self.pool.get('hr.analytic.timesheet')
        if user_id: 
            domain=[('user_id','=',user_id)]
        else:
            domain=[]

        start_date = data.get('start_date',False)
        end_date = data.get('end_date',False)
        
        if start_date:
            domain.append(('date','>=',start_date))
        if end_date:
            domain.append(('date','<=',end_date))            
            
        intervent_ids=ts_pool.search(self.cr, self.uid, domain, order="date")
        time_list=ts_pool.browse(self.cr, self.uid, intervent_ids)
        
        # calculate totals:
        totals={'ore':0.0, 'operazioni':0.0,'cost':0.0,'revenue':0.0}
        for intervent in time_list:
            totals['ore'] += intervent.unit_amount or 0.0
            totals['operazioni'] += intervent.amount_operation or 0.0
            totals['cost'] += intervent.amount or 0.0
            totals['revenue'] += (intervent.account_id.price_operation or 0.0) * (intervent.amount_operation or 0.0)
        return time_list

    def user_list(self, data = None):
        ''' return a browse object for every user         
        '''
        # TODO filter intervent to get user list (not all)
        if data is None:
            data={}
                    
        if data.get('department_id', False):
            domain = [('context_department_id', '=', data.get('department_id',0))]                    
        else:
            domain = []
                
        user_ids=self.pool.get('res.users').search(self.cr, self.uid, domain)        
        return self.pool.get('res.users').browse(self.cr, self.uid, user_ids)

