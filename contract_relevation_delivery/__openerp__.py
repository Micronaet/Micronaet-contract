# -*- encoding: utf-8 -*-
##############################################################################
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

{
    'name' : 'Contract relevation delivery',
    'version' : '0.0.1',
    'category' : 'Generic Modules/Customization',
    'description' : """Parse CSV files that contain, daily exported, to 
                       associate total number of delivery with the intervent 
                       report and evaluate cost e productivity.
                    """,
    'author' : 'Micronaet s.r.l.',
    'website' : 'http://www.micronaet.it',
    'depends' : ['base',
                 'contract_manage',
                 'contract_manage_employee',
                 'contract_manage_report',                 
                 'hr_timesheet',
                 'report_aeroo',
                 'report_aeroo_ooo',
                ],
    'init_xml' : [], 
    'update_xml' : [
                   'security/ir.model.access.csv',
                   'relevation.xml',
                   'scheduler.xml',
                   'report/report_intervent.xml',
                   'wizard/wizard_views.xml',
                   ],
    'demo_xml' : [],
    'active' : False, 
    'installable' : True, 
}
