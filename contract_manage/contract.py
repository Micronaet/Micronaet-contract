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
import logging
import netsvc
import decimal_precision as dp
from osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from tools.translate import _
from tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    )


_logger = logging.getLogger(__name__)

operation_type = [
    ('lecture', 'Lecture'),
    ('hour', 'Intervent Hours'),
    ('mailing', 'Mailing'),
    ('material', 'Material in EUR'),
    ]

class account_analytic_expense_account(osv.osv):
    ''' List of account expenses (imported)
        All this record will be distributed on account.analytic.account
        present in the period selected
    '''

    _name = 'account.analytic.expense.account'
    _description = 'Analytic expense account'
    
    def get_create_code(self, cr, uid, code, name, context=None):
        ''' Search code in database, if not present create and return ID
        '''
        code_ids = self.search(cr, uid, [('code', '=', code)], context=context)
        if code_ids:
            return code_ids[0]
        return self.create(cr, uid, {
            'code': code,
            'name': name,
            }, context=context)    

    _columns = {
        'name': fields.char('Account', size=60, required=True), 
        'code': fields.char('Code', size=10, required=True),
        }

class account_analytic_expense(osv.osv):
    ''' List of account expenses (imported)
        All this record will be distributed on account.analytic.account
        present in the period selected
    '''

    _name = 'account.analytic.expense'
    _description = 'Analytic expense'

    # Scheduler event:
    def schedule_csv_accounting_movement_import(self, cr, uid, csv_file,
            delimiter, header, verbose=100):
        ''' Import movement sync with record in OpenERP
        '''
        
        _logger.info('Start import accounting movement, filee: %s' % csv_file)
        lines = csv.reader(open(os.path.expanduser(
                csv_file), 'rb'), delimiter=delimiter)
        counter = -header

        partner_pool = self.pool.get('res.partner')
        code_pool = self.pool.get('account.analytic.expense.account')
        csv_pool = self.pool.get('csv.base')
        
        # -------------------
        # Load from CSV file:
        # -------------------
        record = {}
        tot_col = 0
        for line in lines:
            try:
                # ----------------------------
                # Starting test for row check:
                # ----------------------------
                counter += 1
                if counter <= 0:
                    continue # jump header line
                if tot_col == 0: # the first time (for tot col)
                   tot_col = len(line)
                   _logger.info('Total column %s' % tot_col)
                   
                if not(len(line) and (tot_col == len(line))):
                    _logger.warning(
                        'Riga: %s Empty line of col different [%s!=%s]' % (
                            counter, tot_col, len(line)))
                    continue
                
                # --------------------------
                # Load fields from CSV file:
                # --------------------------
                causal = csv_pool.decode_string(line[0])
                series = csv_pool.decode_string(line[1])
                number = csv_pool.decode_string(line[2])
                account_code = csv_pool.decode_string(line[3])
                account_name = csv_pool.decode_string(line[4])
                contract_code = csv_pool.decode_string(line[5])
                period = csv_pool.decode_string(line[6])
                date = csv_pool.decode_date(line[7])
                amount = csv_pool.decode_float(line[8])
                department = csv_pool.decode_string(line[9])
                movement_id = csv_pool.decode_string(line[10])
                year = csv_pool.decode_string(line[11])
                
                # -----------------
                # Get extra fields:
                # -----------------
                if period:
                    date_from = "%s-%s-%s" % (
                        '2015', # TODO calculate correct
                        period[:2],
                        period[2:4],
                        )
                    date_to = "%s-%s-%s" % (
                        '2015', # TODO calculate correct
                        period[4:6],
                        period[6:8],
                        )
                else:
                    date_from = False
                    date_to = False
                        
                department_id = False # TODO
                split_type = 'contract' # TODO
                
                code_id = code_pool.get_create_code(
                    cr, uid, account_code, account_name, context=context)

                # ------------------------
                # Sync or create elements:        
                # ------------------------
                name = '%s-%s' % (movement_id, date[:4])
                data = {
                    'name': name,
                    'amount': amount,
                    'note': False,
                    'causal': causal,
                    'series': series,
                    'number': number,
                    'code_id': code_id, 
                    'date': date,
                    'date_to': date_to,
                    'date_from': date_from,
                    'year': year,
                    'split_type': split_type, 
                    'department_id': department_id,
                    }
                self.search(cr, uid, [
                    ('name', '=', name),
                    (),
                    ], context=context)
                
            except:
                _logger.error('Error import deadline')
                continue
        return True

    _columns = {
        'name': fields.char('Protocol #', size=64, required=True,
            help='ID in accounting for link the record of OpenERP'), 
        'amount': fields.float('Amount', digits=(16, 2), required=True),
        'note': fields.text('Note'),

        # Header description:
        # TODO change casual in selection?
        'causal': fields.char('Causal', size=2, required=True),
        'series': fields.char('Series', size=2, required=True),
        'number': fields.char('Document', size=12, required=True),

        # Period:
        'date': fields.date('Ref. date', required=True),
        'date_to': fields.date('To date'),
        'date_from': fields.date('From date'),
        'year': fields.char('Year', size=4),

        # Split possibilities:
        'split_type': fields.selection([
            ('all', 'All'),
            ('department', 'Department'),
            ('contract', 'Contract'),
            #('contracts', 'Contracts'),
            ], 'Split type'),
        'department_id': fields.many2one(
            'hr.department', 'Department',
            help="Department if directly associated"),
        
        'code_id': fields.many2one(
            'account.analytic.expense.account', 'Account code',
            help="Accounting code from external program"),
        #'contract_ids': fields.many2one(
        #    'account.analytic.account', 'expense_account_analitic_rel',
        #    'expense_id', 'contract_id', 'Contract',
        #    help="Contract if directly associated"),
        # TODO Not indicate contract, same as analytic lines!!
        }
