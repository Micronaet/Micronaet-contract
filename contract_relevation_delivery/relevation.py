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

# Utility: #####################################################################
def PrepareDate(valore):
    if valore: # TODO test correct date format
       return valore
    else:
       return time.strftime("%d/%m/%Y")

def PrepareFloat(valore):
    valore=valore.strip() 
    if valore: # TODO test correct date format       
       return float(valore.replace(",","."))
    else:
       return 0.0   # for empty values
       
def Prepare(valore):  
            # For problems: input win output ubuntu; trim extra spaces
            #valore=valore.decode('ISO-8859-1')
            valore=valore.decode('cp1252')
            valore=valore.encode('utf-8')
            return valore.strip()

def ShortCut(valore=''): 
    # used for code the title (partner or contact), ex.: Sig.ra > SIGRA
    if valore:
       valore = valore.upper()
       valore = valore.replace('.','')
       valore = valore.replace(' ','')
       return valore

# Class ########################################################################
class etl_relevation_header(osv.osv):
    ''' Class that is used for manager importation file block:
        every header is a daily file importation, in case of new importation
        it's possibly remove this header (so the subelements are all deleted in
        one moment)
    '''
    _name='etl.relevation.header'
    _description='ETL relevation header'
   
    # Scheduled action: ########################################################
    def schedule_etl_relevation_import(self, cr, uid, path, context=None):
        ''' ETL operations for import elements in csv folder (parameter setted up in
            scheduled action for path)
        '''
        import logging, os
        from datetime import datetime
        
        user_pool = self.pool.get('res.users')
        timesheet_pool=self.pool.get('hr.analytic.timesheet')
        line_pool = self.pool.get('etl.relevation.line')
        _logger = logging.getLogger('contract_relevation_delivery')
        black_list = self.pool.get('res.company').get_relevation_blacklist( cr, uid, context=context)

        # default parameter:
        search_text="Codice_1"
        total_columns = 11
        path=os.path.expanduser(path)
        try:
            for r,d,f in os.walk(path):  # pass all files in folder
                for files in f:
                    file_name = os.path.join(r,files)
                    if files[-4:]!=".csv":
                           _logger.error("No csv file: %s!"%(file_name,))
                           continue # jump file!
                    
                    # counter for every import files:
                    start=False # became true when get header line
                    counter={'tot':0, 'upd':0, 'new':0}                    
                    
                    try:
                        date = datetime.strptime("%s-%s-%s"%(files[:4],files[4:6],files[6:8]), "%Y-%m-%d")
                    except:
                       _logger.error("No date in file name: %s!"%(file_name,))
                       continue # jump file!

                    file_error = False # to test if importation doesn't work
                    header_id = False
                    
                    for line_to_parse in open(file_name,'rb'):
                         if not start:  # jump n lines of header 
                             if line_to_parse[:len(search_text)] == search_text:
                                 start = True # next line enter
                                 _logger.info('Start import file: %s'%(file_name))
                                 
                                 # HEADER CREATION #############################
                                 header_id = self.search(cr, uid, [('name','=',file_name),('date','=',date.strftime('%Y-%m-%d'))], context=context)
                                 if header_id:
                                     header_id = header_id[0]
                                 else:
                                     header_id = self.create(cr, uid, {'name': file_name,
                                                                       'date': date,
                                                                       'import_error': False,
                                                                      }, context=context)

                             continue # jump this line
                             
                         line = line_to_parse.split(",")                         
                         if len(line)!= total_columns:
                             _logger.info('Column error, must be: %s now: %s'%(total_columns, len(line)))
                             continue 
                             
                         # normal line:    
                         counter['tot'] += 1
                         csv_id=0
                         code = Prepare(line[csv_id]).upper()                     # codice lettore (Codice_1)
                         csv_id+=1
                         total = Prepare(line[csv_id])                            # total delivery (textbox46)
                         csv_id+=1
                         total_error = Prepare(line[csv_id])                      # total error (textbox47)
                         csv_id+=1
                         location = Prepare(line[csv_id])                         # location (Filiale_1)
                         csv_id+=1
                         field1 = Prepare(line[csv_id])                           # 19788 (textbox33)
                         csv_id+=1
                         field2 = Prepare(line[csv_id])                           # 72 (textbox34)
                         csv_id+=1
                         company = Prepare(line[csv_id])                          # FRATERNITA' (Ragionesociale_2)
                         csv_id+=1
                         field3 = PrepareFloat(line[csv_id])                      # 19788 (BusteTot_2)
                         csv_id+=1
                         field4 = Prepare(line[csv_id])                           # 19788 (BusteInPenaleTot_3)
                         csv_id+=1
                         field5 = PrepareFloat(line[csv_id])                      # 19788 (BusteTot_3)
                         csv_id+=1
                         field6 = Prepare(line[csv_id]).strip()                   # 19788 (BusteInPenaleTot_2)   strip last line to remove \r\n
                         csv_id+=1
                         
                         if code in black_list:
                             _logger.warning("Jump lector in blacklist: %s!"%(code,))                       
                             continue # jump line
                             
                         line_import_error=False
                         error_description=""
                         # computed field:                    
                         user_id = user_pool.get_user_from_relevation_code(cr, uid, code, context=context)
                         if not user_id: # test before write:
                             error_description="User not found [lector: %s]"%(code,)
                             _logger.error(error_description)
                             line_import_error=True
                             #continue # jumped element!

                         error=[]
                         timesheet_id = timesheet_pool.get_user_date_intervent(cr, uid, user_id, date, total, error, context=context)
                         if not timesheet_id:
                             if error:                                 
                                 error_description=error[0]
                             else:    
                                 error_description="No timesheet [lector %s-date %s]"%(code, date,)
                             _logger.error(error_description)
                             line_import_error=True
                             #continue # jumped element!
                            
                         # TODO update read elements in intervent! 
                         if timesheet_id:
                             pass 

                         # LINE CREATION #######################################
                         line_data={ 
                                    'name': code, # Lector code
                                    #'user_id':user_id,
                                    'total': total,
                                    'error': total_error,
                                    'date': date.strftime('%Y-%m-%d'),
                                    'location': location,
                                    #'timesheet_id': timesheet_id,
                                    'relevation_header_id': header_id,
                                    #'line_import_error': line_import_error,
                                    'error_description': error_description,
                                    }
                            
                         item = line_pool.search(cr, uid, [('name', '=', code),('relevation_header_id','=',header_id)], context=context) # assunt: in importation code is unique!
                         if item: # update
                            try:
                                counter['upd'] += 1  
                                # if timesheet not present and user not present write nothing 
                                # (maybe modified in program)
                                if timesheet_id and user_id: # modifico solo se presenti entrambe!!!
                                    line_data['user_id']=user_id # only during creation not for update!
                                    line_data['timesheet_id'] = timesheet_id

                         
                                modify_id = line_pool.write(cr, uid, item, line_data, context=context)
                                line_id=item[0]
                            except:
                                _logger.info("[ERROR] Modify line, current record: %s"%(code,))
                         else:           
                             try:
                                counter['new'] += 1  
                                line_data['user_id']=user_id # only during creation not for update!
                                line_data['timesheet_id'] = timesheet_id
                                line_data['line_import_error'] = line_import_error
                                
                                line_id = line_pool.create(cr, uid, line_data, context=context)
                             except:
                                 _logger.info("[ERROR] Create line, current record: %s"%(code,))
                         if line_import_error:
                             self.write(cr, uid, header_id, {'import_error': True}, context=context)

            _logger.info('Check error on new value if insert in intervent')
            timesheet_pool.check_error_intervent_value(cr, uid, context=context)
            
            _logger.info('End importation\n Counter: %s'%(counter))
        except:
            _logger.error('Error import product')                              
        return

    _columns = {
        'name':fields.char('File name', size=64, required=False, readonly=False),
        'date': fields.date('Ref. Date'),
        'import_error':fields.boolean('Import error', required=False),
    }
