###############################################################################
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
###############################################################################

import os
import sys
import logging
from tools.translate import _
from osv import fields, osv, expression
from report import report_sxw
from report.report_sxw import rml_parse
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)

dow = {0: "lun", 1: "mar", 2: "mer", 3: "gio", 4: "ven", 5: "sab", 6: "dom"}

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        ''' Parser init
        '''
        if context is None:
            context = {}
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_calendar': self.get_calendar,
            'get_filter_description': self.get_filter_description,
            'week_day': self.week_day,
            })

    def week_day(self, day, data):
        ''' Return the day of a week for day passed in month and year of wizard
        '''
        try: 
            pdate = datetime.strptime("%s-%s-%s" % (
                data.get('year',0), data.get('month',0), day), "%Y-%m-%d")
            is_festivity = "\nFES" if self.pool.get(
                'contract.employee.festivity').is_festivity(
                    self.cr, self.uid, pdate) else "" # festivity
            day_of_week = pdate.weekday()
            
            return "%s\n%s%s" % (day, dow[day_of_week], is_festivity)
        except: 
            return "" # Error return always false (so no sunday) 

    def get_filter_description(self, data):
        ''' Return string that describe wizard filter elements 
            (from data passed)
        '''
        if not data:
            return "Nessun filtro"
        else:
            return 'Dipartimento: %s - Periodo: %s-%s' % (
                data.get('department_name', 'All'),
                data.get('month', '00'), 
                data.get('year', '0000'),
                )
        
    def get_calendar(self, data=None):
        ''' Get calendar for user/mont/year passed
        '''
        if data is None:
            data = {}
        return self.pool.get('hr.analytic.timesheet').get_calendar(
            self.cr, self.uid, data)
        
