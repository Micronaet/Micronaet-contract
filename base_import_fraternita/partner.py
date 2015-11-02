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

class res_partner_extra_fields(osv.osv):
    _inherit ='res.partner'

    _columns = {
       'extra_phone': fields.text('Extra phone'),
       'is_employee': fields.boolean('Is employee', required=False),
       }
res_partner_extra_fields()

class res_partner_address_extra_fields(osv.osv):
    _inherit ='res.partner.address'

    _columns = {
        'extra_phone': fields.text('Extra phone'),
        }
res_partner_address_extra_fields()

class hr_employee_extra_fields(osv.osv):
    _inherit ='hr.employee'

    _columns = {
        'import':fields.boolean('Import', required=False),
        'birth_place': fields.char('Birth place', size=80, required=False, readonly=False), 
       
        # settore
        # stato
        # TODO mettere i campi nella view!!
        'date_recruitment': fields.date('Date recruitment'), # data_assunzione
        'date_retired': fields.date('Date retired'), # data dimissione
        'curricula': fields.text('Curricula'), 
        'patent_type': fields.char('Patent type', size=5, required=False, readonly=False),  # patente
        # mansione               
        # orario di lavoro
        # tipo contratto 
        'date_end_contract': fields.date('End contract'),  # data fine contratto
        # > department_id (esiste)
        # > contract_ids (esiste
        }
hr_employee_extra_fields()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