etl_relevation_header()    

class etl_relevation_line(osv.osv):
    ''' Class that is used for manager importation file block:
        every header is a daily file importation, in case of new importation
        it's possibly remove this header (so the subelements are all deleted in
        one moment)
    '''
    _name='etl.relevation.line'
    _description='ETL relevation line'
    _order='name'

    # on change elements:
    def onchange_timesheet_id(self, cr, uid, ids, timesheet_id, context=None):
        '''
        '''
        res={'value':{}}
        if timesheet_id:
            res['value']={'line_import_error': False,}  #'error_description':''}
        else:
            res['value']={'line_import_error': True,}   #'error_description':''}
            
        return res    
   
    _columns = {
        'name':fields.char('Lector code', size=64, required=False, readonly=False),
        'user_id':fields.many2one('res.users', 'User', required=False),
        'date': fields.date('Ref. Date'),        
        'total': fields.integer('Total'),
        'error': fields.integer('Error'),
        'location':fields.char('Location', size=64, required=False, readonly=False),
        'timesheet_id':fields.many2one('hr.analytic.timesheet', 'Timesheet', required=False),
        'line_import_error':fields.boolean('Line import error', required=False),        
        'error_description':fields.char('Error description', size=64, required=False, readonly=False),
        'relevation_header_id':fields.many2one('etl.relevation.header', 'Header', required=False, ondelete='cascade'),        
        'header_date': fields.related('relevation_header_id','date', type='date', string='Header date'),
    }
