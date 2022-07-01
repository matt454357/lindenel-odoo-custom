import sys
import signal
import psutil
import configparser
import odoorpc
import pyodbc
import os
from datetime import datetime

# only continue if quickbooks is running
print("\nStarting Odoo Sync")
if "QBW32.EXE" not in (p.name() for p in psutil.process_iter()):
    sys.exit("Can't continue without QuickBooks running")


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
rpc = odoorpc.ODOO(host=host, protocol=protocol, port=port)
rpc.login(db, username, password)

# get odoo objects
seq_obj = rpc.env['ir.sequence']
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
cols_string = ", ".join(cols)

# get customers already existing in odoo
print("Getting QB customer references from odoo")
qb_refs = rpc.execute('res.partner', 'read', partner_obj.search([('qb_ref', '!=', False)]), ['qb_ref'])
qb_refs_string = ''
if qb_refs:
    qb_refs_string = "and ListID in ('%s')" % "', '".join([x['qb_ref'] for x in qb_refs])
odoo_qb_partner_map = {x['qb_ref']: x['id'] for x in qb_refs}

# get recently modified customers from QuickBooks
sql = """
    select %s
    from Customer
    where TimeModified>?
    and TimeCreated<=?
    %s
""" % (cols_string, qb_refs_string)
print("Getting modified QB customers")
cur.execute(sql, (sync_dt, sync_dt))
qb_cust_rows = cur.fetchall()
qb_customers = {}
for row in qb_cust_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    qb_customers[row_dict['ListID']] = row_dict
qb_cust_list_ids = list(qb_customers.keys())

# update odoo customers
print("Getting odoo customers")
partner_ids = partner_obj.search([('ref', 'in', qb_cust_list_ids)])
partners = partner_obj.browse(partner_ids)
print("Updating %s modified customers" % len(qb_customers))
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
cols_string = ", ".join(cols)

if qb_refs:
    qb_refs_string = "and ListID not in ('%s')" % "', '".join([x['qb_ref'] for x in qb_refs])

# get recently created customers from QuickBooks
sql = """
    select %s
    from Customer
    where TimeCreated>?
    %s
""" % (cols_string, qb_refs_string)
print("Getting new QB customers")
cur.execute(sql, (sync_dt, ))
qb_cust_rows = cur.fetchall()
qb_customers = []
for row in qb_cust_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    qb_customers.append(row_dict)

# create odoo customers
print("Creating %s new customers" % len(qb_customers))
for cust in qb_customers:
    state_id = state_obj.search([('code', '=', cust['BillAddressState'])])
    country_id = country_obj.search([('name', '=', cust['BillAddressCountry'])])
    vals = {
        'company_type': 'company',
        'qb_ref': cust['ListID'],
        'name': cust['Name'],
        'ref': cust['BillAddressAddr1'],
        'street': cust['BillAddressAddr3'],
        'street2': cust['BillAddressAddr4'],
        'city': cust['BillAddressCity'],
        'zip': cust['BillAddressPostalCode'],
        'state_id': state_id and state_id[0] or False,
        'country_id': country_id and country_id[0] or False,
        'email': cust['Email'],
        'phone': cust['Phone'],
    }
    partner_obj.create(vals)






# -----------------------------------------------------------------------------
# update modified products

# get products already existing in odoo
print("Getting QB product references from odoo")
qb_refs = rpc.execute('product.template', 'read', template_obj.search([('qb_ref', '!=', False)]), ['qb_ref'])
qb_refs_string = ''
if qb_refs:
    qb_refs_string = "and ListID in ('%s')" % "', '".join([x['qb_ref'] for x in qb_refs])

# get product categories
odoo_cat_names = [
    'QB Valve Exchange',
    'QB Valve Repair',
    'QB Valve Purchase',
    'QB Shipping',
    'QB Warranty',
    'QB Kit',
    'QB Parts',
    'QB Other',
]
cat_ids = category_obj.search([('name', 'in', odoo_cat_names)])
cats = category_obj.browse(cat_ids)
odoo_cat_map = {x.name: x.id for x in cats}

# Items in the VALVES account will be manually matched to one of the
# three "QB Valve ..." odoo categories, based on the item name.
# Items with no account will be assigned to the "Other" category
qb_odoo_cat_name_map = [
    # ('VALVES': None),
    ('Shipping', 'QB Shipping'),
    ('Warranty', 'QB Other'),
    ('kit', 'QB Other'),
    ('COGS:PARTS', 'QB Other'),
    ('Sales', 'QB Other'),
    ('PART SALES', 'QB Other'),
    ('tube', 'QB Other'),
    ('regulator', 'QB Other'),
    ('UPS', 'QB Shipping'),
    ('Shipping:Packaging', 'QB Shipping'),
    ('credit', 'QB Other'),
    ('Past due', 'QB Other'),
    # (None: 'QB Other'),
    ('Repairs', 'QB Other'),
    ('Labor', 'QB Other'),
    ('T&E:Travel', 'QB Other'),
    ('T&E:Meals', 'QB Other'),
]
qb_cat_map = {x[0]: odoo_cat_map[x[1]] for x in qb_odoo_cat_name_map}

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
    %s
