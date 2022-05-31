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

# get quickbooks config values
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
category_obj = rpc.env['product.category']
state_obj = rpc.env['res.country.state']
country_obj = rpc.env['res.country']
qb_invoice_obj = rpc.env['qb.invoice']
qb_line_obj = rpc.env['qb.invoice.line']






# -----------------------------------------------------------------------------
# update existing customers

# get recently modified customers from QuickBooks
cols = [
    "ListID",
    "Name",
    "BillAddressAddr1",
    "BillAddressAddr2",
    "BillAddressAddr3",
    "BillAddressAddr4",
    "BillAddressCity",
    "BillAddressPostalCode",
    "BillAddressState",
    "BillAddressCountry",
    "Email",
    "Phone",
]
sql = """
    select %s
    from Customer
    where TimeModified>?
    and TimeCreated<=?
"""
cur.execute(sql, (sync_time, sync_time))
qb_cust_rows = cur.fetchall()
qb_customers = {}
for row in qb_cust_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    row_dict['SalesOrPurchaseDesc'] = row_dict['SalesOrPurchaseDesc'] and row_dict['SalesOrPurchaseDesc'].strip() or None
    qb_customers[row_dict['ListID']] = row_dict
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
        state_id = state_obj.search([('code', '=', qb_customers[partner.ref]['BillAddressState'])])
        vals['state_id'] = state_id or False
    if partner.name != qb_customers[partner.ref]['BillAddressCountry']:
        vals['name'] = qb_customers[partner.ref]['BillAddressCountry']
        country_id = country_obj.search([('name', '=', qb_customers[partner.ref]['BillAddressCountry'])])
        vals['country_id'] = country_id or False
    if partner.email != qb_customers[partner.ref]['Email']:
        vals['email'] = qb_customers[partner.ref]['Email']
    if partner.phone != qb_customers[partner.ref]['Phone']:
        vals['phone'] = qb_customers[partner.ref]['Phone']
    if vals:
        partner.write(vals)




# -----------------------------------------------------------------------------
# create new customers

# get recently created customers from QuickBooks
sql = """
    select
        ListID,
        Name,
        BillAddressAddr1,
        BillAddressAddr2,
        BillAddressAddr3,
        BillAddressAddr4,
        BillAddressCity,
        BillAddressPostalCode,
        BillAddressState,
        BillAddressCountry,
        Email,
        Phone
    from Customer
    where TimeCreated>?
"""
cur.execute(sql, (sync_time, ))
qb_cust_rows = cur.fetchall()
qb_customers = []
for row in qb_cust_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    qb_customers.append(row_dict)

# create odoo customers
for cust in qb_customers:
    vals = {}
    vals['qb_ref'] = cust['ListID']
    vals['name'] = cust['Name']
    vals['ref'] = cust['BillAddressAddr1']
    vals['street'] = cust['BillAddressAddr3']
    vals['street2'] = cust['BillAddressAddr4']
    vals['city'] = cust['BillAddressCity']
    vals['zip'] = cust['BillAddressPostalCode']
    state_id = state_obj.search([('code', '=', cust['BillAddressState'])])
    vals['state_id'] = state_id and state_id[0] or False
    country_id = country_obj.search([('name', '=', cust['BillAddressCountry'])])
    vals['country_id'] = country_id and country_id[0] or False
    vals['email'] = cust['Email']
    vals['phone'] = cust['Phone']
    partner_obj.create(vals)






# -----------------------------------------------------------------------------
# update modified products

# get product categories
cat_ids = category_obj.search([('name', 'in', ['Exchange', 'Valve', 'Shipping', 'Other'])])
cats = category_obj.browse(cat_ids)
cat_map = {x.name: x.id for x in cats}

cols = [
    "ListID",
    "FullName",
    "SalesOrPurchaseDesc",
    "SalesOrPurchasePrice",
    "SalesOrPurchaseAccountRefFullName",
]
cols_string = ", ".join(cols)
sql = """
    select %s
    from Item
    where TimeModified>?
    and TimeCreated<=?
""" % cols_string
cur.execute(sql, (sync_time, sync_time))
qb_tmpl_rows = cur.fetchall()
qb_templates = {}
for row in qb_tmpl_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    row_dict['SalesOrPurchaseDesc'] = row_dict['SalesOrPurchaseDesc'] and row_dict['SalesOrPurchaseDesc'].strip() or None
    qb_templates[row_dict['ListID']] = row_dict
qb_tmpl_list_ids = list(qb_templates.keys())

