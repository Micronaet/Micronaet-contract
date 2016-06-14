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
            'get_objects': self.get_objects,
            'get_filter_description': self.get_filter_description,
        })

    def get_filter_description(self, data = None):
        ''' Return string that describe wizard filter elements (from data passed)
        '''
        data = data or {}

        # Date:
        from_date = data.get('from_date', '/')
        to_date = data.get('to_date', '/')
        
        # Employee:
        all_department = data.get('all', False)
        department_name = data.get('department_name', '/')
        user_name = data.get('user_name', '/')
        
        # Extra:
        detailed = data.get('detailed', False) # TODO develop management
        absence_account_name = data.get('absence_account_name', '/')

        if data:
            return 'Dipartimento: %s - Utente: %s - Periodo: (%s:%s) - Tipo assenza: %s' % (
                'tutti' if all_department else department_name,
                user_name,
                from_date or '/',
                to_date or '/',
                absence_account_name,
                )
        else:
            return 'Nessun filtro'
            
    def get_objects(self, data=None):
        ''' Return list of employee
        '''
        # Pool used:
        ts_pool = self.pool.get('hr.analytic.timesheet')
        
        # -----------------------
        # Read wizard parameters:
        # -----------------------
        data = data or {}

        # Date:
        from_date = data.get('from_date', False)
        to_date = data.get('to_date', False)
        
        # Employee:
        all_department = data.get('all', False)
        department_id = data.get('department_id', False)
        user_id = data.get('user_id', False)
        
        # Extra:
        detailed = data.get('detailed', False)
        absence_account_id = data.get('absence_account_id', False)

        # --------------------------------
        # Generate domain from parameters:
        # --------------------------------
        domain = [('account_id.not_working', '=', True)] # no working account

        # Account contract:
        if absence_account_id:
            domain.append(('account_id','=',absence_account_id))

        # Employee block:
        if not all_department:
            if department_id:
                domain.append(
                    ('user_id.context_department_id', '=', department_id))                
            if user_id:
                domain.append(('user_id', '=', user_id))
            
        # Period range:
        if from_date:
           domain.append(('date', '>=', from_date))
        if to_date:
           domain.append(('date', '>=', to_date))

        # Read record:
        ts_ids = ts_pool.search(self.cr, self.uid, domain) # order
        
        # Sort record:
        ts_proxy = ts_pool.browse(self.cr, self.uid, ts_ids)
        
        res = []
        
        # Break code part:
        old = [False, False]
        total = [0, 0]
        for item in sorted(ts_proxy, key=lambda intervent:(
                intervent.user_id.name,
                intervent.account_id.name,
                intervent.date,
                )):
                
            # Startup break line:
            if old[0] == False:
                old[0] = item.user_id.id
            if old[1] == False:
                old[1] = item.account_id.id
            
            # -----------------            
            # Write total line:
            # -----------------            
            if item.user_id.id != old[0]: # check user break
                res.append(('tot_user', tuple(total))) # last previous
                # Old this element:
                old[0] = item.user_id.id
                old[1] = item.account_id.id                
                # Reset total:
                total[0] = item.unit_amount
                total[1] = item.unit_amount
            else: # check account break
                total[0] += item.unit_amount # same user
                        
                if item.account_id.id != old[1]: # break account
                    res.append(('tot_account', tuple(total))) # last previous
                    # Old this element:
                    old[1] = item.account_id.id       
                    # Reset total:
                    total[1] = item.unit_amount
                else:
                    total[1] += item.unit_amount

            # ----------------            
            # Write data line:
            # ----------------            
            res.append(('intervent', item))

        # TODO append last total    
        if not(old[0] == False):
            res.append(('tot_user', total)) # append old
        return res

