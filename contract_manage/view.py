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
from tools.translate import _
# TODO FINIRE!!!!
class hr_analytic_timesheet_total(osv.osv):
    _name = "hr.analytic.timesheet.total"
    _description = "Intervent total"
    _auto = False
    _columns = {
            'name': fields.many2one('auction.dates','Auction date',readonly=True,select=1),
            'state': fields.selection((('draft','Draft'),('close','Closed')),'Status', select=1),
            'adj_total': fields.float('Total Adjudication'),
            'date': fields.date('Date', readonly=True,select=1),
            'user_id':fields.many2one('res.users', 'User',select=1)

    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_auction_adjudication')
        cr.execute("""
            create or replace view report_auction_adjudication as (
                select
                    l.id as id,
                    l.id as name,
                    sum(m.obj_price) as adj_total,
                    to_char(l.create_date, 'YYYY-MM-01') as date,
                    l.create_uid as user_id,
                    l.state
                from
                    auction_dates l ,auction_lots m
                    where
                        m.auction_id=l.id
                    group by
                        l.id,l.state,l.name,l.create_uid,to_char(l.create_date, 'YYYY-MM-01')

            )
        """)
report_auction_adjudication()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
