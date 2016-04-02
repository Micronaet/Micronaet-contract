# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>) 
#    
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
#############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
import time

type_selection = [
    ('product', 'Material'),
    ('service', 'Use / Tools'),
    ('invoice', 'Invoice for account'),
    ] # NOTE invoice was added but not very correct
    
operation_type = [
    ('lecture', 'Lecture'),
    ('hour', 'Intervent Hours'),
    ('mailing', 'Mailing'),
    ]
    
trip_type = [
    ('trip', '1 Trip only'),
    ('trip2', '2 Trip only'),
    ('tour', 'Tour only'),
    ('all', 'All 1 (1 tour + trip)'),
    ('all2', 'All 2 (2 tour + trip)'),
    ]
    
vehicle_type = [
    ('car', 'Car'),
    ('moto', 'Moto / Scooter'),
    ('camion', 'Camion'),
    ]

class account_analytic_intervent_type(osv.osv):
    ''' Type of intervent: used to setup Journal for sale or tools
    '''
    _name = "account.analytic.intervent.type"
    
    _columns = {
        'name': fields.selection(
            type_selection,'Type', select=True), 
        'journal_id': fields.many2one(
            'account.analytic.journal', 'Journal', required=True),
        }
account_analytic_intervent_type()

class account_analytic_intervent_extra_product(osv.osv_memory):
    ''' osv_memory to include extra product on intervent
    '''
    _name = "account.analytic.extra.wizard"

    def on_change_type_get_uom(self, cr, uid, ids, type_id, context=None):
        ''' Search default uom for product passed
        '''
        return {'value': {'product_id':False, 'uom_id':False, 'quantity':0.0},}

    def on_change_product_get_uom(self, cr, uid, ids, product_id, context=None):
        ''' Search default uom for product passed
        '''
        res={'value': {'uom_id': False, 'quantity':0.0},}
        if product_id:
           product_proxy=self.pool.get('product.product').browse(cr, uid, product_id)
           res['value']={'uom_id': product_proxy.uom_id.id}
        return res

    _columns = {
         'product_id': fields.many2one(
             'product.product', 'Product', required=True),
         'uom_id': fields.many2one(
             'product.uom', 'UOM'),
         'quantity': fields.float(
             'Quantity', digits=(16, 2), required=True),
         'type': fields.selection(
             type_selection,'Type', select=True), 
         # search in account.analytic.intervent.type
    }     
account_analytic_intervent_extra_product()

