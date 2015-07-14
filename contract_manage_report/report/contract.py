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

totals = {'hour': 0.0,
          'hour_cost': 0.0,
          'cost': 0.0,
          'invoice': 0.0,
          'operation':0.0,
         }

subtotals = {'hour': 0.0,
             'hour_cost': 0.0,
             'cost': 0.0,
             'invoice': 0.0,
             'operation': 0.0,
             'balance': 0.0,
             'general': 0.0,
            }

variables = {} # per problemi nell'interpretare le funzioni
t_cost={}
t_hour={}
t_hour_cost={}
t_invoice={}
t_operation={}

class Parser(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        # Total for counters:
        self.counters = {}
        
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            # Counters operations:
            'reset_all_counter': self.reset_all_counter,
            'set_counter': self.set_counter,
            'get_counter': self.get_counter,
        
            # Function called from ODT loop passing contract.id and data {}
            'intervent_proxy': self.get_intervent, # get intervent list
            'cost_proxy': self.get_cost,           # get costs list
            'invoice_proxy': self.get_invoice,     # get invoice list

            # Function called from ODT that loop using previous funct (contract.id and data {})
            'get_intervent_loop': self.get_intervent_loop, # get intervent total (global variable) 
            'get_cost_loop': self.get_cost_loop,           # get costs total (global variable)
            'get_invoice_loop': self.get_invoice_loop,     # get invoice total (global variable)

            'wizard_objects': self.wizard_objects, # master list of obj browse
            'test_part': self.test_part,           # show block test
            
            'reset_counters': self.reset_counters,
            
            'reset_subtotals': self.reset_subtotals, # Sumary report (every contract parent)

            'get_totals_account': self.get_totals_account,
            
            'get_totals': self.get_totals, 
            'get_subtotals': self.get_subtotals,
            'increment_subtotals': self.increment_subtotals,
            
            'set_variables': self.set_variables,
            'get_variables': self.get_variables,

            'filter_description': self.filter_description, # description of filter from wizard
            
            # Utility: 
            'format_data_italian': self.format_data_italian,
        })

    # --------------------   
    # Counters operations:    
    # --------------------   
    def reset_all_counter(self,):
        self.counters = {}
        return
    
    def set_counter(self, name, value = 0.0):
        ''' Create or set a counter in the counter list of the class
            If value is not setted counter is reset
        '''
        self.counters[name] = value
        return

    def get_counter(self, name):
        ''' Return counter value, if present, else 0.0
        '''
        if name not in self.counters:  # create if not present (0.0)
            self.counters[name] = 0.0
        return self.counters.get(name, 0.0)
    # --------------------   
    
    # TODO to remove!!!    
    def format_data_italian(self, value):
        ''' value = data in ISO format YYYY-MM-DD
            @return data in italian format DD-MM-YYYY (if present)
        '''
        if not value: 
            return ""
        
        value=value.strip()
        if len(value.strip())==10:
            return "%s/%s/%s"%(value[8:10], value[5:7], value[:4])
        return "" 

    def get_intervent_loop(self, account_id, data = None):
        ''' Reset totals every start
        '''
        response = self.get_intervent(account_id, data = data)
        return "" # Only used for total globals variables
        
    def get_cost_loop(self, account_id, data = None):
        ''' Reset totals every start
        '''
        response = self.get_cost(account_id, data = data)
        return "" # Only used for total globals variables
        
    def get_invoice_loop(self, account_id, data = None):
        ''' Reset totals every start
        '''
        response = self.get_invoice(account_id, data = data)
        return "" # Only used for total globals variables
        
    def get_totals_account(self, type_of, account_id):
        ''' Reset totals every start
        '''
        global t_cost
        global t_hour
        global t_hour_cost
        global t_invoice
        global t_operation
        global subtotals

        if type_of=='invoice':
            return t_invoice.get(account_id, 0.0)
        elif type_of=='cost':
            return t_cost.get(account_id, 0.0)
        elif type_of=='hour':
            return t_hour.get(account_id, 0.0)
        elif type_of=='hour_cost':
            return t_hour_cost.get(account_id, 0.0)
        elif type_of=='operation':    
            return t_operation.get(account_id, 0.0)
        elif type_of=='balance':
            res = t_invoice.get(account_id, 0.0) + t_cost.get(account_id, 0.0) + t_hour_cost.get(account_id, 0.0)
            subtotals[type_of] += res
            return res
            
        return 0.0
        
    def reset_counters(self):
        ''' Reset totals every start
        '''
        global subtotal
        global t_hour
        global t_hour_cost
        global t_invoice
        global t_operation

        t_cost = {}
        t_hour = {}
        t_hour_cost = {}
        t_invoice = {}
        t_operation = {}
        return 

    def get_totals(self, field, subtotalize=True):
        ''' Get totals for field:
              hour
              hour_cost
              cost
              invoice
        '''        
        global totals 
        global subtotals 
        
        res = totals.get(field, 0.0)
        if subtotalize:
            subtotals[field] += res
        return res

    def get_variables(self, variable):
        ''' Return variable value
        '''        
        global variables
        return variables.get(variable, 0.0)

    def set_variables(self, variable, value=0.0):
        ''' Set variable value and return value for print 
        '''        
        global variables
        variables[variable] = value or  0.0
        return variables[variable]

    def reset_subtotals(self):
        ''' Reset totals every start (for sumary report)
        '''
        global subtotals
        
        subtotals = {'hour': 0.0,
                     'hour_cost': 0.0,
                     'cost': 0.0,
                     'invoice': 0.0,
                     'operation': 0.0,
                     'balance': 0.0,
                     'general': 0.0,
                    }
        return 

    def get_subtotals(self, field):
        ''' Get subtotals for field:
        '''
        global subtotals 
        return subtotals.get(field, 0.0)

    def increment_subtotals(self, field, total):
        ''' Increment subtotals value for field (used for generat that is calculated)
            Subtotals are usually reset with the function
            It return total value (for print in ODS)
        '''
        global subtotals
        subtotals[field] = subtotals.get(field, 0.0) + (total or 0.0)
        return total # for let print the value

    def filter_description(self, data = None, short = False):
        ''' Get description textual of filter selecter on wizard
        '''
        if data is None:
           data = {}

        if short:
            res = ""
            if data.get('start_date', False): 
                res += "Da %s "%(self.formatLang(data.get('start_date'), date=True))
            if data.get('end_date', False): 
                res += "A %s "%(self.formatLang(data.get('end_date'), date=True))
            return "[ %s ]"%(res)
        else:
            res = "Filtro: "
            if data.get('contract_id', False):
                res += "Solo contratto: %s; "%(data.get('contract_name', "???"))
            elif data.get('department_id', False):
                res += "Solo dipartimento: %s; "%(data.get('department_name', "???"))
                
            if data.get('active_contract',False):
                res += "Movimentate; "
            if data.get('start_date', False): 
                res += "Dalla data %s; "%(self.formatLang(data.get('start_date'), date=True))
            if data.get('end_date', False): 
                res += "Alla data %s; "%(self.formatLang(data.get('end_date'), date = True))

            res += "  [ %s - %s - %s - %s - %s ]"%(
                "interventi visibili" if data.get('intervent', True) else "interventi non visibili", 
                "costi visibili" if data.get('cost', True) else "costi non visibili",
                "fatture visibili" if data.get('invoice', True) else "fatture non visibili",
                "bilancio periodo visibile" if data.get('balance_summary', True) else "bilancio periodo non visibile",
                "bilancio visibili" if data.get('balance', True) else "bilancio non visibili",
            )
            return res                             

    def test_part(self, block, data = None):
        ''' Function that test the wizard parameter and then return depend on 
            block name the value for show or not show in report
        '''
        if data is None:
           data = {}

        if block=='intervent':
            return data.get('hour', True)              # default show hour
        elif block=='cost':
            return data.get('cost', True)              # default show cost
        elif block=='invoice': 
            return data.get('invoice', True)           # default show invoice
        elif block=='balance': 
            return data.get('balance', True)           # default show balance
        elif block=='date_summary':
            return data.get('balance_summary', True)   # default show balance summary    
        return True
        
    def wizard_objects(self, objects, data = None):
        ''' Get list of contract (according to filter in wizard)
            Used in list of contract for detailed and summary report
        '''
        if data is None: 
           return objects           
        
        contract_pool = self.pool.get('account.analytic.account')

        # Test if there's contract selected, or department, or all:   
        if data.get('contract_id', 0): # all contract:
            domain = [('id','=',data.get('contract_id',0))]
        else:
            # Filter for domain
            if data.get('department_id', 0): # department
                domain = [('department_id', '=', data.get('department_id',0))]                    
            else:
                domain = []
            # Filter for active
            if data.get('active_contract',False):
                # TODO DUG!!!! work only if parent has movements!!!!
                # Find contract list movement ##################################
                domain_active = [] #TODO filter department?
                start_date = data.get('start_date',False)
                end_date = data.get('end_date',False)
                
                if start_date: domain_active.append(('date', '>=', start_date))
                if end_date:   domain_active.append(('date', '<=', end_date))

                intervent_pool = self.pool.get('hr.analytic.timesheet')
                item_ids = intervent_pool.search(self.cr, self.uid, domain_active)
                intervent_contract_ids = set([contract.account_id.id for contract in intervent_pool.browse(self.cr, self.uid, item_ids)])
                # TODO correct loop for load parent_id here

                invoice_cost_pool = self.pool.get('account.analytic.line')
                item_ids = invoice_cost_pool.search(self.cr, self.uid, domain_active)
                invoice_cost_ids = set([contract.account_id.id for contract in invoice_cost_pool.browse(self.cr, self.uid, item_ids)])
                item_ids=list(invoice_cost_ids | intervent_contract_ids)
                # TODO correct loop for load parent_id here

                domain.append(('id','in',item_ids)) 

        contract_ids = contract_pool.search(self.cr, self.uid, domain, order="code,name")
        return contract_pool.browse(self.cr, self.uid, contract_ids)
        
    def get_intervent(self, account_id, data = None):
        ''' Filter all account intervent and return browse obj
        '''    
        if data is None: 
            data={}

        domain = [('account_id','=',account_id)]
        start_date = data.get('start_date',False)
        end_date = data.get('end_date',False)
        
        if start_date:
            domain.append(('date','>=',start_date))
        if end_date:
            domain.append(('date','<=',end_date))

        intervent_pool = self.pool.get('hr.analytic.timesheet')
        intervent_ids = intervent_pool.search(self.cr, self.uid, domain)
        intervent_proxy = intervent_pool.browse(self.cr, self.uid, intervent_ids)

        global totals 

        global t_hour
        global t_hour_cost
        global t_operation

        totals['hour'] = sum([intervent.unit_amount or 0.0 for intervent in intervent_proxy])
        totals['hour_cost'] = sum([intervent.amount or 0.0 for intervent in intervent_proxy])
        totals['operation'] = sum([intervent.amount_operation or 0.0 for intervent in intervent_proxy])

        t_hour[account_id]=totals['hour']
        t_hour_cost[account_id]=totals['hour_cost']
        t_operation[account_id]=totals['operation']
        
        return intervent_proxy

    def get_invoice(self, account_id, data = None):
        ''' Filter all account intervent and return browse obj
        '''    
        
        if data is None: 
            data={}

        start_date = data.get('start_date',False)
        end_date = data.get('end_date',False)

        # invoice journal
        journal_pool = self.pool.get('account.analytic.intervent.type')
        journal_ids = journal_pool.search(self.cr, self.uid, [('name','=','invoice')]) 
        journal_proxy = journal_pool.browse(self.cr, self.uid, journal_ids)
        if not journal_proxy:
            pass # TODO error no Journal setted up
            return []
        journal_id=journal_proxy[0].journal_id.id
        
        domain = [
            ('account_id', '=', account_id),
            ('journal_id', '=', journal_id),
            ]
        if start_date:
            domain.append(('date', '>=', start_date))
        if end_date:
            domain.append(('date', '<=', end_date))

        invoice_pool = self.pool.get('account.analytic.line')
        invoice_ids = invoice_pool.search(self.cr, self.uid, domain) 
        invoice_proxy = invoice_pool.browse(self.cr, self.uid, invoice_ids)

        global totals 
        global t_invoice
        
        totals['invoice'] = sum(
            [invoice.amount or 0.0 for invoice in invoice_proxy]) # price
        t_invoice[account_id] = totals['invoice']
        return invoice_proxy

    def get_cost(self, account_id, data=None):
        ''' Filter all account intervent and return browse obj        
        '''    
        if data is None: 
            data={}

        start_date = data.get('start_date',False)
        end_date = data.get('end_date',False)
        
        # get 2 journal service and material:
        journal_pool = self.pool.get('account.analytic.intervent.type')
        journal_ids = journal_pool.search(self.cr, self.uid, [
            ('name', '!=', 'invoice')])  # all but not invoice
        journal_proxy = journal_pool.browse(self.cr, self.uid, journal_ids)
        journal_list = [item.journal_id.id for item in journal_proxy]

        domain = [
            ('account_id', '=', account_id),
            ('journal_id', 'in', journal_list)
            ]
        if start_date:
            domain.append(('date', '>=', start_date))
        if end_date:
            domain.append(('date', '<=', end_date))

        cost_pool = self.pool.get('account.analytic.line')
        cost_ids = cost_pool.search(self.cr, self.uid, domain) 
        cost_proxy = cost_pool.browse(self.cr, self.uid, cost_ids)
        
        global totals 
        global t_cost

        totals['cost'] = sum([cost.amount or 0.0 for cost in cost_proxy])
        t_cost[account_id] = totals['cost']

        return cost_proxy 