etl_relevation_line()

class etl_relevation_header(osv.osv):
    ''' Add extra 2many fields
    '''
    _name='etl.relevation.header'
    _inherit='etl.relevation.header'
           
    _columns = {
        'relevation_line_ids':fields.one2many('etl.relevation.line', 'relevation_header_id', 'Lines', required=False),
    }
etl_relevation_header()    

class res_users_extra_fields(osv.osv):
    ''' Add extra fields to user
    '''
    _name='res.users'
    _inherit='res.users'
   
    def get_user_from_relevation_code(self, cr, uid, code, context=None):
        ''' get user id from code of lector
        ''' 
        user_ids=self.search(cr, uid, [('relevation_code','ilike',code)], context=context) # NOTE: for link to a record with tab or space at end of name
        if user_ids and len(user_ids)==1:
            return user_ids[0]
        else:
            return False
       
    _columns = {
        'relevation_code':fields.char('User code', size=64, required=False, readonly=False, help="For lector used to delivery mail"),
    }
res_users_extra_fields()    

class res_company_extra_fields(osv.osv):
    ''' Add extra fields to company
    '''
    _name='res.company'
    _inherit='res.company'
   
    def get_relevation_blacklist(self, cr, uid, item_id=0, context=None):
        ''' Return the list of relevator blacklisted for company, if passed
            else return first company
        '''
        try:
            if not item_id:
                item_ids = self.search(cr, uid, [], context=context)
                if item_ids:
                    item_id=item_ids[0]
                else:
                    return ()    

            company_proxy = self.browse(cr, uid, item_id, context=context)                    
            return eval(company_proxy.relevation_blacklist)
        except:
            return ()
                
    _columns = {
        'relevation_blacklist':fields.text('Lector blacklist', required=False, readonly=False, help="List of lector to remove, in tupla format: ('LECTOR_1','LECTOR_2')"),
    }
res_company_extra_fields()    


class hr_analytic_timesheet_extra_functions(osv.osv):
    ''' Extra function to append in object
    '''
    _name='hr.analytic.timesheet'
    _inherit='hr.analytic.timesheet'
   
    def get_user_date_intervent(self, cr, uid, user_id, date_intervent, amount_operation_etl, error, context=None):
        ''' find intervent and return its link
        ''' 
        intervent_ids = self.search(cr, uid, [('user_id','=',user_id),('date','=',date_intervent.strftime('%Y-%m-%d'))], context=context)
        if intervent_ids and len(intervent_ids)==1:
            # Update value for relevation in intervent:
            update_rel = self.write(cr, uid, intervent_ids, {'amount_operation_etl': amount_operation_etl,
                                                             'error_etl': True, # TODO è corretto? default (after there's a test on it
                                                             }, context=context)
            return intervent_ids[0] 
        elif len(intervent_ids)>=1:
            error.append("Too much intervent [day: %s-Tot:%s"%(date_intervent, len(intervent_ids)))
            return False
        else: # generic error    
            error.append("No intervent [day: %s-Tot:%s"%(date_intervent, len(intervent_ids)))
            return False

    def check_error_intervent_value(self, cr, uid, context=None):
        ''' Test for all elements setted up as error_etl if there's the correct value, error only if:
            amount_operation_etl = amount_operation (and not 0)
        '''
        item_ids = self.search(cr, uid, [('error_etl','=',True)], context=context)
        
        for element in self.browse(cr, uid, item_ids, context=context):
            if not element.amount_operation:
                data = {'amount_operation': element.amount_operation_etl,'error_etl': False,}
                mod=self.write(cr, uid, [element.id], data, context=context)
                
            elif element.amount_operation == element.amount_operation_etl:
                data = {'error_etl': False,}
                mod=self.write(cr, uid, [element.id],data, context=context)
                
            else:
                pass # nothing, so error remain (or autocorrect?)                  
        return 
            
hr_analytic_timesheet_extra_functions() 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
