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

import os
import sys
from osv import fields, osv, expression
from datetime import datetime, timedelta


class hr_analytic_timesheet(osv.osv):
    ''' Add utility to timesheet for calculare month elements
    '''
    _inherit = 'hr.analytic.timesheet'
    
    # -------------------------------------------------------------------------
    #                             Utility:
    # -------------------------------------------------------------------------
    def get_employee_worked_hours(self, cr, uid, user_ids, from_date, to_date, 
            worked, not_worked, not_worked_recover, context=None):
        ''' Search in analytic account line all employee_id.user_id that 
            has worked hour for the period
            compile worked and not worked dict with: 
                   {user_id: {day_of_month: worked}
                   {user_id: {day_of_month: not worked}
        '''
        res = {}
        
        # ---------------------------------------
        # only this user_id in the from-to period
        # ---------------------------------------
        line_ids = self.search(cr, uid, [
            ('user_id', 'in', user_ids),
            ('date', '>=', from_date.strftime("%Y-%m-%d")),
            ('date', '<=', to_date.strftime("%Y-%m-%d")),
            ])
                                              
        # -----------------------------------
        # loop all lines for totalize results                                      
        # -----------------------------------
        for line in self.browse(cr, uid, line_ids): 
            month_day = int(line.date[8:10])
            amount = line.unit_amount or 0.0
            
            if line.account_id.is_recover: 
                # recover:
                dict_ref = not_worked_recover
            elif line.account_id.not_working: 
                # absence: 
                dict_ref = not_worked
            else: 
                # presence
                dict_ref = worked

            if line.user_id.id not in dict_ref:
                dict_ref[line.user_id.id] = {}
                dict_ref[line.user_id.id][month_day] = amount
            else:    
                if month_day in dict_ref[line.user_id.id]:
                    dict_ref[line.user_id.id][month_day] += amount
                else:    
                    dict_ref[line.user_id.id][month_day] = amount
                    
            # total column:
            if 32 in dict_ref[line.user_id.id]: 
                dict_ref[line.user_id.id][32] += amount
            else:
                dict_ref[line.user_id.id][32] = amount
            # TODO update total!!!! (worked and not worked)
        return 
hr_analytic_timesheet()      