account_analytic_expense()

class account_analytic_intervent_activity(osv.osv):
    ''' Activity for intervent (generic catalogation)
    '''

    _name = 'account.analytic.intervent.activity'
    _description = 'Intervent activity'

    _columns = {
        'name': fields.char('Activity', size=64, required=True,
            help="Name of the activity"),
        'department_id': fields.many2one('hr.department', 'Department',
            help="If empty is for all department / contract"),
        }
account_analytic_intervent_activity()

class product_product_extra(osv.osv):
    """ Product extra fields
    """

    _inherit = 'product.product'

    _columns = {
        'is_hour_cost': fields.boolean('Hour cost'),
        'department_id': fields.many2one('hr.department', 'Dipartimento',
            help="The department that usually has this product / service / instrument"),
        }
product_product_extra()

class hr_department_extra(osv.osv):
    """ HR department extra fields
    """

    _inherit = 'hr.department'

    _columns = {
        'inactive': fields.boolean('Inactive'),
        'for_extra_department': fields.boolean('For extra cost',
            help="If cheched all extra department cost can be assigned to the analytic account of this department"),
        'code': fields.char('Account code', size=5),
        }

    _defaults = {
        'inactive': lambda *a: False,
        'for_extra_department': lambda *a: True,
        }
hr_department_extra()

class res_city(osv.osv):
    ''' Object relation for join analytic account with city
    '''

    _inherit = "res.city"

    _columns = {
        'trip_km': fields.float('Trip km (average)', digits=(16, 2),
            help="Km average for headquarter"),
        'tour_km': fields.float('Tour km (average)', digits=(16, 2),
            help="Km average for tour in the city"),
        }
res_city()

class res_city_relation(osv.osv):
    ''' Object relation for join analytic account with city
    '''
    _name = "res.city.relation"
    _description = "City relation"

    # -------------------------------------------------------------------------
    #                          ON CHANGE PROCEDURE:
    # -------------------------------------------------------------------------
    def on_change_city_compute_std_cost(self, cr, uid, ids, city_id,
            context=None):
        ''' If city is changed get default value for trip and tour cost from
            res.city
        '''
        res = {'value': {'trip_km': 0.0, 'tour_km': 0.0}}

        if not city_id: # empty value
           return res

        city_pool = self.pool.get("res.city")
        city_proxy = city_pool.browse(cr, uid, [city_id], context=context)[0]

        res['value']['trip_km'] = city_proxy.trip_km or 0.0
        res['value']['tour_km'] = city_proxy.tour_km or 0.0
        return res

    # TODO table to migrate 'account_city_rel', 'account_id', 'city_id'
    _columns = {
        'name': fields.many2one('res.city', 'City',
            help="When city filtered is enabled this field contains list of cities available"),
        'trip_km': fields.float('Trip km (average)', digits=(16, 2),
            help="Km average for headquarter"),
        'tour_km': fields.float('Tour km (average)', digits=(16, 2),
            help="Km average for tour in the city"),
        'contract_id': fields.many2one('account.analytic.account', 'Contract'),
        }
res_city_relation()