""" % (cols_string, qb_refs_string)
print("Getting modified QB products")
cur.execute(sql, (sync_dt, sync_dt))
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
print("Getting odoo products")
template_ids = template_obj.search([('qb_ref', 'in', qb_tmpl_list_ids)])
templates = template_obj.browse(template_ids)
print("Updating %s modified products" % len(qb_templates))
for tmpl in templates:
    vals = {}
    new_cat_id = qb_cat_map.get(qb_templates[tmpl.qb_ref]['SalesOrPurchaseAccountRefFullName'])
    if qb_templates[tmpl.qb_ref]['SalesOrPurchaseAccountRefFullName'] == 'VALVES':
        if '/E' in qb_templates[tmpl.qb_ref]['FullName']:
            new_cat_id = odoo_cat_map.get('QB Valve Exchange')
        elif '/S' in qb_templates[tmpl.qb_ref]['FullName']:
            new_cat_id = odoo_cat_map.get('QB Valve Purchase')
        else:
            new_cat_id = odoo_cat_map.get('QB Valve Repair')
    new_cat_id = new_cat_id or odoo_cat_map['QB Other']
    if tmpl.name != qb_templates[tmpl.qb_ref]['FullName']:
        vals['name'] = qb_templates[tmpl.qb_ref]['FullName']
    if tmpl.list_price != qb_templates[tmpl.qb_ref]['SalesOrPurchasePrice']:
        vals['list_price'] = qb_templates[tmpl.qb_ref]['SalesOrPurchasePrice']
    if tmpl.description != qb_templates[tmpl.qb_ref]['SalesOrPurchaseDesc']:
        vals['description'] = qb_templates[tmpl.qb_ref]['SalesOrPurchaseDesc']
    if tmpl.categ_id.id != new_cat_id:
        vals['categ_id'] = new_cat_id
    if vals:
        tmpl.write(vals)






# -----------------------------------------------------------------------------
# create new products

if qb_refs:
    qb_refs_string = "and ListID not in ('%s')" % "', '".join([x['qb_ref'] for x in qb_refs])

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
    %s
""" % (cols_string, qb_refs_string)
print("Getting new QB products")
cur.execute(sql, (sync_dt, ))
qb_tmpl_rows = cur.fetchall()
qb_templates = []
for row in qb_tmpl_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    row_dict['SalesOrPurchaseDesc'] = row_dict['SalesOrPurchaseDesc'] and row_dict['SalesOrPurchaseDesc'].strip() or None
    qb_templates.append(row_dict)

