#!/bin/sh
echo Fare: delete from account_analytic_line where ref line 'FT%';
python ./invoice.py ~/ETL/servizi/daticommoerp.SEE

