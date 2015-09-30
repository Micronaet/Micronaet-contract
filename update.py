#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import os
import sys
import xmlrpclib

lista = """         89 |  -0.27 | 8F9WD (copia)
         85 |  -0.27 | AD02098 (copia)
         85 |  -0.27 | AD02098 (copia)
        116 |    -40 | AIRLESS (copia)
         23 |    -40 | Asfaltatrice xyz
        108 |    -20 | BIANCO AIRLESS GUBELA PL200 (copia)
        110 |    -20 | BIANCO RIFRANGENTE GUBELA AK 1000 (copia)
         91 |  -0.27 | BR794JG (copia)
         90 |  -0.27 | BX078NX (copia)
         86 |  -0.27 | CD240BW (copia)
         27 |  -0.27 | CE737JE FIAT PUNTO GASOLIO AUTOVETTURA
         96 |  -0.27 | CE885JM (copia)
         97 |  -0.27 | CM141EY (copia)
         50 |  -0.27 | CW624LW  (copia)
         51 |  -0.27 | DA562VT (copia)
         93 |  -0.27 | DB992GD (copia)
         43 |  -0.27 | DE349AZ
         44 |  -0.27 | DE363AZ
         45 |  -0.27 | DH323CM
         33 |  -0.27 | DH726JX
         46 |  -0.27 | DH763CG
        106 |    -20 | DILUENTE (copia)
         92 |  -0.27 | DJ079JC (copia)
         87 |  -0.27 | DN831NC (copia)
         47 |  -0.27 | DS602TH
         62 |  -0.27 | DX81672 (copia)
         57 |  -0.27 | DY40288 (copia)
         95 |  -0.27 | EB455TY (copia)
        101 |  -0.27 | EK044YR (copia)
        114 |    -40 | GENERATORE CORRENTE (copia)
        107 |    -20 | GIALLO AIRLESS GUBELA PL202 (copia)
        111 |    -20 | GIALLO RIFRANGENTE GUBELA PV 802 (copia)
        128 | -39.58 | GRADIENTE STUCCO RAPIDO lt 1 (copia)
         24 |    -32 | Latta vernice bianca
        102 |    -20 | MURIVAL RAAL 9002 (copia)
        125 |   -9.2 | MURIVAL RAAL 9002 tinte muro/14 litri (copia)
        109 |    -20 | NERO GUBELA PL200 (copia)
        126 | -16.15 | RISANANTE A 10-B1 ANTIMUFFA lt 1 (copia)
        112 |    -20 | SIKAFLOOR 263 SL (copia)
        127 |  -9.68 | SMALTO K81 VARI COLORI lt 1 (copia)
        115 |    -40 | TRACCIALINEE (copia)
        104 |    -20 | UNIEPOX BLU (copia)
        105 |    -20 | UNIEPOX GIALLO (copia)
        103 |    -20 | UNIEPOX ROSSO (copia)
         75 |   -0.1 | X2VCDH  (copia)
         60 |  -0.27 | X3BNM2 (copia)
         80 |  -0.27 | X3V3C7 (copia)
         83 |  -0.27 | X3WXT3 (copia)"""
product_db = {}
for p in lista.split('\n'):
    element = p.split('|')
    product_db[element[2].strip()] = (int(element[0].strip()), float(element[1].strip()))
        


# XMLRPC connection for autentication (UID) and proxy 
server = '192.168.1.21' #'localhost'
port = 8069
dbname = 'fratservizi'
user = 'admin'
pwd = 'password'

sock = xmlrpclib.ServerProxy(
    'http://%s:%s/xmlrpc/common' % (server, port), allow_none=True)
uid = sock.login(dbname, user, pwd)
sock = xmlrpclib.ServerProxy(
    'http://%s:%s/xmlrpc/object' % (server, port), allow_none=True)

item_ids = sock.execute( # search current ref
   dbname, uid, pwd, 'account.analytic.line', 'search', [           
       ('date', '>=', '2015/01/01'),
       ('journal_id', '=', 3),
       ])

# Read database:
item_read = sock.execute(
   dbname, uid, pwd, 'account.analytic.line', 'read', 
   item_ids, ('product_id', 'name', 'amount', 'unit_amount'))
for record in item_read: 
   if record['name'] not in product_db:
       print "NOT FOUND: ", record
   else:
       new = product_db[record['name']]
       print "OLD: ID %s > %s Amount %s > %f" % (
           record['product_id'][0], 
           new[0], 
           record['amount'],
           record['unit_amount'] * new[1],
           )
       sock.execute(
           dbname, uid, pwd, 'account.analytic.line', 'write', 
           record['id'], {
               'product_id': new[0],
               'amount': record['unit_amount'] * new[1],
               })