class account_analytic_intervent_wizard(osv.osv_memory):
    ''' Filter user, department, account before inserting wizard 
    '''    
    _name = "account.analytic.intervent.wizard"
    _rec_name = "user_id"

    dow = {
        0: "Lun", 
        1: "Mar", 
        2: "Mer",
        3: "Gio",
        4: "Ven",
        5: "Sab",
        6: "Dom",
        }
           
    # Utility function (private for internal use)
    def _get_journal_from_type(self, cr, uid, type_id, context=None):
        ''' Get Analytic Journal start from type of expense:
            search in journal list the one setted up with this type
        '''
        journal_ids = self.pool.get(
            "account.analytic.intervent.type").search(cr, uid, [
                ('name','=',type_id)], context=context)
        journal_id = self.pool.get(
            "account.analytic.intervent.type").read(
                cr, uid, journal_ids, context=context)
        return journal_id[0]['journal_id'][0]    
        # TODO error if not presen the journal setted up

    def _create_line(self, cr, uid, product_id, quantity, company_id, unit, 
            journal_id, name, date, account_id, user_id, intervent_id=0, 
            intervent_annotation=False, operation=False,
            amount_operation=False, city_id=False, activity_id=False, 
            mail_raccomanded=False, location_site=False, 
            super_intervent=False, total_trip_km=0.0, vehicle_type=False,
            context=None):                              

        ''' Create analytic line
            used for Intervent element and Expense elements too
        '''
        # start record populate:
        intervent_data = {
            'user_id': user_id,
            'account_id': account_id,
            'name': name,
            'product_id': product_id,
            'journal_id': journal_id,
            'unit_amount': quantity,
            'date': date,
            'city_id': city_id,
            'operation': operation , 
            'amount_operation': amount_operation,
            'activity_id': activity_id,
            'location_site': location_site,
            'mail_raccomanded': mail_raccomanded,
            'total_trip_km': total_trip_km,
            }

        # ---------------------------------------------------------------------
        #                        Normal intervent:                        
        # ---------------------------------------------------------------------
        if intervent_id and not super_intervent: 
            # if has intervent_id is an extra cost:
            analytic_line_proxy = self.pool.get('account.analytic.line')
            intervent_data['extra_analytic_line_timesheet_id'] = intervent_id
            
        # ---------------------------------------------------------------------
        #                         Super intervent:                        
        # ---------------------------------------------------------------------
        elif intervent_id and super_intervent:   
            # if has intervent_id and super_intervent, is a timesheet linked to group intervent
            analytic_line_proxy = self.pool.get('hr.analytic.timesheet')
            # Add extra field for intervent
            intervent_data['intervent_annotation'] = intervent_annotation 
            # Link to group:
            intervent_data['superintervent_group_id'] = intervent_id 
            
        else: # use Timesheet:
           analytic_line_proxy = self.pool.get('hr.analytic.timesheet')
           # Add extra field for intervent:
           intervent_data['intervent_annotation'] = intervent_annotation 

        ## TODO vedere perchè non funziona con il giornale impostato su SALE
        amount_value = analytic_line_proxy.on_change_unit_amount(
            cr, uid, False, product_id, quantity, company_id, unit=unit, 
            journal_id=journal_id, context=context)['value']
        intervent_data.update(amount_value)                 
        return analytic_line_proxy.create(
            cr, uid, intervent_data, context=context)

    def create_superintervent_function(self,cr, uid, item_list, context=None):
        '''Create super intervent function (used from wizard super intervent)
           Get a item parameter: list of (id, uid, data, q, contract_ids) element
           create a timesheet element linked to the group element passed           
        '''
        try: # Try to create hr.analytic.tymesheet or account.analytic.account
            for item in item_list:
                # Create Intervent:
                employee_ids=self.pool.get('hr.employee').search(cr, uid, [('user_id','=',item[1])])
                
                if not employee_ids: # mandatory field
                   raise osv.except_osv("Error", "No product defined for employee (or Journal)")                                                          
                
                employee_proxy=self.pool.get('hr.employee').browse(cr, uid, employee_ids[0])
                    
                for account in self.pool.get(
                        'account.analytic.account').browse(cr,uid,item[4]): 
                    # contract_ids
                    # Intervent report:
                    intervent_id = self._create_line(
                        cr, 
                        uid, 
                        employee_proxy.product_id.id,
                        item[3], # Q.
                        employee_proxy.user_id.company_id.id, 
                        False, 
                        employee_proxy.journal_id.id,
                        account.name,  # contract name
                        item[2], # date 
                        account.id,    # contract ID
                        item[1], # uid 
                        operation=False,
                        amount_operation=0.0,
                        city_id=False,
                        intervent_annotation="General timesheet cost",
                        intervent_id=item[0], 
                        super_intervent=True,                        
                        context=context)
        except: 
            raise osv.except_osv("Error", "Unable to create intervent!")
        return

    # Wizard button function:
    def create_intervent_function(self,cr, uid, ids, context=None):
        '''Wizard to get default start value before insert intervent:
           get uid, department_id, account
           create intervent
           put default elements and lock values           
        '''
        # Get data from wizard:
        # Create Intervent:
        item_wizard=self.browse(cr, uid, ids)[0]
        employee_ids=self.pool.get('hr.employee').search(cr, uid, [('user_id','=',item_wizard.user_id.id)])
        
        if not employee_ids: # mandatory field
           raise osv.except_osv("Error", "No product defined for employee (or Journal)")                                                                   

        try: # Try to create hr.analytic.tymesheet or account.analytic.account
            employee_proxy=self.pool.get('hr.employee').browse(cr, uid, employee_ids[0])
            company_id = item_wizard.user_id.company_id.id
            account_id = item_wizard.account_analytic_id.id
            
            # -----------------------------------------------------------------
            #                          Vacancy intervent:
            # -----------------------------------------------------------------
            if item_wizard.range_vacancy: # Vacancy range:
                from datetime import datetime, timedelta
                
                from_date = datetime.strptime(item_wizard.date, "%Y-%m-%d")
                to_date = datetime.strptime(item_wizard.to_date, "%Y-%m-%d")
                days = (to_date - from_date).days
                if days <= 0:
                    raise osv.except_osv("Error", "From date must be < To date!")                

                day_2_number = {'mo':0,'tu':1,'we':2,'th':3,'fr':4,'sa':5,'su':6}
                #day_2_number = {0:'mo',1:'tu',2:'we',3:'th',4:'fr',5:'sa',6:'su'}
                timesheet_worked = dict(
                    (day_2_number[item.week_day], item.name) for item in employee_proxy.contract_tipology_id.line_ids)
                    
                for day in range(0, days + 1):
                    ref_day = from_date + timedelta(days=day)
                    date = ref_day.strftime("%Y-%m-%d") # item_wizard.date  # From date to date 
                    wd = ref_day.weekday() #day_2_number(ref_day.weekday())
                    if wd not in timesheet_worked:
                        continue # day not created
                    quantity = timesheet_worked[wd] #8             # Hours (item_wizard.quantity)
                    
                    intervent_id = self._create_line( # Intervent report:
                        cr, 
                        uid, 
                        employee_proxy.product_id.id,
                        quantity,
                        company_id, 
                        False, 
                        employee_proxy.journal_id.id,
                        item_wizard.account_analytic_id.name,                                 
                        date, 
                        account_id,
                        item_wizard.user_id.id,
                        operation=item_wizard.operation,
                        amount_operation=item_wizard.amount_operation,
                        city_id=item_wizard.city_id.id,
                        intervent_annotation=item_wizard.intervent_annotation,
                        activity_id=item_wizard.activity_id.id,
                        mail_raccomanded=item_wizard.mail_raccomanded,
                        location_site=item_wizard.location_site,
                        context=context,
                        )

            # -----------------------------------------------------------------
            #                        Normal intervent:
            # -----------------------------------------------------------------
            else: # Normal intervent
                date = item_wizard.date        
                intervent_id = self._create_line( # Intervent report:
                    cr, 
                    uid, 
                    employee_proxy.product_id.id,
                    item_wizard.quantity,
                    company_id, 
                    False, 
                    employee_proxy.journal_id.id,
                    item_wizard.account_analytic_id.name,                                 
                    date, 
                    account_id,
                    item_wizard.user_id.id,
                    operation=item_wizard.operation,
                    amount_operation=item_wizard.amount_operation,
                    city_id=item_wizard.city_id.id,
                    intervent_annotation=item_wizard.intervent_annotation,
                    activity_id=item_wizard.activity_id.id,
                    mail_raccomanded=item_wizard.mail_raccomanded,
                    location_site=item_wizard.location_site,
                    total_trip_km=item_wizard.total_trip_km, # Add KM 
                    vehicle_type= item_wizard.vehicle_type,
                    context=context,
                    )

            # -----------------------------------------------------------------
            #                       Create expenses:            
            # -----------------------------------------------------------------
            for expense in item_wizard.extra_ids:
                expense_id = self._create_line(
                    cr, 
                    uid, 
                    expense.product_id.id, 
                    expense.quantity, 
                    company_id, 
                    False,
                    self._get_journal_from_type(
                        cr, uid, expense.type, context=context), 
                    expense.product_id.name,
                    date, 
                    account_id,
                    item_wizard.user_id.id,
                    intervent_id=intervent_id, 
                    context=context,
                    )
 
            # -----------------------------------------------------------------
            #                        KM cost for car:
            # -----------------------------------------------------------------
            # Is set an extra cost for cars trip: # TODO correct???????????????
            if item_wizard.trip_type and item_wizard.product_id: 
                # Manually creation for the expense:
                total_km_for_trip = self.pool.get(
                    'account.analytic.account').get_km_from_city_trip(
                        cr, uid, account_id, item_wizard.trip_type,
                        item_wizard.city_id.id, context=context)
                expense_id = self._create_line(
                    cr, 
                    uid, 
                    item_wizard.product_id.id, 
                    total_km_for_trip, 
                    company_id, 
                    False,
                    self._get_journal_from_type(
                        cr, uid, 'service', context=context), 
                    item_wizard.product_id.name,
                    date, 
                    account_id,
                    item_wizard.user_id.id,
                    intervent_id=intervent_id, 
                    context=context,
                    )
        except: 
            raise osv.except_osv(
                "Error", 
                "Unable to create intervent or expences!")

        return {'type': 'ir.actions.act_window_close'} # Close the window     
        #TODO togliere la action di sotto
               
    # ON CHANGE PROCEDURE: ####################################################
    def on_change_like_last(self, cr, uid, ids, like_last, context=None):
        ''' Search last intervent inserted and use that user_id and date for
            this one, elsewhere use actual ID and today date
        '''
        res={}
        res['value']= {}
        res['domain']={}
        res['domain']['account_analytic_id'] = [
            ('is_contract', '=', True),
            ('type', '=', 'normal'),
            ('state', '=', 'open')]
        
        if like_last:        
            # get last ID, max(id) of analytic line: 
            cr.execute("SELECT max(id) FROM hr_analytic_timesheet WHERE create_uid=%s",(uid,))
            item_id = cr.fetchone()[0]
            
            if not item_id:
                return res # if not present last insert do nothing

            hr_analytic_proxy = self.pool.get('hr.analytic.timesheet').browse(
                cr, uid, item_id, context=context)
            
            res['value']['user_id'] = hr_analytic_proxy.user_id.id #record_account_id[1]
            res['value']['date'] =  hr_analytic_proxy.date
            res['value']['account_analytic_id'] = hr_analytic_proxy.account_id.id
            res['value']['quantity'] = hr_analytic_proxy.unit_amount
            res['value']['city_id'] = hr_analytic_proxy.city_id.id
            res['value']['location_site'] = hr_analytic_proxy.location_site
            res['value']['operation'] = hr_analytic_proxy.operation
            res['value']['amount_operation'] = hr_analytic_proxy.amount_operation
            res['value']['activity_id'] = hr_analytic_proxy.activity_id.id
            res['value']['mail_raccomanded'] = hr_analytic_proxy.mail_raccomanded
            res['value']['department_id'] = hr_analytic_proxy.department_id.id

            res['domain']['account_analytic_id'] += [
                ('department_id', '=', hr_analytic_proxy.department_id.id)]
        else:   
            res['value']['user_id'] = uid
            res['value']['date'] = time.strftime('%Y-%m-%d')
            res['value']['account_analytic_id'] = False   
            res['value']['quantity'] = 0.0
            res['value']['city_id'] = False
            res['value']['location_site'] = False
            res['value']['operation'] = False
            res['value']['amount_operation'] = 0.0
            res['value']['activity_id'] = False
            res['value']['mail_raccomanded'] = False

            # search department for that user logged
            cr.execute("SELECT id, context_department_id FROM res_users WHERE id=%s", (uid,))
            record_id = cr.fetchone()
            res['value']['department_id'] = record_id[1]

            # set the filter on contract according to department
            if record_id[1]:
               res['domain']['account_analytic_id'] += [
                   ('department_id', '=', record_id[1])]
        return res
        
    def on_change_user_name(self, cr, uid, ids, user_id, department_id, 
            like_last, context=None):
        ''' Search default department according to user name
            (first filter)
        '''
        res = {
            'value': {},
            'domain': {},
            }
        # standard filter:
        res['domain']['account_analytic_id'] = [
            ('is_contract','=',True),
            ('type','=','normal'),
            ('state','=','open'),
            ]

        if user_id:
           user_proxy=self.pool.get('res.users').browse(cr, uid, user_id)
           res['value']['department_id'] = user_proxy.context_department_id.id
           
           #if not like_last:
           #    res['value']['account_analytic_id']=False
               
           # if department of user != actual dept then reset (else keep information
           # because contract is of this dept.
           if user_proxy.context_department_id.id != department_id:                             
               res['value']['account_analytic_id'] = False   
               #res['value']['quantity'] = 0.0
               res['value']['city_id'] = False
               res['value']['location_site'] = False
               res['value']['operation'] = False
               res['value']['amount_operation'] = 0.0
               res['value']['activity_id'] = False
               res['value']['mail_raccomanded'] = False
           
           res['domain']['account_analytic_id'] += [
               ('department_id', '=', user_proxy.context_department_id.id)]
               
        else:
           if not like_last:
               res['value']['account_analytic_id']=False
        return res

    def on_change_department(self, cr, uid, ids, department_id, like_last, context=None):
        ''' Search default department according to user name
            (first filter)
        '''
        res={'domain': {}, 'value':{},}
        # standard filter:
        res['domain']['account_analytic_id'] = [
            ('is_contract','=',True),
            ('type','=','normal'),
            ('state','=','open'),
            ]

        res['value']['account_analytic_id'] = False   
        res['value']['city_id'] = False
        res['value']['location_site'] = False
        res['value']['operation'] = False
        res['value']['amount_operation'] = 0.0
        res['value']['activity_id'] = False
        res['value']['mail_raccomanded'] = False

        if department_id:
           res['domain']['account_analytic_id'] += [
               ('department_id', '=', department_id)]
         
        return res

    def on_change_date_get_weekday(self, cr, uid, ids, date, context=None):
        ''' get date and set day of week 
        '''
        from datetime import datetime        
        try:
            wk = self.dow[datetime.strptime(date, "%Y-%m-%d").weekday()]            
            return {'value':{'week_day': wk},}
        except:
            return {'value':{'week_day': 'ERR'},} # return error
    
    def onchange_range_vacancy(self, cr, uid, ids, range_vacancy, 
            department_id, context=None):
        ''' If checked change domain for contact for not_work elements
        '''
        res = {'domain': {}}
        if range_vacancy:
            res['domain']['account_analytic_id'] = [('not_working','=',True)]
        else:
            res['domain']['account_analytic_id'] = [('state','=','open')]
            if department_id:
               res['domain']['account_analytic_id'].append(
                   ('department_id','=',department_id))
            res['value']={}
            res['value']['account_analytic_id']=False
        return res            
        
    def on_change_contract(self, cr, uid, ids, account_analytic_id, 
            context=None):
        ''' Search default type of operation for contract and put value in operation
            resetting amount import
        '''
        res = {
            'value': {}, 
            'domain': {},
            }

        if account_analytic_id: 
            contract_proxy=self.pool.get('account.analytic.account').browse(
                cr, uid, account_analytic_id)
            res['value'] = {
                'operation': contract_proxy.default_operation, 
                'amount_operation': 0.0,
                }
            if contract_proxy.location_filtered:
               res['domain']['city_id'] = [
                   ('id', 'in', [
                       item.name.id for item in contract_proxy.filter_city_ids
                       ])] 
               # NOTE: not use: res.city.relation for city_id field pfor when there's not city setted up
            else:   
               res['domain']['city_id'] = [] # all contract
               #res['value']['total_trip_km'] = 0.0
            # TODO filter for operation (so no change)?
        return res

    def onchange_destination_km(self, cr, uid, ids, trip_type, city_id,
            account_analytic_id, context=None):
        ''' Calculate Km for this intervent
        '''
        res = {'value': {'total_trip_km': 0.0}}
        
        if not(trip_type and city_id and account_analytic_id):
            return res # do nothing
            
        # Check if city is in contract (may be different Km value):
        account_pool = self.pool.get('account.analytic.account')
        
        contract_proxy = account_pool.browse(
            cr, uid, account_analytic_id, context=context)
        trip_km = 0.0
        tour_km = 0.0    
        for city in contract_proxy.filter_city_ids:
            if city_id == city.name.id:
                trip_km = city.trip_km
                tour_km = city.tour_km
                
        # Check in city record:                
        if not trip_km:
            city_pool = self.pool.get('res.city')
            city_proxy = city_pool.browse(cr, uid, city_id, context=context)
            trip_km = city_proxy.trip_km
            if not tour_km: # contract more power
                tour_km = city_proxy.tour_km
                        
        if trip_type == 'all': # with 1 tour
            total_trip_km = trip_km + tour_km
        elif trip_type == 'all2': # with 2 tour
            total_trip_km = trip_km * 2 + tour_km
        elif trip_type == 'trip': # 1 trip
            total_trip_km = trip_km
        elif trip_type == 'trip2': # 2 trip
            total_trip_km = trip_km * 2
        elif trip_type == 'tour':
            total_trip_km = tour_km
        else: 
            return res    
        res['value']['total_trip_km'] = total_trip_km
        return res
        
    def on_change_hours(self, cr, uid, ids, quantity, operation, amount_operation, context=None):
        ''' If operation if per hours copy the same value
        '''
        res={'value': {},
            }
        if not amount_operation: # only if not setted up
           if operation=="hour":
              res['value']={'amount_operation': quantity, }
        return res

    _columns = {
        'user_id':fields.many2one('res.users', 'User', required=True),  
        'department_id': fields.many2one('hr.department', 'Department', 
            required=False),
        'account_analytic_id': fields.many2one('account.analytic.account', 
            'Contract', required=True),
        'quantity': fields.float('Quantity', digits=(16, 2),),
        'extra_ids':fields.one2many('account.analytic.extra.wizard', 'wizard_id', 'Extra'),
        'date': fields.date('Date', required=True),
         
        # location cost:
        # NOTE: not use: res.city.relation for city_id field pfor when there's not city setted up
        'city_id':fields.many2one('res.city', 'Località'),
        'trip_type':fields.selection(trip_type,'Trip type', select=True), 
        'vehicle_type':fields.selection(vehicle_type, 'Vehicle type', 
            select=True), 
        'product_id': fields.many2one('product.product', 'Car'),
        'total_trip_km': fields.float('Tot. km.', digits=(16, 2)),
         
        'operation':fields.selection(operation_type,'operation', select=True), 
        'amount_operation': fields.float('amount operation', digits=(16, 2)),
        'intervent_annotation': fields.text('Note'),      
        'activity_id':fields.many2one('account.analytic.intervent.activity', 
            'Activity'),          
        'mail_raccomanded':fields.boolean('Raccomanded', 
            help="Mail is a raccomanded"),
        'location_site': fields.char('Location', size=50, 
            help="Location of intervent"),
        'like_last':fields.boolean('Like last', 
            help="Set deafult user or date like last intervent inserted"),  
        'week_day':fields.char('Label', size=5), # only for view, not saved

        'range_vacancy':fields.boolean('Vacancy (range)', 
            help="If cheched added a 'to' date for vacancy period"),
        'to_date': fields.date('To Date'),
        } 

    # constraits function:
    def _check_quantity(self, cr, uid, ids, context=None):
        wiz_item=self.browse(cr, uid, ids, context=context)
        if wiz_item:
           return wiz_item[0].quantity > 0.0 
        return False
    
    # default function:
    def _default_department_id(self, cr, uid, ids, context=None):
        return self.pool.get('res.users').browse(
            cr, uid, uid).context_department_id.id

    def _default_week_day(self, cr, uid, ids, context=None):
        ''' Find weekday of today
        '''
        from datetime import datetime
        return self.dow[datetime.now().weekday()]        
        
    #_constraints = [
    #     (_check_quantity, "Quantity of intervent must be > 0", ['quantity',]),
    #]

    _defaults = {
        'department_id': _default_department_id,
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'like_last': lambda *a: False,
        'week_day': _default_week_day,
    }    
account_analytic_intervent_wizard()

class account_analytic_intervent_extra_product(osv.osv_memory):
    ''' Inherited to inser m2o fields with master wizard
    '''
    
    _name = "account.analytic.extra.wizard"
    _inherit = "account.analytic.extra.wizard"
    
    _columns = {
         'wizard_id':fields.many2one('account.analytic.intervent.wizard', 
             'Wizard'),
    }     
account_analytic_intervent_extra_product()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