class account_analytic_account_extra_fields(osv.osv):
    ''' Add extra field to object
    '''

    _inherit = "account.analytic.account"

    # Utility function (temp function):
    def copy_filtered_city_ids(self, cr, uid, context=None):
        ''' Temp function for migrate city from m2m to o2m fields
        '''
        city_pool = self.pool.get('res.city.relation')

        # 1. Create, for first time, the list of city in contract
        contract_ids = self.search(cr, uid, [
            ('location_filtered','=',True)], context=context)
        for contract in self.browse(cr, uid, contract_ids, context=context):
            if not contract.filter_city_ids:
                for c in contract.filtered_city_ids:
                    city_pool.create(cr, uid, {
                        'name': c.id,
                        'contract_id': contract.id}, context=context)

        # 2. Update Km from city to contract city
        city_ids = city_pool.search(cr, uid, [], context=context)
        #["|",('tour_km','!=',False),('trip_km','!=',False)], context=context)
        for city in city_pool.browse(cr, uid, city_ids, context=context):
            data = {}
            if not city.tour_km:
                data['tour_km'] = city.name.tour_km
            if not city.trip_km:
                data['trip_km'] = city.name.trip_km

            if data:
                city_pool.write(cr, uid, [city.id], data, context=context)
        return True

    # Utility function:
    def get_km_from_city_trip(self, cr, uid, account_id, trip_type, city_id,
            context=None):
        ''' Compute Km for given city_id, account_id, trip_type (better put here the list not in wizard
        '''

        if not (account_id and trip_type and city_id): # must exist all
            return 0.0

        account_proxy=self.browse(cr,uid, [account_id], context=context)[0]

        trip = 0.0
        tour = 0.0
        # search the value in account.analytic.account (if there's cities set)
        for city in account_proxy.filter_city_ids:
            if city.name.id == city_id:
                trip = city.trip_km
                tour = city.tour_km
                break

        # search the value in res.city (used for ex if there's not cities set)
        if (not trip) or (not tour):
            res_city_ids = self.pool.get("res.city").search(
                cr, uid, [('id','=',city_id)], context=context)
            if res_city_ids:
                res_city_proxy = self.pool.get("res.city").browse(
                    cr, uid, res_city_ids, context=context)[0] # 1st only
                trip = trip if trip else res_city_proxy.trip_km
                tour = tour if tour else res_city_proxy.tour_km

        # compute according to the trip type:
        if trip_type == 'trip':
            return trip or 0.0
        elif trip_type == 'tour':
            return tour or 0.0
        elif trip_type == 'all':
            return (trip or 0.0) + (tour or 0.0)
        else:
            return 0.0

    def _function_total_amount_operation(self, cr, uid, ids, name, arg,
            context=None):
       ''' Calculate from analytic movement total amount of operation
       '''
       res = {}
       for i in ids:
           res[i] = {}

       find_line_ids = self.pool.get('hr.analytic.timesheet').search(
           cr, uid, [('account_id', 'in', ids)])
       for line in self.pool.get('hr.analytic.timesheet').browse(
               cr, uid, find_line_ids, context=context):
           if 'actual_amount_operation' in res[line.account_id.id]:
              res[line.account_id.id][
                  'actual_amount_operation'] += line.amount_operation
           else:
              res[line.account_id.id][
                  'actual_amount_operation'] = line.amount_operation
           if line.account_id.total_amount_operation:
              res[line.account_id.id][
                  'actual_perc_amount_operation'] = 100.0 * res[
                      line.account_id.id][
                          'actual_amount_operation'
                          ] / line.account_id.total_amount_operation
           else:
              res[line.account_id.id]['actual_perc_amount_operation'] = 0.0
       return res

    _columns = {
        'total_amount': fields.float('Total amount', digits=(16, 2)),
        'department_id': fields.many2one('hr.department', 'Dipartimento'),
        'is_contract': fields.boolean('Is contract',
            help="Check if this account is a master contract (or subvoice)"),
        'is_recover': fields.boolean('Is recover',
            help="Check this if the contract is a recovery for extra hour worked (used in report timesheet for calculate recover hour for next month)"),
        'has_subcontract': fields.boolean('Has subcontract',
            help="Check if this account is a master contract (or subvoice)"),
        'default_operation': fields.selection(operation_type,
            'Default operation', select=True),
        'total_amount_operation': fields.float('Total amount operation',
            digits=(16, 2)),
        'price_operation': fields.float('Price per operation', digits=(16, 2)),
        'actual_amount_operation': fields.function(
            _function_total_amount_operation, method=True, type='float',
            string='Actual total operation ', store=False, multi=True),
        'actual_perc_amount_operation': fields.function(
            _function_total_amount_operation, method=True, type='float',
            string='Actual total operation ', store=False, multi=True),
            # TODO solution to store false?

        'location_filtered': fields.boolean('City filtered',
            help="If true this account has a shot list of cities"),

        # TODO TO REMOVE!
        'filtered_city_ids': fields.many2many('res.city', 'account_city_rel',
            'account_id', 'city_id', 'City',
            help="When city filtered is enabled this field contains list of cities available"),

        'filter_city_ids': fields.one2many(
            'res.city.relation', 'contract_id', 'City element',
            help="When city filtered is enabled this field contains list of cities available"),

        'commercial_rate': fields.float('% Commercial rate', digits=(16, 2),
            help="% of invoice value for commercial value"),
        'general_rate': fields.float('% General rate', digits=(16, 2),
            help="% of invoice value for general value"),
        'not_working': fields.boolean('Not working',
            help="All intervent to this contract are not working elements (like festivity, permission etc.)"),
        }

    _defaults = {
        'is_contract': lambda *a: True,
        'is_recover': lambda *a: False,
        }