# update odoo products
template_ids = template_obj.search([('ref', 'in', qb_tmpl_list_ids)])
templates = template_obj.browse(template_ids)
for tmpl in templates:
    vals = {}
    if tmpl.product_tmpl_id.name != qb_templates[tmpl.ref]['FullName']:
        vals['name'] = qb_templates[tmpl.ref]['FullName']
    if tmpl.product_tmpl_id.list_price != qb_templates[tmpl.ref]['SalesOrPurchasePrice']:
        vals['list_price'] = qb_templates[tmpl.ref]['SalesOrPurchasePrice']
    if tmpl.product_tmpl_id.list_price != qb_templates[tmpl.ref]['SalesOrPurchaseDesc']:
        vals['list_price'] = qb_templates[tmpl.ref]['SalesOrPurchaseDesc']
    if vals:
        tmpl.write(vals)






# -----------------------------------------------------------------------------
# create new products

# get recently created products from QuickBooks
cols = [
    "ListID",
    "FullName",
    "SalesOrPurchaseDesc",
    "Type",
    "SalesOrPurchasePrice",
    "SalesOrPurchaseAccountRefFullName",
]
cols_string = ", ".join(cols)
sql = """
    select %s
    from Item
    where TimeCreated>?
    and FullName not like '%%/S'
""" % cols_string
cur.execute(sql, (sync_time, ))
qb_tmpl_rows = cur.fetchall()
qb_templates = []
for row in qb_tmpl_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    row_dict['SalesOrPurchaseDesc'] = row_dict['SalesOrPurchaseDesc'] and row_dict['SalesOrPurchaseDesc'].strip() or None
    qb_templates.append(row_dict)

# create odoo products
for tmpl in qb_templates:
    cat_id = cat_map['Other']
    if tmpl['SalesOrPurchaseAccountRefFullName'] == 'VALVES':
        cat_id = cat_map['Valve']
    if '/E' in tmpl['FullName']:
        cat_id = cat_map['Exchange']
    vals = {
        'type': 'consu',
        'categ_id': cat_id,
        'ref': tmpl['ListID'],
        'name': tmpl['FullName'],
        'description': tmpl['SalesOrPurchaseDesc'],
        'list_price': tmpl['SalesOrPurchasePrice'],
    }
    template_obj.create(vals)





# -----------------------------------------------------------------------------
# update modified invoices

cols = [
    "TxnID",
    "IsPaid",
    "TxnDate",
    "ShipDate",
    "PONumber",
    "ShipMethodRefFullName",
]
cols_string = ", ".join(cols)
sql = """
    select %s
    from Invoice
    where TimeModified>?
    and TimeCreated<=?
""" % (cols_string, )
cur.execute(sql, (sync_time, ))
qb_rows = cur.fetchall()
qb_invoices = {}
qb_txn_ids = []
for row in qb_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    qb_invoices.append(row_dict)
    qb_invoices[row_dict['TxnID']] = row_dict
qb_txn_ids = list(qb_invoices.keys())

# update qb invoices in odoo
invoice_ids = qb_invoice_obj.search([('qb_txn', 'in', qb_txn_ids)])
invoices = qb_invoice_obj.browse(invoice_ids)
for invoice in invoices:
    vals = {}
    if invoice['txn_date'] != qb_invoices[invoice['qb_txn']]['TxnDate']:
        vals['txn_date'] = qb_invoices[invoice['qb_txn']]['TxnDate']
    if invoice['ship_date'] != qb_invoices[invoice['qb_txn']]['ShipDate']:
        vals['ship_date'] = qb_invoices[invoice['qb_txn']]['ShipDate']
    if invoice['is_paid'] != qb_invoices[invoice['qb_txn']]['IsPaid']:
        vals['is_paid'] = qb_invoices[invoice['qb_txn']]['IsPaid']
    if invoice['ship_method'] != qb_invoices[invoice['qb_txn']]['ShipMethodRefFullName']:
        vals['ship_method'] = qb_invoices[invoice['qb_txn']]['ShipMethodRefFullName']
    if invoice['po_number'] != qb_invoices[invoice['qb_txn']]['PONumber']:
        vals['po_number'] = qb_invoices[invoice['qb_txn']]['PONumber']
    if vals:
        invoice.write(vals)







# -----------------------------------------------------------------------------
# create new invoices

