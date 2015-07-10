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

class account_analytic_superintervent_wizard(osv.osv_memory):
    ''' Wizard that group superintervent and create all timesheet line AKA    
        analytic line in Journal
        Possibile filter is:
        1) This user of all user
        2) This department or all department or all extra_department
        3) From date to date
        All filter is not mandatory!        
    '''
    _name = "account.analytic.superintervent.wizard"

    # Button function:
    def create_superintervent_function(self, cr, uid, ids, context=None):
        ''' Create group of active superintervent
            Assign group costs to his own department contract (searching all
            open contract)
        '''
        # get wizard parameter to generate filter: #############################
        wizard_proxy = self.browse(cr, uid, ids)[0] # only one element
        superintervent_pool = self.pool.get('account.analytic.superintervent')
        group_pool = self.pool.get('account.analytic.superintervent.group')
        account_pool = self.pool.get('account.analytic.account')
        department_pool = self.pool.get('hr.department')
        
        domain_filter=[('group_id','=',False)]
        if not wizard_proxy.all_users:
           if wizard_proxy.user_id: # mandatory when no all_users:
              domain_filter.append(('user_id','=',wizard_proxy.user_id.id))

        if wizard_proxy.extra_department:
           domain_filter.append(('department_id','=',False)) # all department empty (check extra_department)
        elif not wizard_proxy.all_department:
           if wizard_proxy.department_id: # mandatory when no all_department:
              domain_filter.append(('department_id','=',wizard_proxy.department_id.id))
        # else no filter (all situations if check: all_departments)
        if wizard_proxy.from_date: 
           domain_filter.append(('date','>=',wizard_proxy.from_date))
        if wizard_proxy.to_date: 
           domain_filter.append(('date','<=',wizard_proxy.to_date))

        # List of intervent filtered > create group when break code ############
        superintervent_ids = superintervent_pool.search(cr, uid, domain_filter, order="department_id,user_id,date desc") # order for code break

        if not superintervent_ids:  # No result, only close wizard 
           return {'type': 'ir.actions.act_window_close',} # TODO return group list
           
        intervent_list=[]     # for update group intervent list
        group_list=[]         # for end redirect
        last_intervent=False
        total = 0.0
        for intervent in superintervent_pool.browse(cr, uid, superintervent_ids, context=context):
            if not last_intervent: # first history element
               last_intervent = intervent # test department
               
            if (last_intervent.department_id.id, last_intervent.user_id.id) != (intervent.department_id.id, intervent.user_id.id):  # TODO verify if is better use product
               # Create superintervent group: **********************************
               data_group={
                          'name': "%s- User: %s [Dep. %s]"%(wizard_proxy.to_date or last_intervent.date, 
                                                          last_intervent.user_id.name,
                                                          last_intervent.department_id.name if last_intervent.department_id else "All",
                                                          ),
                          'user_id': last_intervent.user_id.id,
                          #'employee_id': ,
                          'department_id': last_intervent.department_id.id if last_intervent.department_id else False,
                          'quantity': total,
                          'date': wizard_proxy.to_date or last_intervent.date, # TODO is correct to take last date after evalutating to_date?
                          }                              
               group_id = group_pool.create(cr, uid, data_group, context=context)
               group_list.append(group_id)
               # update intervent to link to the new group:
               update_intervent_group=superintervent_pool.write(cr, uid, intervent_list, {'group_id': group_id,})
               # ***************************************************************

               # reset value for new element yet read
               total=intervent.quantity           
               intervent_list=[]

               last_intervent=intervent
            else:
               total += intervent.quantity or 0.0
            intervent_list.append(intervent.id) # last line of the loop
                  
        # write last record ****************************************************
        data_group={
                   'name': "%s- User: %s [Dep. %s]"%(wizard_proxy.to_date or last_intervent.date, 
                                                   last_intervent.user_id.name,
                                                   last_intervent.department_id.name if last_intervent.department_id else "All",
                                                   ),
                   'user_id': last_intervent.user_id.id,
                   #'employee_id': ,
                   'department_id': last_intervent.department_id.id if last_intervent.department_id else False,
                   'quantity': total,
                   'date': wizard_proxy.to_date or last_intervent.date, # TODO is correct to take last date after evalutating to_date?
                   }                              
        group_id=group_pool.create(cr, uid, data_group, context=context)
        group_list.append(group_id)
        # update intervent to link to the new group:
        update_intervent_group=superintervent_pool.write(cr, uid, intervent_list, {'group_id': group_id,})
        # **********************************************************************
        
        # load information on date to calculate list of open account, divided per dept 
        department_contract={}
        total_contract=0.0
        all_contract=[]
        for department_id in [item for item in department_pool.search(cr, uid, [('for_extra_department','=',True)])]:        
            department_contract[department_id]=[item for item in account_pool.search(cr,uid,[ "&", "&", "&", "|",
                                                                                             ('date','=',False),                        # Date end non present
                                                                                             ('date','>',time.strftime('%Y-%m-%d')),    # OR Not deadline
                                                                                             ('state','=','open'),                      #    AND Open state
                                                                                             ('department_id','=',department_id),       #        AND This department
                                                                                             ('type','=', 'normal'),                    #            AND Type normal (not view)
                                                                                            ])] 
            all_contract += department_contract[department_id]
        total_contract = len(all_contract)
    
        # generate analytic.account.line / timesheet accordin to the list of account 
        divided_elements=[] # (id, uid, data, q, contract_ids)
        for group in group_pool.browse(cr,uid,group_list):
            if group.department_id: # there's a dep.
               total_account=len(department_contract[group.department_id.id])	
               contract_list_ids=department_contract[group.department_id.id] # only the department list
            else:
               total_account=total_contract
               contract_list_ids=all_contract
            hour_intervent=(group.quantity / total_account) if total_account else 0.0
            divided_elements.append((group.id, group.user_id.id, group.date, hour_intervent, contract_list_ids)) # TODO test false element
            
        self.pool.get('account.analytic.intervent.wizard').create_superintervent_function(cr, uid, divided_elements, context=None)    
            # TODO loop to create for every contract the division of costs !!!!!!!!
            
        return {'type': 'ir.actions.act_window_close',} # TODO return group list

    # On change action:
    def on_change_all_user(self, cr, uid, ids, all_users, context=None):
        ''' If all_user is True reset user_name
        '''
        if all_users:
           return {'value': {'user_id': False}}
        return {}
        
    def on_change_all_department(self, cr, uid, ids, extra_department, all_department, context=None):
        ''' If extra_department reset all_department and department_id
            If all_department reset department_id
        '''
        res = {'value': {}}
        if extra_department:
           res['value']['all_department']=False
           res['value']['department_id']=False
        elif all_department:
           res['value']['department_id']=False
        return res
        
    _columns = {
         'name':fields.text('Importation commment', required=False, readonly=False),
         'comment':fields.text('Note', required=False, readonly=True),

         'all_users':fields.boolean('All users', required=False),
         'user_id':fields.many2one('res.users', 'User', required=False, help="If is for a specific user (not for all"),

         'extra_department':fields.boolean('Extra department', required=False, help="Only the super intervent marked as 'extra department'"),
         'all_department':fields.boolean('All department', required=False, help="All department, also super intervent marked as 'extra department'"),
         'department_id': fields.many2one('hr.department', 'Department', required=False, help="Only this department"),
         
         'from_date': fields.date('From date', required=False),
         'to_date': fields.date('To date', required=False),
         }     

    _defaults = {
         'comment': lambda *a: "Filter element, after create, group of super intervent are created\nand analytic line costs are divided on contracts",
         'name': lambda *x: "%s - all open super intervent, all user, all department"%(time.strftime('%Y-%m-%d'),),
         
         'all_users': lambda *x: True, 
         'all_department': lambda *x: True, 
         
         'user_id': lambda *x: False,
         'department_id': lambda *x: False,
         'ro_date': lambda *a: time.strftime('%Y-%m-%d'),
         }     
account_analytic_superintervent_wizard()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
