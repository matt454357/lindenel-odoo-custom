import sys
import psutil
import configparser
import odoorpc
import pyodbc
import os
from datetime import datetime

# only continue if quickbooks is running
if "QBW32.EXE" not in (p.name() for p in psutil.process_iter()):
    sys.exit()


# get and read config file
dir_name = os.path.dirname(__file__)
conf_file_name = os.path.join(dir_name, 'qodbc_push_odoo.ini')
parser = configparser.RawConfigParser()
parser.read(conf_file_name)

# get odoo config values
host = parser['ODOO']['host']
port = parser['ODOO']['port']
protocol = parser['ODOO']['protocol']
db = parser['ODOO']['db']
username = parser['ODOO']['username']
password = parser['ODOO']['password']

# get qickbooks config values
dsn = parser['QB']['dsn']
sync_time = parser['QB']['sync_time']
sync_dt = datetime.strptime(sync_time, "%Y-%m-%d %H:%M:%S")


# connect to QuickBooks via QODBC
cxn = pyodbc.connect('DSN=QuickBooks Data;')
cur = cxn.cursor()

# connect to Odoo via odoorpc
rpc = odoorpc.ODOO(host, port=port)
rpc.login(db, username, password)

# get odoo objects
partner_obj = rpc.env['res.partner']
template_obj = rpc.env['product.template']
product_obj = rpc.env['product.product']
state_obj = rpc.env['res.country.state']
country_obj = rpc.env['res.country']
core_obj = rpc.env['core.exchange']


# get recently modified customers from QuickBooks
sql = """
    select
        ListID,
        Name,
        BillAddressAddr3,
        BillAddressAddr4,
        BillAddressCity,
        BillAddressPostalCode,
        BillAddressState,
        BillAddressCountry
    from Customer
    where TimeModified>?
    and TimeCreated<=?
"""
cur.execute(sql, (sync_time, sync_time))
qb_cust_rows = cur.fetchall()
qb_customers = {}
for row in qb_cust_rows:
    qb_customers[row[0]] = {
        'ListID': row[0],
        'Name': row[1],
        'BillAddressAddr3': row[4],
        'BillAddressAddr4': row[5],
        'BillAddressCity': row[7],
        'BillAddressPostalCode': row[8],
        'BillAddressState': row[9],
        'BillAddressCountry': row[10],
    }
qb_cust_list_ids = list(qb_customers.keys())

# update odoo customers
partner_ids = partner_obj.search([('ref', 'in', qb_cust_list_ids)])
partners = partner_obj.browse(partner_ids)
for partner in partners:
    vals = {}
    if partner.name != qb_customers[partner.ref]['Name']:
        vals['name'] = qb_customers[partner.ref]['Name']
    if partner.street != qb_customers[partner.ref]['BillAddressAddr3']:
        vals['street'] = qb_customers[partner.ref]['BillAddressAddr3']
    if partner.street2 != qb_customers[partner.ref]['BillAddressAddr4']:
        vals['street2'] = qb_customers[partner.ref]['BillAddressAddr4']
    if partner.city != qb_customers[partner.ref]['BillAddressCity']:
        vals['city'] = qb_customers[partner.ref]['BillAddressCity']
    if partner.zip != qb_customers[partner.ref]['BillAddressPostalCode']:
        vals['zip'] = qb_customers[partner.ref]['BillAddressPostalCode']
    if partner.state_id.code != qb_customers[partner.ref]['BillAddressState']:
        state_id = state_obj.search(['code', '=', qb_customers[partner.ref]['BillAddressState']])
        vals['state_id'] = state_id or False
    if partner.name != qb_customers[partner.ref]['BillAddressCountry']:
        vals['name'] = qb_customers[partner.ref]['BillAddressCountry']
        country_id = country_obj.search(['name', '=', qb_customers[partner.ref]['BillAddressCountry']])
        vals['country_id'] = country_id or False
    if vals:
        partner.write(vals)

# get recently created customers from QuickBooks
sql = """
    select
        ListID,
        Name,
        BillAddressAddr3,
        BillAddressAddr4,
        BillAddressCity,
        BillAddressPostalCode,
        BillAddressState,
        BillAddressCountry
    from Customer
    where TimeCreated>?
"""
cur.execute(sql, (sync_time, ))
qb_cust_rows = cur.fetchall()
qb_customers = []
for row in qb_cust_rows:
    qb_customers.append({
        'ListID': row[0],
        'Name': row[1],
        'BillAddressAddr3': row[2],
        'BillAddressAddr4': row[3],
        'BillAddressCity': row[4],
        'BillAddressPostalCode': row[5],
        'BillAddressState': row[6],
        'BillAddressCountry': row[7],
    })

# create odoo customers
for cust in qb_customers:
    vals = {}
    vals['ref'] = cust['ListID']
    vals['name'] = cust['Name']
    vals['street'] = cust['BillAddressAddr3']
    vals['street2'] = cust['BillAddressAddr4']
    vals['city'] = cust['BillAddressCity']
    vals['zip'] = cust['BillAddressPostalCode']
    state_id = state_obj.search(['code', '=', cust['BillAddressState']])
    vals['state_id'] = state_id or False
    vals['name'] = cust['BillAddressCountry']
    country_id = country_obj.search(['name', '=', cust['BillAddressCountry']])
    vals['country_id'] = country_id or False
    if vals:
        partner_obj.create(vals)









# get recently modified products
sql = """
    select
        ListID,
        Name,
        SalesOrPurchasePrice
    from Item
    where TimeModified>?
    and TimeCreated<=?
"""
cur.execute(sql, (sync_time, sync_time))
qb_tmpl_rows = cur.fetchall()
qb_templates = {}
for row in qb_tmpl_rows:
    qb_templates[row[0]] = {
        'ListID': row[0],
        'Name': row[1],
        'SalesOrPurchasePrice': row[4],
    }