account_analytic_account_extra_fields()

class account_analytic_line_extra_fields(osv.osv):

    _inherit ='account.analytic.line'

    _columns = {
        'extra_analytic_line_timesheet_id': fields.many2one(
            'hr.analytic.timesheet', 'Timesheet generator',
            ondelete='cascade'),
        'import_type': fields.char('Import type', size=1,
            help="For import invoice from account program, I for invoice, L for line"),
        'activity_id': fields.many2one('account.analytic.intervent.activity',
            'Activity'),
        'mail_raccomanded': fields.boolean('Is raccomanded',
            help="Mail is a raccomanded"),

        # Expense:
        'expense_id': fields.many2one('account.analytic.expense', 'Expense',
            ondelete='cascade'),
        }

    _defaults = {
        'import_type': lambda *a: False,
        }
account_analytic_line_extra_fields()

class hr_analytic_timesheet_extra_fields(osv.osv):

    _inherit ='hr.analytic.timesheet'

    _columns = {
        'extra_analytic_line_ids': fields.one2many(
            'account.analytic.line', 'extra_analytic_line_timesheet_id',
            'Extra analitic entry'),
        'city_id': fields.many2one('res.city', 'Località'),
        'location_site': fields.char('Location', size=50,
            help="Location of intervent"),
        'operation': fields.selection(operation_type,'operation', select=True),
        'amount_operation': fields.float('amount operation', digits=(16, 2)),
        'amount_operation_etl': fields.float('amount operation ETL',
            digits=(16, 2)),
        'error_etl': fields.boolean('Error ETL'),
        'intervent_annotation': fields.text('Note'),
        'department_id': fields.related('account_id','department_id',
            type='many2one', relation='hr.department', string='Department'),
        }

    _defaults = {
        'error_etl': lambda *a: False,
        }
hr_analytic_timesheet_extra_fields()

class hr_analytic_timesheet_stat(osv.osv):
    """ HR analytic timesheet statistic for dashboard """

    _name='hr.analytic.timesheet.stat'
    _description = 'HR analytic stat'
    _auto = False # no creation of table
    _rec_name = 'user_id'
    #_order_by = 'date desc'

    _columns = {
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'date': fields.date('Date'),
        'unit_amount': fields.float('Tot. hour', digits=(16, 2)),
        'total': fields.integer('Total')
        }

    def init(self, cr):
        """
        initialize the sql view for the stats
        cr -- the cursor
        SELECT hr.id, a.id
        FROM hr_analytic_timesheet hr
        JOIN account_analytic_line a
        ON (hr.line_id = a.id)
        """
        cr.execute("""
            CREATE OR REPLACE VIEW hr_analytic_timesheet_stat AS
                SELECT
                    MIN(account.id) AS id,
                    account.user_id AS user_id,
                    account.date,
                    SUM(account.unit_amount) AS unit_amount,
                    COUNT(*) AS total
                FROM
                    hr_analytic_timesheet hr
                    JOIN
                    account_analytic_line account
                    ON (hr.line_id = account.id)
                GROUP BY
                    account.date, account.user_id
                ORDER BY
                    account.date DESC;
           """)
hr_analytic_timesheet_stat()