# create odoo products
print("Creating %s new products" % len(qb_templates))
for tmpl in qb_templates:
    new_cat_id = qb_cat_map.get(tmpl['SalesOrPurchaseAccountRefFullName'])
    if tmpl['SalesOrPurchaseAccountRefFullName'] == 'VALVES':
        if '/E' in tmpl['FullName']:
            new_cat_id = odoo_cat_map.get('QB Valve Exchange')
        elif '/S' in tmpl['FullName']:
            new_cat_id = odoo_cat_map.get('QB Valve Purchase')
        else:
            new_cat_id = odoo_cat_map.get('QB Valve Repair')
    new_cat_id = new_cat_id or odoo_cat_map['QB Other']
    vals = {
        'type': 'consu',
        'categ_id': new_cat_id,
        'qb_ref': tmpl['ListID'],
        'name': tmpl['FullName'],
        'description': tmpl['SalesOrPurchaseDesc'],
        'list_price': float(tmpl['SalesOrPurchasePrice'] or 0.0),
        'default_code': seq_obj.next_by_code('qb.part.code')
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
print("Getting modified QB invoices")
cur.execute(sql, (sync_dt, sync_dt))
qb_rows = cur.fetchall()
qb_invoices = {}
qb_txn_ids = []
for row in qb_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    qb_invoices[row_dict['TxnID']] = row_dict
qb_txn_ids = list(qb_invoices.keys())

# update qb invoices in odoo
print("Getting odoo invoices")
invoice_ids = qb_invoice_obj.search([('qb_ref', 'in', qb_txn_ids)])
invoices = qb_invoice_obj.browse(invoice_ids)
print("Updating %s modified invoices" % len(qb_invoices))
for invoice in invoices:
    vals = {}
    if invoice.txn_date != qb_invoices[invoice.qb_ref]['TxnDate']:
        vals['txn_date'] = qb_invoices[invoice.qb_ref]['TxnDate'].strftime("%Y-%m-%d %H:%M:%S")
    if invoice.ship_date != qb_invoices[invoice.qb_ref]['ShipDate'] and qb_invoices[invoice.qb_ref]['ShipDate']:
        vals['ship_date'] = qb_invoices[invoice.qb_ref]['ShipDate'].strftime("%Y-%m-%d %H:%M:%S")
    if invoice.is_paid != qb_invoices[invoice.qb_ref]['IsPaid']:
        vals['is_paid'] = qb_invoices[invoice.qb_ref]['IsPaid']
    if invoice.ship_method != qb_invoices[invoice.qb_ref]['ShipMethodRefFullName']:
        vals['ship_method'] = qb_invoices[invoice.qb_ref]['ShipMethodRefFullName']
    if invoice.po_number != qb_invoices[invoice.qb_ref]['PONumber']:
        vals['po_number'] = qb_invoices[invoice.qb_ref]['PONumber']
    if vals:
        invoice.write(vals)







# -----------------------------------------------------------------------------
# create new invoices

# get invoices already existing in odoo
print("Getting QB invoice references from odoo")
qb_refs = rpc.execute('qb.invoice', 'read', qb_invoice_obj.search([('qb_ref', '!=', False)]), ['qb_ref'])
qb_ref_list = [x['qb_ref'] for x in qb_refs]

cols = [
    "TxnID",
    "RefNumber",
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
print("Getting new invoices")
cur.execute(sql, (sync_dt, ))
qb_rows = cur.fetchall()
qb_invoices = []
qb_customer_ids = []
for row in qb_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    if row_dict['TxnID'] in qb_ref_list:
        continue
    qb_invoices.append(row_dict)
    qb_customer_ids.append(row_dict['CustomerRefListID'])

# create qb invoices in odoo
print("Creating %s new invoices" % len(qb_invoices))
for invoice in qb_invoices:
    partner_id = odoo_qb_partner_map.get(invoice['CustomerRefListID'])
    if not partner_id:
        sys.exit("Failed to find customer on invoice %s" % invoice['RefNumber'])
    vals = {
        'name': invoice['RefNumber'],
        'qb_ref': invoice['TxnID'],
        'txn_date': invoice['TxnDate'].strftime("%Y-%m-%d %H:%M:%S"),
        'ship_date': invoice['ShipDate'] and invoice['ShipDate'].strftime("%Y-%m-%d %H:%M:%S") or False,
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

# get invoice lines already existing in odoo
print("Getting QB invoice line references from odoo")
qb_refs = rpc.execute('qb.invoice.line', 'read', qb_line_obj.search([('qb_ref', '!=', False)]), ['qb_ref'])
qb_ref_list = [x['qb_ref'] for x in qb_refs]

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
print("Getting new invoice lines")
cur.execute(sql, (sync_dt, ))
qb_rows = cur.fetchall()
qb_inv_lines = []
qb_inv_ids = []
qb_line_item_codes = []
for row in qb_rows:
    row_dict = {}
    for col in range(len(cols)):
        row_dict[cols[col]] = row[col]
    if row_dict['InvoiceLineTxnLineID'] in qb_ref_list:
        continue
    qb_inv_lines.append(row_dict)
    if row_dict['InvoiceLineItemRefListID'] and row_dict['InvoiceLineItemRefListID'] not in qb_line_item_codes:
        qb_line_item_codes.append(row_dict['InvoiceLineItemRefListID'])
    if row_dict['TxnID'] not in qb_inv_ids:
        qb_inv_ids.append(row_dict['TxnID'])

# get qb invoices from odoo
print("Getting QB invoice ref-id map from odoo")
qb_inv_ids = rpc.execute('qb.invoice', 'read', qb_invoice_obj.search([('qb_ref', '!=', False)]), ['qb_ref'])
qb_odoo_invs = {x['qb_ref']: x['id'] for x in qb_inv_ids}

# get odoo products
print("Getting odoo products")
odoo_prod_ids = template_obj.search([('qb_ref', 'in', qb_line_item_codes)])
odoo_prods = template_obj.browse(odoo_prod_ids)
qb_odoo_prods = {x.qb_ref: x.id for x in odoo_prods}

# create qb invoice lines in odoo
print("Creating %s new invoice lines" % len(qb_inv_lines))
for line in qb_inv_lines:
    qb_invoice_id = qb_odoo_invs.get(line['TxnID'])
    vals = {
        'qb_invoice_id': qb_invoice_id,
        'qb_ref': line['InvoiceLineTxnLineID'],
        'qb_line_seq_num': line['InvoiceLineSeqNo'],
        'product_tmpl_id': qb_odoo_prods.get(line['InvoiceLineItemRefListID']),
        'description': line['InvoiceLineDesc'].replace('\00', ''),
        'quantity': float(line['InvoiceLineQuantity'] or 0),
    }
    qb_line_obj.create(vals)






# close quickbooks connection
cur.close()
cxn.close()




# write now() to the config file sync_time
print("Saving timestamp of successful sync")
parser.set('QB', 'sync_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
fp = open(conf_file_name, 'w')
parser.write(fp)
fp.close()

print("Sync complete\n")

def signal_handler(sig, frame):
    # close quickbooks connection
    print('Closing Connections')
    cur.close()
    cxn.close()
    sys.exit("Exited early because of user interupt")

signal.signal(signal.SIGINT, signal_handler)