qb_tmpl_list_ids = list(qb_templates.keys())

# update odoo products
template_ids = template_obj.search([('default_code', 'in', qb_tmpl_list_ids)])
templates = template_obj.browse(template_ids)
for tmpl in templates:
    vals = {}
    if tmpl.product_tmpl_id.name != qb_templates[tmpl.default_code]['Name']:
        vals['name'] = qb_templates[tmpl.default_code]['Name']
    if tmpl.product_tmpl_id.list_price != qb_templates[tmpl.default_code]['SalesOrPurchasePrice']:
        vals['list_price'] = qb_templates[tmpl.default_code]['SalesOrPurchasePrice']
    if vals:
        tmpl.write(vals)

# get recently created products from QuickBooks
sql = """
    select
        ListID,
        Name,
        SalesOrPurchasePrice
    from Item
    where TimeCreated>?
"""
cur.execute(sql, (sync_time, ))
qb_tmpl_rows = cur.fetchall()
qb_templates = []
for row in qb_tmpl_rows:
    qb_templates.append({
        'ListID': row[0],
        'Name': row[1],
        'SalesOrPurchasePrice': row[4],
    })

# create odoo products
for tmpl in qb_templates:
    vals = {
        'type': 'consu',
        'categ_id': 1,
        'default_code': tmpl['ListID'],
        'name': tmpl['Name'],
        'list_price': tmpl['SalesOrPurchasePrice'],
    }
    template_obj.create(vals)







# get core exchange item ids from qb
sql = """
    select ListID
    from Item
    where Name like '%/E%'
"""
cur.execute(sql)
qb_item_rows = cur.fetchall()
exchange_item_ids = [x[0] for x in qb_item_rows]
ids_string = "', '".join(exchange_item_ids)

# get new core exchange invoice lines
sql = """
    select
        InvoiceLineTxnLineID,
        TxnID,
        TxnNumber,
        IsPaid,
        InvoiceLineItemRefListID,
        InvoiceLineDesc,
        InvoiceLineQuantity,
        TimeCreated,
        InvoiceCustomerListID
    from InvoiceLine
    Where TimeCreated>?
    and InvoiceLineItemRefListID in ('%s')
""" % ids_string
# sync_time.strftime("%Y-%m-%d %H:%M:%S")
cur.execute(sql, (sync_time, ))
qb_core_rows = cur.fetchall()
qb_cores = []
qb_core_item_codes = []
qb_invoice_line_ids = []
qb_customer_ids = []
for row in qb_core_rows:
    qb_cores.append({
        'InvoiceLineTxnLineID': row[0],
        'TxnID': row[1],
        'TxnNumber': row[2],
        'IsPaid': row[3],
        'InvoiceLineItemRefListID': row[4],
        'InvoiceLineDesc': row[5],
        'InvoiceLineQuantity': row[6],
        'TimeCreated': row[7],
        'InvoiceCustomerListID': row[8],
    })
    qb_core_item_codes.append(row[4])
    qb_invoice_line_ids.append(row[0])
    qb_customer_ids.append(row[8])

# get odoo partners
odoo_partner_ids = partner_obj.search([('ref', 'in', qb_customer_ids)])
odoo_partners = partner_obj.browse(odoo_partner_ids)
qb_odoo_partners = {x.ref: x.id for x in odoo_partners}

# create odoo core records
for core in qb_cores:
    if not partner_id:
        sys.exit("Failed to find customer %s" % core['ListID'])
    vals = {
        'partner_id': partner_id,
        'ext_ref': core['InvoiceLineTxnLineID'],
        'qb_invoice': core['TxnNumber'],
        'product_tmpl_id': core_tmpl_ids[core['InvoiceLineItemRefListID']],
        'description': core['InvoiceLineDesc'],
        'quantity': core['InvoiceLineQuantity'],
        'invoice_date': core['TimeCreated'],
        'is_paid': core['IsPaid'],
    }
    core_obj.create(vals)







# get modified core exchange invoice lines
sql = """
    select
        InvoiceLineTxnLineID,
        TxnID,
        TxnNumber,
        IsPaid,
        InvoiceLineItemRefListID,
        InvoiceLineDesc,
        InvoiceLineQuantity,
        TimeCreated,
        InvoiceCustomerListID
    from InvoiceLine
    where TimeModified>?
    and TimeCreated<=?
    and InvoiceLineItemRefListID in ('%s')
""" % ids_string
# sync_time.strftime("%Y-%m-%d %H:%M:%S")
cur.execute(sql, (sync_time, sync_time))
qb_core_rows = cur.fetchall()
qb_cores = []
qb_core_item_codes = []
qb_invoice_line_ids = []


for row in qb_core_rows:
    qb_cores[row[0]] = {
        'ListID': row[0],
        'Name': row[1],
        'BillAddressAddr3': row[4],
        'BillAddressAddr4': row[5],
        'BillAddressCity': row[7],
        'BillAddressPostalCode': row[8],
        'BillAddressState': row[9],
        'BillAddressCountry': row[10],
    }
qb_cust_list_ids = list(qb_customers.keys())



# get core ids from odoo
core_ids = core_obj.search([('ext_ref', 'in', core_ids)])
core_recs = template_obj.browse(core_ids)

# update odoo core records







# close quickbooks connection
cur.close()
cxn.close()




# write now() to the config file sync_time
parser.set('QB', 'sync_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
fp = open(conf_file_name, 'w')
parser.write(fp)
fp.close()