# Intervent super department:
class account_analytic_superintervent_group(osv.osv):
    ''' Super invervent grouped, first step for divide total of hours (costs)
        on active account / contract
    '''

    _name='account.analytic.superintervent.group'
    _description = 'Intervent on department grouped'

    def unlink(self, cr, uid, ids, context=None):
        ''' Delete manually the analytic line create by timesheet entry
            Let super method delete cascate on timesheet
            >to correct the problem that timesheet doesn't delete analytic line
        '''
        line_ids = []
        for group in self.browse(cr, uid, ids, context=context):
            if group.timesheet_ids:  # analytic line to delete:
               line_ids += [item.line_id.id for item in group.timesheet_ids]
        res = osv.osv.unlink(
            self, cr, uid, ids, context=context) # no super call
        # delete all line analytic:
        if line_ids:
            self.pool.get('account.analytic.line').unlink(
                cr, uid, line_ids, context=context)
        return res

    _columns = {
        'name': fields.char('Description of group', size=64, required=True,
            help="Just few word to describe intervent"),
        'user_id':fields.many2one('res.users', 'User', required=True,
            help="Must have an employee linket and a product"),
        'employee_id':fields.many2one('hr.employee', 'Employee',
            help="Get from user"),
        'department_id': fields.many2one('hr.department', 'Department',
            help="If empty is for all department / contract"),
        'quantity': fields.float('Quantity', digits=(16, 2), required=True,
            help="total hour of period"),
        'date': fields.date('Date', required=True,
            help="Last date of the period, for define the valuation of the costs"),
        }
account_analytic_superintervent_group()

class account_analytic_superintervent(osv.osv):
    ''' Intervent element that cannot assign to a particular account / contract
        This intervent are grouped by a wizard to get a total hour for
        department at the end of a period (ex. month) and after divider on
        active contract of the deparment (as a hr.analytic.timesheet)
    '''

    _name = 'account.analytic.superintervent'
    _description = 'Intervent on department'

    # on_change event:
    def on_change_extra_department(self, cr, uid, ids, extra_department,
            context=None):
        ''' On change event, if extra_department is set to True,
            delete department
        '''
        if extra_department:
           return {'value': {'department_id': False, }}
        return True

    # override ORM actions:
    def unlink(self, cr, uid, ids, *args, **kwargs):
        for superintervent in self.browse(cr, uid, ids):
            if superintervent.group_id:
                raise osv.except_osv(
                    _('Operation Not Permitted !'),
                    _('You can not delete a superintervent that is yet grouped. I suggest to delete group before.'))

        return super(account_analytic_superintervent, self).unlink(
            cr, uid, ids, context=context) # *args, **kwargs)

    _columns = {
        'name': fields.char('Short description', size=64, required=True,
            help="Just few word to describe intervent"),
        'user_id': fields.many2one('res.users', 'User', required=True,
            help="Must have an employee linket and a product"),
        'department_id': fields.many2one('hr.department', 'Department'),
        'extra_department': fields.boolean('Extra department',
            help="If super intervent is extra department the cost is divided on all contract"),
        'quantity': fields.float('Quantity', digits=(16, 2), required=True),
        'date': fields.date('Date', required=True),
        #'extra_ids':fields.one2many('account.analytic.extra.wizard', 'wizard_id', 'Extra'), # TODO (extra costs!!)
        #'city_id':fields.many2one('res.city', 'Località'),
        'intervent_annotation': fields.text('Note',
            help="Long description of the intervent"),
        'group_id': fields.many2one('account.analytic.superintervent.group',
            'Group generated', ondelete="set null",
            help="If present the super intervent is yet grouped for a future division, if group is deleted intervet return on a previous state"),
        }

    _defaults = {
        'extra_department': lambda *a: False,
        'date': lambda *a: datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        }
account_analytic_superintervent()

class hr_analytic_timesheet_extra_fields(osv.osv):
    ''' Add extra many2one fields to analytic timesheet items
        (create a link to the group that create this entries)
    '''

    _inherit ='hr.analytic.timesheet'

    _columns = {
        'superintervent_group_id':fields.many2one(
            'account.analytic.superintervent.group', 'Super intervents',
            ondelete="cascade",
            help="Super intervent group that generate this analytic line, deleting a group delete all analytic line created"),
        }
hr_analytic_timesheet_extra_fields()

class account_analytic_superintervent_group(osv.osv):
    ''' Add extra relation fields
    '''

    _inherit='account.analytic.superintervent.group'

    _columns = {
        'superintervent_ids':fields.one2many('account.analytic.superintervent',
             'group_id', 'Super intervent',
             help="List of interven that generate this entry"),
        'timesheet_ids':fields.one2many('hr.analytic.timesheet',
            'superintervent_group_id', 'Timesheet line created',
            help="List of analytic line / timesheet line that are created from this group"),
        }
account_analytic_superintervent_group()

class account_analytic_expense(osv.osv):
    ''' *many fields added after
    '''

    _inherit = 'account.analytic.expense'

    _columns = {
        'analytic_line_ids': fields.one2many(
            'account.analytic.line', 'expense_id', 'Analytic line',
            help="Analytic line child of this expense"),
        }
account_analytic_expense()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