class hr_analytic_timesheet(osv.osv):
    ''' Put utility function here for to be used alse from external
        > Wizard
        > Importation
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

        # Convert datetime in str:
        if type(from_date) == datetime:
            form_date = from_date.strftime("%Y-%m-%d")
        if type(to_date) == datetime:
            # Bug: this function is used from report and import
            # Report require: <= to date (datetime), 
            # Import require: < to_date (string)
            # So corrected here for use only <:
            to_date = to_date - timedelta(days=1)
            to_date = to_date.strftime("%Y-%m-%d")

        # ---------------------------------------
        # only this user_id in the from-to period
        # ---------------------------------------
        line_ids = self.search(cr, uid, [('user_id', 'in', user_ids),
            ('date', '>=', from_date), ('date', '<', to_date)])
                                              
        # -----------------------------------
        # loop all lines for totalize results                                      
        # -----------------------------------
        for line in self.browse(cr, uid, line_ids): 
            month_day = int(line.date[8:10])
            amount = line.unit_amount or 0.0
            
            # Type of hour:
            if line.account_id.is_recover:                 
                dict_ref = not_worked_recover # recover:                
            elif line.account_id.not_working:                 
                dict_ref = not_worked # absence:                 
            else:                 
                dict_ref = worked # presence

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
        
    def get_calendar(self, cr, uid, data=None, context=None):
        ''' Original function moved here from parser for calculate all database
            for report intervent
            The function is moved here as we call also from importation
        '''
        # ---------------------------------------------------------------------
        #                          Utility function: 
        # ---------------------------------------------------------------------            
        def get_block(start_date, ref_month, day_of_month, employee_work, 
                tot_hour_to_work, employee_worked_hours, 
                employee_not_worked_hours, employee_not_worked_recover_hours):
            ''' start_date = datetime element for first day of calendar
                ref_month = actual month, used to test end of month during day 
                    calc
                employee_work = dict with work hour per day (contract)
                tot_hour_to_work = list passed as totalizator of hour to work
                employee_worked_hours = dict with worked hours (intervent)
                employee_not_worked_hours = dict with not worked hours 
                    (intervent with account absence)
                employee_not_worked_recover_hours = dict with not worked hours 
                    for recover (intervent with account absence)
                
                Return: block for represent one day for one employee
                Setup default parameter as:
                [ work hour > calculated depending on employee_work
                  hour worked 
                  hour festivity 
                  status: FER = Festivity, WE= Week end, OK work + festivity >= 
                      hour to work, KO if <
                ]                  
            '''

            res = [0.0, 0.0, 0.0, "", 0.0] # default value  
            actual_date = start_date + timedelta(days = day_of_month - 1)
            wd = datetime.weekday(actual_date)

            if day_of_month == 32: # Total column:
                res[0] = tot_hour_to_work[0]                
                # total worked hours
                res[1] = employee_worked_hours[
                    32] if 32 in employee_worked_hours else 0.0
                # total not worked hours     
                res[2] = employee_not_worked_hours[
                    32] if 32 in employee_not_worked_hours else 0.0 

                # total not worked recover hours
                res[4] = employee_not_worked_recover_hours[
                    32] if 32 in employee_not_worked_recover_hours else 0.0   
                
                # worked - to work - recover (used)
                todo = res[1] - res[0] - res[4]
                
                # last column is 0 not "OK"
                res[3] = "%s\n%3.2f" % (
                    "recup." if todo >= 0 else "manca", 
                    todo) 
   
            elif actual_date.strftime("%m") == ref_month: # same month
                # test if is festivity day:
                if festivity_pool.is_festivity(
                        cr, uid, actual_date): 
                    # festivity
                    res[0] = 0.0 # no work hours
                    res[3] = "\nFES"
                else: 
                    # other day:
                    wh = employee_work[wd] if wd in employee_work else 0.0
                    res[0] = wh
                    tot_hour_to_work[0] += wh
                    #if wd in (5,6): # saturday and sunday:
                    #    res[3] = "\nW.E."
                
                # work and not work hours:
                if day_of_month in employee_worked_hours:
                    res[1] = employee_worked_hours[day_of_month]
                    
                if day_of_month in employee_not_worked_hours:
                    res[2] = employee_not_worked_hours[day_of_month]

                if day_of_month in employee_not_worked_recover_hours:
                    res[4] = employee_not_worked_recover_hours[day_of_month]
                
                # -------
                # Status:
                # -------
                if not (res[0] or res[1] or res[2] or res[4]): 
                    # all 0
                    res[3] = ""
                elif res[1] + res[2] + res[4] == res[0]:  
                    # OK
                    res[3] = "="
                elif res[1] + res[2] + res[4] < res[0]: 
                    # KO
                    res[3] = "<\nERR"
                elif res[1] + res[2] + res[4] - 10.0 > res[0]: 
                    #ERR (too much extra hours)
                    res[3] = ">\nERR"
                elif res[1] + res[2] + res[4] - 4.0 > res[0]:  
                    #WAR (much extra hours)
                    res[3] = ">\nWAR"
                elif res[1] + res[2] + res[4] > res[0]: 
                    # OK > (extra hours)
                    res[3] = ">"
                else:
                    res[3] = "???"
                   
            else: # new month
                res = ["", "", "", "", ""]                
            return res[:]

        # ----------
        # Pool used:
        # ----------
        ts_pool = self.pool.get('hr.analytic.timesheet')
        employee_pool = self.pool.get('hr.employee')
        festivity_pool = self.pool.get('contract.employee.festivity')

        # Constant used:
        day_number = {
            'mo': 0, 'tu': 1, 'we': 2, 'th': 3, 'fr': 4, 'sa': 5, 'su': 6}

        # ---------------------------------------------------------------------
        #                         DATA PARAMETERS:
        # ---------------------------------------------------------------------
        if data is None:
           data = {}

        # Common parameters:
        # Get refer for data (else take actual month):
        ref_month = "%02d" % (
            int(data.get('month', datetime.now().strftime("%m"))))
        ref_year  = "%04d" % (
            int(data.get('year', datetime.now().strftime("%Y"))))        
            
        # From wizard:
        department_id = data.get('department_id', False) # no from importation
        
        # From importation:
        importation_user_ids = data.get('user_ids', False)
                
        # ---------------
        # Variables used:
        # ---------------
        res_dict = {}
        
        start_date = datetime.strptime("%s-%s-01" % (
            ref_year, ref_month), "%Y-%m-%d")
        stop_d_1 = datetime.strptime("%04d-%02d-%s" % (
            start_date.year if start_date.month <12 else start_date.year + 1,
            start_date.month + 1 if start_date.month < 12 else 1, 
            1), "%Y-%m-%d")

        stop_date = (stop_d_1 + timedelta(days = -1)) 

        # ------------------
        # Get employee list:
        # ------------------
        if importation_user_ids: # from importation:
            # NOTE: from importation no department_id admitted
            employee_ids = employee_pool.search(
                cr, uid, [('user_id', 'in', importation_user_ids)])
            
        else: # from wizard:
            # Filter department or all:    
            if department_id: # get filter if department is present
                filter_department = [('department_id', '=', department_id)]
            else:
                filter_department = []
            employee_ids = employee_pool.search(
                cr, uid, filter_department) #, order='name')
                
        employee_proxy = employee_pool.browse(cr, uid, employee_ids)

        # ----------------------------------------------------------
        # Load all worked hours and festivity for selected employee:
        # ----------------------------------------------------------
        # Search user_id list
        user_ids = []
        for employee in employee_proxy: # sorted by name
            if employee.user_id and employee.user_id.id not in user_ids:
                user_ids.append(employee.user_id.id)
                
        # Populate worked and not worked hours:
        employee_worked_hours = {}
        employee_not_worked_hours = {}
        employee_not_worked_recover_hours = {}

        ts_pool.get_employee_worked_hours(cr, uid, user_ids, 
            start_date, stop_date, employee_worked_hours, 
            employee_not_worked_hours, employee_not_worked_recover_hours) 
        
        # ------------------
        # Create print list:
        # ------------------
        for employee in employee_proxy: # sorted by name
            if employee.user_id: # there's linked user
                
                # Load all working hour for employee
                employee_work_hours = {}
                if employee.contract_tipology_id:
                    for line in employee.contract_tipology_id.line_ids:                
                        employee_work_hours[
                            day_number[line.week_day]] = line.name
                    exist_tipology=True
                else:
                    exist_tipology=False
                    
                # Create default month loading block 
                # (after compute worked hour and absence hour)
                tot_hour_to_work = [0.0] 
                res_dict[employee.user_id.id] = ["%s\n(%s)\n%s" % (
                    employee.name, 
                    employee.department_id.name if employee.department_id else "Impostare dipartimento",
                    "" if exist_tipology else "\nImpostare orario",
                    )] + [
                        get_block(start_date,
                        ref_month,
                        item,
                        employee_work_hours,
                        tot_hour_to_work,
                        employee_worked_hours[
                            employee.user_id.id] if employee.user_id.id in employee_worked_hours else {},
                        employee_not_worked_hours[
                            employee.user_id.id] if employee.user_id.id in employee_not_worked_hours else {},
                        employee_not_worked_recover_hours[
                            employee.user_id.id] if employee.user_id.id in employee_not_worked_recover_hours else {},
                        ) for item in range(1,33)]
            else:
                pass # TODO error if there's not a user in employee    
        ris = [res_dict[k] for k in res_dict]
        ris.sort()
        return ris
        
hr_analytic_timesheet()