cols = [
    "TxnID",
    "TxnNumber",
    "CustomerRefListID",
    "IsPaid",
    "TxnDate",
    "ShipDate",
    "PONumber",
    "ShipMethodRefFullName",
    "ShipAddressAddr1",
    "ShipAddressAddr2",
    "ShipAddressAddr3",
    "ShipAddressAddr4",
    "ShipAddressAddr5",
    "ShipAddressCity",
    "ShipAddressState",
    "ShipAddressPostalCode",
    "ShipAddressCountry",
]
cols_string = ", ".join(cols)
sql = """
    select %s
    from Invoice
    Where TimeCreated>?
""" % (cols_string, )
cur.execute(sql, (sync_time, ))
qb_rows = cur.fetchall()
qb_invoices = []
qb_customer_ids = []
for row in qb_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    qb_invoices.append(row_dict)
    qb_customer_ids.append(row_dict['CustomerRefListID'])

# get odoo partners
odoo_partner_ids = partner_obj.search([('ref', 'in', qb_customer_ids)])
odoo_partners = partner_obj.browse(odoo_partner_ids)
qb_odoo_partners = {x.ref: x.id for x in odoo_partners}

# create qb invoices in odoo
for invoice in qb_invoices:
    partner_id = qb_odoo_partners.get(invoice['CustomerRefListID'])
    if not partner_id:
        sys.exit("Failed to find customer on invoice %s" % invoice['TxnNumber'])
    vals = {
        'name': invoice['TxnNumber'],
        'qb_txn': invoice['TxnID'],
        'txn_date': invoice['TxnDate'],
        'ship_date': invoice['ShipDate'],
        'is_paid': invoice['IsPaid'],
        'partner_id': partner_id,
        'ship_method': invoice['ShipMethodRefFullName'],
        'po_number': invoice['PONumber'],
        'ship_addr1': invoice['ShipAddressAddr1'],
        'ship_addr2': invoice['ShipAddressAddr2'],
        'ship_addr3': invoice['ShipAddressAddr3'],
        'ship_addr4': invoice['ShipAddressAddr4'],
        'ship_addr5': invoice['ShipAddressAddr5'],
        'ship_city': invoice['ShipAddressCity'],
        'ship_state': invoice['ShipAddressState'],
        'ship_zip': invoice['ShipAddressPostalCode'],
        'ship_country': invoice['ShipAddressCountry'],
    }
    qb_invoice_obj.create(vals)





# -----------------------------------------------------------------------------
# create new invoice lines

# get new core exchange invoice lines
cols = [
    "InvoiceLineTxnLineID",
    "InvoiceLineSeqNo",
    "TxnID",
    "InvoiceLineItemRefListID",
    "InvoiceLineDesc",
    "InvoiceLineQuantity",
]
cols_string = ", ".join(cols)
sql = """
    select %s
    from InvoiceLine
    Where TimeCreated>?
    and InvoiceLineDesc is not null
""" % (cols_string, )
cur.execute(sql, (sync_time, ))
qb_rows = cur.fetchall()
qb_inv_lines = []
qb_inv_ids = []
qb_line_item_codes = []
for row in qb_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    qb_inv_lines.append(row_dict)
    if row_dict['InvoiceLineItemRefListID'] and row_dict['InvoiceLineItemRefListID'] not in qb_line_item_codes:
        qb_line_item_codes.append(row_dict['InvoiceLineItemRefListID'])
    if row_dict['TxnID'] not in qb_inv_ids:
        qb_inv_ids.append(row_dict['TxnID'])

# get qb invoices from odoo
odoo_inv_ids = qb_invoice_obj.search([('qb_ref', 'in', qb_line_item_codes)])
odoo_invs = qb_invoice_obj.browse(odoo_inv_ids)
qb_odoo_invs = {x.qb_txn: x.id for x in odoo_invs}

# get odoo products
odoo_prod_ids = template_obj.search([('qb_ref', 'in', qb_line_item_codes)])
odoo_prods = template_obj.browse(odoo_prod_ids)
qb_odoo_prods = {x.qb_ref: x.id for x in odoo_prods}

# create qb invoice lines in odoo
for line in qb_inv_lines:
    qb_invoice_id = qb_odoo_invs.get(line['TxnID'])
    vals = {
        'qb_invoice_id': qb_invoice_id,
        'qb_ref': line['InvoiceLineTxnLineID'],
        'qb_line_seq_num': line['InvoiceLineSeqNo'],
        'product_tmpl_id': qb_odoo_prods[line['InvoiceLineItemRefListID']],
        'description': line['InvoiceLineDesc'],
        'quantity': line['InvoiceLineQuantity'],
    }
    qb_line_obj.create(vals)






# close quickbooks connection
cur.close()
cxn.close()




# write now() to the config file sync_time
parser.set('QB', 'sync_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
fp = open(conf_file_name, 'w')
parser.write(fp)
fp.close()
