# Data Cleaning and Data Quality: A Practical Manual

### Based on ColtraDataAI - for the non-technical reader who wants to understand what is actually happening

---

## Who this manual is for

This manual is written for someone who uses data every day, knows when something looks wrong in a spreadsheet, and wants to understand the science behind fixing it - without needing to write code or know statistics. If you have ever inherited a messy Excel file, tried to reconcile two lists that should match but do not, or wondered why a report came out wrong when the data looked fine, this manual is for you.

By the end, you will be able to hold a confident conversation with a data analyst, a software developer, or an AI consultant about data quality - and you will understand why tools like ColtraDataAI exist and what they are actually doing under the hood.

---

## Part One: The Foundations

### Chapter 1 - What is Data Science, really?

The phrase "data science" sounds intimidating. It sounds like mathematics, algorithms, and PhD theses. In practice, data science is about answering questions using information you have collected.

Think of it like being a detective. A detective has witness statements, CCTV footage, phone records, and financial transactions. The job is to look at all of that information, sort out what is reliable from what is unreliable, connect the dots, and reach a conclusion you can stand behind.

Data science is exactly that, but the witnesses are your spreadsheets, your databases, your accounting systems, and your CRM. The detective work is done partly by people and partly by software. The conclusion is a report, a chart, a prediction, or a recommendation.

There are several sub-disciplines within data science. The three most commonly discussed are:

**Data Engineering** - The plumbing. Building the pipes that collect, store, and move data from one place to another. When a developer talks about "pipelines," they mean automated systems that take data from a source (like a sales system), transform it, and deposit it somewhere useful (like a dashboard or a report). Data engineers build and maintain those pipes.

**Data Analysis** - The interpretation. Taking data that has already been collected and organised, and asking questions of it. What is trending up? What correlates with what? Which customers are most profitable? Data analysts do this work, often in tools like Excel, Python, or SQL. They produce insights.

**Machine Learning and AI** - The pattern recognition. Training computer models to spot patterns in large amounts of data and make predictions or decisions. This is what people mean when they talk about "AI." At its core, a machine learning model is a mathematical function that has been adjusted by seeing thousands of examples until it can generalise to new ones.

All three of these disciplines depend entirely on one thing: clean data. Dirty data fed into the most sophisticated AI in the world produces wrong answers, confidently delivered. This is so common in the industry that it has a name: **Garbage In, Garbage Out**, or GIGO.

---

### Chapter 2 - What is "dirty data" and why does it happen?

Before explaining what dirty data is, it helps to understand why it exists at all.

Data is created by people. People use different systems. Systems have different formats. Companies grow, merge, and change software. Processes evolve but the old data does not get updated. Staff enter the same information in slightly different ways. Automated imports sometimes break silently and no one notices until the report is wrong.

Here are the main categories of dirty data, with everyday examples:

**Missing values**
A field that should have a value but does not. A customer record with no phone number. An invoice with no due date. A shipment with no delivery date. Missing values are not always mistakes - sometimes the information genuinely was not captured. But they can cause calculations to fail or produce misleading results.

**Inconsistent formatting**
The same information written in different ways. "United Kingdom," "UK," "U.K.," and "GB" all mean the same thing to a human, but to a computer they are four completely different values. This breaks grouping, filtering, and any kind of reporting that depends on matching values.

**Duplicates**
The same record appearing more than once. This happens when data is imported from multiple sources, when forms are submitted twice, or when two systems are merged. Duplicates inflate counts and values - sales figures look higher than they are, stock counts are wrong, customer lists are padded.

**Wrong data types**
A number stored as text. A date stored as a plain string. A percentage stored as a decimal in one place and a whole number somewhere else. These cause calculations to fail silently or produce nonsense results.

**Values outside expected ranges**
A quantity of -50 items. A price of zero. A date in 1900. A postcode with seven letters. These are technically present but are almost certainly wrong. They are called **outliers** when they are extreme but possibly real, and **invalid values** when they simply cannot be correct.

**Referential integrity failures**
In linked datasets, one record refers to another that does not exist. An invoice linked to a customer ID that is not in the customer table. A shipment assigned to a warehouse code that has been retired. The link is broken.

**Encoding and character issues**
Accented characters, special symbols, or invisible whitespace that crept in during import. "Hernández" becomes "Hern?ndez." A name with a trailing space that does not match the same name without it. These are invisible to the naked eye but break exact matching.

---

### Chapter 3 - The vocabulary of data quality

These are the terms you will hear in any serious conversation about data, and what they actually mean:

**Schema** - The definition of a dataset's structure. A schema says: this table has these columns, each column holds this type of data, and these columns cannot be empty. Think of it as the rules for how data should be organised, written down in advance.

**Field / Column / Attribute** - These three words all mean the same thing in most contexts. A single piece of information within a record. In a spreadsheet, a column. In a database, a field or attribute.

**Record / Row** - A single entry in a dataset. One customer, one invoice, one shipment.

**Null / Blank / Empty** - A missing value. "Null" is the technical term from database science. All three mean: this field has no value.

**Standardisation** - Taking values that mean the same thing but are written differently, and converting them all to one agreed format. Turning "delivered," "dlvd," "complete," and "del" all into "Delivered."

**Validation** - Checking whether a value meets a rule. A postcode that does not match the correct format fails validation. An NHS number that fails its check-digit calculation fails validation. Validation does not fix the problem - it flags it.

**Transformation** - Calculating something new from existing data. Deriving the number of days between dispatch and delivery from two date fields. Calculating whether a stock level is below reorder point. Transformations add derived information.

**Pipeline** - An automated sequence of steps that takes raw data and produces a clean or processed version. The word comes from Unix computing, where you literally pipe the output of one command into the input of the next. A data pipeline does the same thing at scale.

**ETL** - Extract, Transform, Load. The classic pattern for data processing. Extract data from a source, transform it (clean it, reshape it, enrich it), then load it into its destination. This is what ColtraDataAI is doing when you upload a file and download a clean version.

**Deduplication** - The process of finding and removing duplicate records.

**Normalisation** - Making data consistent. In databases, normalisation has a specific technical meaning about table structure. In data quality, it usually means bringing values to a consistent standard (same units, same format, same casing).

**Audit trail** - A record of what was changed, when, and why. In data cleaning, this means logging every change made so you can review, explain, or reverse it.

**Data profiling** - Automatically summarising a dataset to understand its shape before cleaning. How many rows? How many nulls per column? What are the most common values? What are the min and max values? Profiling gives you the lay of the land before you start work.

**Check digit** - A number added to an identifier (like an NHS number or a barcode) that can be mathematically verified. If the check digit does not match, the number was entered incorrectly. This is a form of built-in self-validation.

**Canonical** - The agreed, official version of a value. When a system standardises "dlvd," "complete," and "del" all to "Delivered," then "Delivered" is the canonical form.

---

### Chapter 4 - How automated cleaning works

ColtraDataAI takes a file you upload and runs it through two layers of cleaning.

**Layer 1: Standard cleaning** applies to every file regardless of domain. This is the basic hygiene pass. It strips leading and trailing whitespace from text fields. It detects and flags empty values. It identifies columns that look like dates and parses them into a consistent format. It spots obvious duplicates. It standardises column names. This layer does not need to know anything about your business - it applies universal data quality rules.

**Layer 2: Domain cleaning** applies rules specific to your industry. This is where the intelligence lives. The app detects which domain your data belongs to (or you tell it), and then applies a set of rules written specifically for that context. A finance dataset gets different checks than a logistics dataset. A healthcare dataset has different validation requirements than a retail inventory.

The reason this distinction matters is that what counts as "wrong" depends entirely on context. A value of zero in a stock column might be fine - you are out of stock. A value of zero in a price column is almost certainly an error - nothing is free by default. The domain layer knows these distinctions.

---

## Part Two: The Seven Domains

Each chapter below describes one of ColtraDataAI's domain cleaners - what data it works with, what problems it finds, and what it does to fix them. The aim is to give you a clear picture of why these specific checks exist and what they prevent.

---

### Chapter 5 - Logistics and Supply Chain

**What this data looks like**

A logistics dataset tracks the movement of goods. It typically has columns for shipment or tracking references, carrier names, origin and destination locations, dispatch and delivery dates, weights, and a status field showing where in the journey a shipment currently is.

This data comes from courier systems, warehouse management software, freight platforms, and manual booking forms. When multiple carriers are used, the data often arrives in separate formats and has to be combined - which is where most of the inconsistency comes from.

**What goes wrong**

The most common problem is inconsistent status values. One carrier's system outputs "dlvd" while another outputs "complete" and a third outputs "Delivered." All three mean the same thing, but to any software trying to count delivered shipments, they look like three different statuses. Reports become unreliable.

Carrier names suffer the same problem. "DHL," "D.H.L.," "DHL Express," and "Deutsche Post DHL" might all refer to the same carrier depending on context. Filtering by carrier gives you incomplete results.

Weight fields often arrive in mixed units. One record is in kilograms, another in pounds, a third in grams. If you average these without standardising units first, the result is meaningless.

Date order problems are common and dangerous. A delivery date that appears before the dispatch date is impossible - it means something was entered wrongly. Left unchecked, this produces negative transit times which corrupt any analysis of delivery performance.

Duplicate shipments can occur when a booking is processed twice or when two systems both record the same movement. Duplicates inflate volume figures and distort carrier performance metrics.

**What ColtraDataAI does**

- Maps all status variants to a single canonical set: Delivered, In Transit, Out for Delivery, Pending, Collected, Delayed, Failed, Returned, Cancelled.
- Standardises carrier names so that reporting groups shipments correctly.
- Normalises weight units so comparisons are meaningful.
- Calculates transit time in days from dispatch to delivery dates, making performance analysis possible.
- Flags any row where delivery date is earlier than dispatch date as a date order error.
- Identifies probable duplicate shipments based on matching reference numbers.

**The business consequence of not cleaning this**

A logistics manager relying on dirty status data will have no reliable view of how many shipments are actually in progress versus delayed. Carrier performance reports will be wrong. Transit time averages will be distorted by impossible negative values. Duplicate shipments will overstate volumes and cost.

**Key terms to know**

AWB - Air Waybill. A tracking reference used in air freight.
Consignee - The recipient of a shipment.
Dispatch date vs delivery date - The day the item left the sender versus the day it arrived with the recipient. Transit time is the gap.
ETA - Estimated Time of Arrival.

---

### Chapter 6 - Finance and Accounting

**What this data looks like**

A finance dataset typically contains general ledger entries, journal lines, or transaction records. It has columns for account codes, account names, debit amounts, credit amounts, journal references, posting periods, VAT or tax codes, cost centres, and narrative descriptions.

This data comes from accounting systems like Sage, Xero, QuickBooks, or SAP. It is often exported for analysis, reconciliation, or audit preparation.

**What goes wrong**

Account codes are supposed to be uniform, but exports from some systems drop leading zeros. A code that should be "0700" comes through as "700." This makes it impossible to match codes against a chart of accounts.

VAT codes are tightly controlled in the UK. HMRC recognises specific codes for standard rate (S), zero rate (Z), exempt (E), and so on. Systems that allow free-text entry in the tax code field often accumulate variants like "Std," "Standard," "20%," and "S20" alongside the correct values. None of these will reconcile properly in a VAT return.

Journal references often have inconsistent formatting. "JNL001," "JNL 001," "jnl001," and "JNL-001" are all the same reference typed differently. Searching for a journal by reference becomes unreliable.

Accounting period fields are notoriously inconsistent. "Period 1," "P1," "April," "Apr-24," "2024-04" - all potentially meaning the same month, written differently by different users or exported from different system versions.

Narratives (the description of what a transaction is for) are supposed to explain journal entries for audit purposes. Blank narratives or generic ones like "correction" or "adj" are a red flag in any audit. They suggest the person posting did not document their work.

The trial balance check is the most fundamental test in accounting: the sum of all debits must equal the sum of all credits. If they do not, something is wrong. ColtraDataAI flags this automatically.

**What ColtraDataAI does**

- Pads account codes to 4 digits so "700" becomes "0700."
- Classifies accounts by their numeric range against standard UK nominal code ranges (Fixed Assets 0-999, Current Assets 1000-1999, Current Liabilities 2000-2999, and so on).
- Validates VAT codes against recognised UK VAT scheme codes and flags anything outside that set.
- Strips and standardises journal references.
- Maps period values to standard labels.
- Flags missing or non-numeric cost centres.
- Checks whether total debits and total credits balance.
- Flags blank or suspiciously generic narratives.

**The business consequence of not cleaning this**

An accountant or auditor working with dirty financial data risks misclassifying transactions, failing to reconcile VAT correctly, and presenting a trial balance that does not balance. In an audit context, unexplained narratives and inconsistent references raise questions about the quality of record-keeping. The reputational and regulatory consequences can be significant.

**Key terms to know**

Chart of Accounts - The master list of all account codes and their descriptions used by a business.
General Ledger (GL) - The central record of all financial transactions.
Nominal code - The numeric code assigned to each type of income or expenditure in the chart of accounts.
Trial balance - A report listing all account balances. If accounting is correct, debits and credits must be equal.
VAT code - A short code identifying which VAT rate or scheme applies to a transaction.
Cost centre - A department or division code used to allocate expenses.
Journal - A manual accounting entry, typically used for adjustments and corrections.

---

### Chapter 7 - Import and Export Trade

**What this data looks like**

A trade dataset records the movement of goods across international borders. It has columns for commodity codes (called HS codes), countries of origin and destination, declared values, currencies, units of measure, quantities, trade direction (import or export), and customs references.

This data comes from customs declarations, freight forwarders, customs agents, and trade compliance systems.

**What goes wrong**

HS codes are the international system for classifying goods in trade. Every product traded internationally has a code. These codes are 6 digits at the international level, extended to 8 or 10 digits in some countries. The problem is that these codes often arrive with the wrong number of digits, missing leading zeros, or containing letters and symbols that should not be there.

Country names and codes are inconsistently recorded. "United Kingdom," "UK," "U.K.," "GB," and "GBR" all refer to the same country. The international standard is ISO 3166-1 alpha-2 (two-letter codes: GB, US, DE, FR). Analysis and compliance reporting requires consistent country codes.

Currency codes have the same problem. The international standard is ISO 4217 (three letters: GBP, USD, EUR). Systems that allow free text often accumulate "pounds," "sterling," "£," "GBP," and "Pound" alongside the correct code.

Unit of measure fields are inconsistently recorded. "kilograms," "kg," "KG," "Kg," and "Kilos" all mean the same thing but will not group together without standardisation.

Declared values must be positive. A zero or negative declared value on a customs document is not just a data error - it can trigger compliance problems. These need to be flagged immediately.

**What ColtraDataAI does**

- Validates HS codes: they must be 6 to 10 digits, numeric only, and are zero-padded to 6 digits where they fall short.
- Maps country names and variants to their correct ISO 3166-1 alpha-2 two-letter codes.
- Standardises currency codes to ISO 4217 three-letter format.
- Standardises units of measure to canonical labels.
- Detects whether each record represents an import or an export based on column names and direction fields.
- Flags any declared value that is zero or negative.

**The business consequence of not cleaning this**

Incorrect HS codes on customs declarations are a compliance risk. Misdeclared codes can result in the wrong duty rate being applied, which means either overpaying or (more seriously) underpaying import duty. Country and currency inconsistencies break trade statistics and customs reporting. Zero or negative declared values can trigger audit flags with HMRC or customs authorities.

**Key terms to know**

HS Code - Harmonised System code. The international classification number for traded goods, maintained by the World Customs Organization.
TARIC - The EU's extended tariff code, building on HS codes.
ISO 3166-1 alpha-2 - The international standard for two-letter country codes (GB, US, DE, etc.).
ISO 4217 - The international standard for three-letter currency codes (GBP, USD, EUR, etc.).
FOB value - Free On Board. The value of goods at the point of export, excluding shipping and insurance.
CIF value - Cost, Insurance, Freight. The value including shipping and insurance to the point of import.
MRN - Movement Reference Number. A customs reference assigned when a declaration is submitted.

---

### Chapter 8 - Retail and Inventory

**What this data looks like**

A retail inventory dataset tracks products, their prices, their costs, and their stock levels. It has columns for SKUs (product codes), product names, selling prices, cost prices, stock quantities, reorder points, categories, supplier names, and barcodes.

This data comes from EPOS systems (tills), warehouse management systems, stock control spreadsheets, and supplier data feeds.

**What goes wrong**

SKUs (Stock Keeping Units - unique product codes) are supposed to be consistent identifiers. But they often have trailing spaces, inconsistent casing, or small variations ("SKU001," "sku001," "SKU 001") that cause the same product to appear as different items in reports.

Price and cost conflicts are a serious business problem. If the buying price (what you paid the supplier) is higher than the selling price (what you charge the customer), you are selling at a loss. This can happen through entry errors, system migrations, or promotional updates that were only applied to one field. The cleaner flags every row where cost exceeds selling price.

Negative stock levels are mathematically possible in some systems (usually meaning more was sold or written off than was recorded as received), but they represent a real problem. You cannot physically have -10 units on a shelf. These need to be investigated.

Items at or below their reorder point need attention. If you have set a reorder point of 20 units for a product and stock falls to 15, the system should be prompting a purchase order. Clean, flagged data makes this visible.

Barcodes follow international standards. EAN-13 barcodes (the standard 13-digit barcode on most retail products) have a check digit that can be mathematically verified. A barcode where the check digit does not match was either entered incorrectly or printed incorrectly. UPC-A (the American 12-digit standard) works the same way.

Duplicate SKUs in a dataset mean the same product code is assigned to two different records - which will cause all manner of confusion in stock reporting and order fulfilment.

Zero prices on active products mean an item will be invoiced at nothing, giving it away for free by default.

**What ColtraDataAI does**

- Standardises SKUs: strips whitespace and converts to uppercase.
- Flags every product where cost price exceeds selling price.
- Flags every product where stock quantity is negative.
- Flags every product where stock is at or below its reorder point.
- Validates EAN-13 and UPC-A barcodes by calculating the expected check digit and comparing.
- Standardises category names to title case.
- Identifies duplicate SKUs.
- Flags products with a zero selling price.

**The business consequence of not cleaning this**

A retailer operating on dirty inventory data risks selling at a loss without knowing it, running out of stock without a prompt to reorder, losing sales to incorrect stock counts, and having scanning failures at the till due to invalid barcodes. In a business where margins are tight, any of these can have a direct impact on profitability.

**Key terms to know**

SKU - Stock Keeping Unit. A unique identifier for a product variant.
EAN-13 - European Article Number. The 13-digit barcode standard used on most retail products worldwide.
UPC-A - Universal Product Code. The 12-digit barcode standard predominantly used in North America.
GTIN - Global Trade Item Number. An umbrella term that encompasses EAN and UPC.
Check digit - The final digit in a barcode, calculated from the other digits. If it does not match, the barcode is invalid.
Reorder point - The stock level at which a new purchase order should be raised.
Margin - The difference between selling price and cost price, expressed as a percentage of the selling price.

---

### Chapter 9 - Professional Services and Consulting

**What this data looks like**

A consulting dataset tracks time, billing, and project performance. It has columns for project or matter codes, client names, consultant names, billable hours, total hours worked, budget hours, day rates, hourly rates, work dates, and project status.

This data comes from timesheet systems, project management tools, practice management software (common in law and accountancy firms), and billing systems.

**What goes wrong**

Timesheet data is notoriously prone to entry errors. Someone accidentally enters 244 hours instead of 24.4. A daily total exceeds 24 hours, which is physically impossible. These outliers corrupt averages and make performance reports look absurd.

Day rates and hourly rates can end up as zero or negative through system errors, import failures, or formula mistakes. A zero rate means work is being recorded but will never generate revenue. This is a silent billing leak.

Project codes need to be consistent to group time and cost correctly. Spaces, mixed case, and typos cause entries for the same project to scatter across reports.

Utilisation rate is one of the most important metrics in any consulting or professional services business. It measures what percentage of a consultant's time is billable to clients (as opposed to internal, non-chargeable work). The formula is: billable hours divided by total hours, multiplied by 100. Without clean hour data, this metric is meaningless.

Overruns are when a project consumes more hours than were budgeted. Early detection of overruns lets a practice manager have a conversation with the client or adjust the budget before the overrun becomes a write-off.

Project status fields accumulate the same kind of inconsistency as any other status column. "In progress," "active," "live," "ongoing" all mean the same thing, but they will not group together in a pivot table.

**What ColtraDataAI does**

- Flags rows where daily hours exceed 24 or weekly totals exceed 168 (impossible values).
- Flags zero or negative day rates and hourly rates.
- Standardises project codes: strips whitespace and converts to uppercase.
- Calculates utilisation rate for each consultant where billable and total hours are present.
- Flags projects where actual hours exceed budgeted hours (overrun detection).
- Standardises project status values to a canonical set: Active, Completed, On Hold, Cancelled, Won, Lost.

**The business consequence of not cleaning this**

A consulting firm that cannot trust its timesheet data cannot bill accurately, cannot measure utilisation, and cannot manage project profitability. Overruns that go undetected until the end of an engagement erode margin. Utilisation metrics built on dirty data lead to staffing decisions based on fiction.

**Key terms to know**

Billable hours - Hours that can be charged to a client.
Utilisation rate - The percentage of total working hours that are billable. A key performance metric in consulting and professional services.
Overrun - When actual hours or costs exceed the budgeted amount.
Write-off - Hours or costs that were incurred but will not be charged to the client.
Day rate - The standard daily charge for a consultant's time.
Matter - The legal/professional services term for a project or case.
Fee earner - A person whose time is billed to clients. The professional services equivalent of "consultant."

---

### Chapter 10 - Healthcare (Operational)

**What this data looks like**

An operational healthcare dataset tracks appointments, patient identifiers, clinical codes, waiting times, and staff categories. It has columns for NHS numbers, ICD-10 diagnosis codes, appointment statuses, referral dates, appointment dates, staff roles, postcodes, wards, and patient names.

This data comes from patient management systems, appointment booking systems, and NHS reporting extracts.

**What goes wrong**

NHS numbers are the most important patient identifier in the NHS system. Each patient has a unique 10-digit NHS number. These numbers use a Modulus 11 algorithm to generate a check digit (the last digit). If the number you have does not produce the right check digit, it was either entered incorrectly or it belongs to a different patient. Using the wrong NHS number in any clinical or administrative context is a patient safety and data protection risk.

ICD-10 codes are the international system for classifying diseases and diagnoses. Every diagnosis should be recorded using a code from this system (for example, J45 for asthma or E11 for type 2 diabetes). The format is one letter followed by two digits and an optional decimal extension. Free-text entries or codes in the wrong format cannot be used for clinical reporting, commissioning, or research.

Appointment status fields accumulate variants just like any other status field. "DNA," "Did Not Attend," "DidNotAttend," "dna," "no show" - all mean the same thing but will not aggregate correctly without standardisation.

Waiting time calculation is a key NHS performance metric. The time between referral date and appointment date (in calendar days) must be calculated consistently. Errors in date entry mean some waiting times appear negative or impossibly long.

Postcodes are used for mapping patient populations, planning services, and commissioning. Postcodes in the wrong format cannot be geocoded or matched to geographic areas.

**What ColtraDataAI does**

- Validates NHS numbers using the Modulus 11 check digit algorithm and flags any that fail.
- Validates ICD-10 codes against the standard format and flags non-conforming entries.
- Standardises appointment status values to a canonical set: Attended, DNA (Did Not Attend), Cancelled by Patient, Cancelled by Provider, Booked, Rescheduled.
- Calculates waiting time in days from referral date to appointment date.
- Standardises staff category and grade labels.
- Validates UK postcodes against the standard format.

**The business consequence of not cleaning this**

In healthcare, dirty data is not just operationally inconvenient - it has patient safety implications. An incorrect NHS number means a patient's record is linked to the wrong person. An invalid ICD-10 code means a diagnosis does not appear in any reporting or research. Inaccurate waiting time data masks capacity problems and affects commissioning decisions. NHS organisations are subject to data quality inspections, and poor-quality data can affect regulatory ratings.

**Key terms to know**

NHS number - The unique 10-digit identifier assigned to every patient registered with the NHS.
Modulus 11 - A mathematical algorithm for generating and verifying check digits. Used for NHS numbers and other identifiers.
ICD-10 - International Classification of Diseases, 10th revision. The global standard for coding diagnoses and health conditions.
DNA - Did Not Attend. Appointment where the patient did not show up without cancelling.
Referral - A request from one clinician for a patient to see another (e.g. GP referring to a consultant).
Waiting time - The gap in days between referral and first appointment. A key NHS performance metric.
Postcode - The UK postal code. Used in healthcare for geographic analysis and service planning.
Modulus 11 check digit - A digit appended to a number that allows its validity to be verified mathematically.

---

### Chapter 11 - Small and Medium Enterprises (SME)

**What this data looks like**

An SME dataset covers the general operational data of a small business: customer and supplier records, invoices, payments, and contact information. It has columns for postcodes, National Insurance numbers, VAT registration numbers, Companies House numbers, invoice numbers, invoice dates, due dates, payment dates, amounts, phone numbers, payment terms, and customer names.

This is the "general business administration" domain - the data that falls outside more specialist categories but is crucial to running any UK small business.

**What goes wrong**

UK postcodes are used for delivery, marketing, and compliance. An incorrectly formatted postcode will fail address validation and cannot be matched to geographic areas. The UK postcode format is specific (combinations of letters and numbers in a defined pattern), and there are many ways to get it slightly wrong.

National Insurance (NI) numbers are required for payroll. They follow the pattern AB123456C - two letters, six digits, one letter. Certain letter combinations at the start are not used (for example, "D" and "F" are invalid as the first letter). An incorrectly formatted NI number will fail HMRC submissions.

VAT registration numbers in the UK follow specific formats. Standard UK VAT numbers are "GB" followed by 9 digits. Government departments and NHS bodies use slightly different formats. ColtraDataAI validates the format and flags anything that does not conform.

Companies House numbers must be 8 characters. UK limited companies registered in England and Wales have numbers that are 8 digits, zero-padded. Scottish companies start with "SC," Northern Ireland companies with "NI." Numbers shorter than 8 characters were padded with leading zeros in the original registration but often lose them during data entry or export.

Overdue invoices are a cash flow problem. An invoice is overdue when its due date has passed and no payment date has been recorded. Identifying these automatically without having to scroll through a spreadsheet is exactly the kind of routine task that should be automated.

UK phone numbers are entered in countless formats: "07700 900000," "07700900000," "+447700900000," "447700900000," "0044 7700 900000." For any system that needs to dial, text, or deduplicate contacts, a consistent format is essential. The international standard is E.164: a plus sign, the country code, and the number without spaces or punctuation (+447700900000).

Payment terms such as "Net 30," "30 days," "net30," "30 Day," and "month end" all represent payment conditions but will not group or filter correctly without standardisation.

**What ColtraDataAI does**

- Validates UK postcodes against the standard regular expression for UK postcode format.
- Validates NI numbers against the AB123456C pattern and checks for invalid prefix combinations.
- Validates UK VAT numbers (GB + 9 digits, or the government/health body variants).
- Validates Companies House numbers: flags those not matching 8-character format and pads short numeric entries with leading zeros.
- Identifies overdue invoices: any row where the due date is in the past and no payment date is recorded.
- Standardises UK phone numbers to the international E.164 format (+44...).
- Standardises payment terms to canonical forms: Net 30, Net 60, Net 90, etc.

**The business consequence of not cleaning this**

A small business operating with dirty administrative data risks failed payroll submissions (invalid NI numbers), failed VAT returns (invalid VAT numbers), undeliverable post (invalid postcodes), and missed debt collection (unidentified overdue invoices). The overdue invoice detection alone can have a direct and immediate impact on cash flow if the list has been left unchecked.

**Key terms to know**

NI number - National Insurance number. Every UK worker has one, used for tax and benefits. Format: AB123456C.
VAT number - Value Added Tax registration number. Required for VAT-registered businesses. UK format: GB followed by 9 digits.
Companies House number - The unique registration number assigned to every UK company. Must be 8 characters.
E.164 - The international standard format for phone numbers: + country code + number, no spaces (e.g. +447700900000).
Overdue invoice - An invoice where the due date has passed with no payment recorded.
Payment terms - The agreed timeframe for payment. Net 30 means payment due within 30 days of invoice date.
Regular expression (regex) - A pattern used to check whether a string of text matches a defined format. Used to validate postcodes, NI numbers, and similar structured identifiers.

---

## Part Three: The Bigger Picture

### Chapter 12 - How data quality fits into AI and machine learning

This is where the connection between data cleaning and artificial intelligence becomes clear.

Machine learning models are trained by feeding them examples. An AI that learns to predict whether a customer will pay on time is trained on thousands of historical invoice records - each with a set of features (invoice amount, customer history, payment terms, industry) and a known outcome (paid on time or overdue). The model learns which features predict which outcome.

If the training data is dirty, the model learns from dirty examples. It learns that "Net 30" and "net30" are different payment terms, because they look different to a computer. It learns that "UK" customers behave differently from "United Kingdom" customers, because they appear as separate categories. It learns patterns that are artefacts of data entry inconsistency rather than genuine patterns in the business.

The result is a model with poor accuracy on real-world data, or a model that picks up spurious correlations that do not generalise.

This is why data quality is not just a bookkeeping concern or a spreadsheet hygiene issue. It is the foundation of any reliable analytical or AI system. Data scientists routinely say they spend 60-80% of their time cleaning and preparing data before any modelling begins. ColtraDataAI automates the most repeatable parts of that work.

**The concept of data lineage** - Where did a piece of data come from, and what happened to it between its source and its current location? Being able to answer this question is increasingly important in regulated industries. If an auditor asks why a particular number appears in a report, you need to be able to trace it back to its source. Clean, well-documented data with an audit trail supports this.

**The concept of data governance** - The policies and processes that ensure data is collected, stored, and used correctly across an organisation. This includes who is allowed to enter data, in what format, through which systems, and who is responsible for its quality. Governance is the organisational layer; cleaning tools are the technical layer.

---

### Chapter 13 - Terms you will hear in any data science conversation

This is a quick reference for language that comes up regularly in data-adjacent discussions. Understanding these terms will let you engage with confidence.

**DataFrame** - A table of data in memory, used in Python (via a library called pandas). When a developer says "I have a DataFrame," they mean a spreadsheet-like object with rows and columns that they are manipulating in code.

**SQL** - Structured Query Language. The standard language for querying and manipulating data held in relational databases. When someone says "I'll write a query," they usually mean SQL. It reads like near-English: "SELECT customer_name, invoice_total FROM invoices WHERE due_date < today AND payment_date IS NULL" means "give me the customer names and amounts for all invoices that are past due and unpaid."

**Database vs spreadsheet** - A spreadsheet (Excel, Google Sheets) is a file. A database is a system that stores data in tables, manages relationships between them, and lets multiple users query the same data simultaneously without corrupting it. Databases are faster, more reliable, and better for large volumes of data.

**API** - Application Programming Interface. A standardised way for one software system to talk to another. When ColtraDataAI's Enterprise API is described, it means other software can send data to ColtraDataAI and receive cleaned data back automatically, without any human uploading a file.

**JSON** - JavaScript Object Notation. A format for sending data between systems via APIs. It looks like structured text with curly braces and colons. Not something you need to write, but worth recognising if a developer shows you what an API response looks like.

**Regex (regular expression)** - A pattern matching language used to check whether text conforms to a format. The UK postcode validator and NHS number format check both use regex. You do not need to write them, but knowing what they are helps when a developer mentions "validating against a regex."

**Python** - The most widely used programming language in data science. If someone is building a data tool, a cleaning script, or a machine learning model, it is most likely in Python.

**Pandas** - A Python library for working with tabular data. It is to Python what Excel is to a business analyst - the main tool for reading, manipulating, and writing data tables.

**Outlier** - A value that is unusually far from the typical range for that column. May be an error (a transposed digit) or may be a genuine extreme value worth investigating. Outlier detection is the process of finding these automatically.

**Feature engineering** - In machine learning, a "feature" is an input variable used to make a prediction. Feature engineering is the process of creating new, more informative features from raw data. For example, deriving "days since last payment" from a payment date is feature engineering.

**Model** - A mathematical function that has been trained on data. A model takes inputs (features) and produces an output (a prediction, a classification, a score). The quality of the model depends entirely on the quality of the data it was trained on.

**Accuracy, Precision, Recall** - Three ways of measuring how well a model performs. Accuracy is the proportion of predictions that are correct. Precision is: of all the things the model predicted were positive, how many actually were? Recall is: of all the actual positive cases, how many did the model correctly identify? These are often in tension - a model can be tuned to be more precise (fewer false positives) or more thorough (fewer false negatives) depending on what matters most.

**Bias** - In the data science context, bias means that a model systematically gets things wrong in a particular direction, often because the training data over-represented or under-represented certain groups or scenarios. Biased data produces biased models.

**Overfitting** - When a model learns the training data too well, including its noise and errors, and then fails to generalise to new data. A model that overfits is memorising rather than learning.

---

### Chapter 14 - Conversations you can now have

Based on what is in this manual, here are the kinds of discussion points you can now engage with confidently:

**With a data analyst:**
"Our logistics data has mixed status values coming from three different carrier APIs. We standardise them to a canonical set before loading. What would you recommend for handling statuses that do not map to any known value?"

**With a developer:**
"The finance export is dropping leading zeros on nominal codes. Should we be padding them at ingest in the pipeline, or enforcing the format at the source system?"

**With an AI consultant:**
"We are seeing high variance in our invoice payment predictions. Given that our training data has known inconsistencies in payment terms formatting, could that be contributing to the model noise?"

**With a product or business owner:**
"The healthcare dataset has NHS number validation failures on about 3% of records. Before we do any analysis, we need to resolve those - either by sourcing the correct numbers or excluding those records, because basing any reporting on incorrect patient identifiers is a governance risk."

**With an auditor:**
"Every change made by the cleaning tool is logged. We can show you the original value, the corrected value, and the rule that was applied. The audit trail is part of the output."

---

## Appendix: Quick Reference Glossary

| Term | Plain English meaning |
|---|---|
| API | A way for software systems to talk to each other automatically |
| Audit trail | A record of what was changed, when, and why |
| Canonical | The agreed, official version of a value |
| Check digit | A calculated digit that verifies an identifier was entered correctly |
| Data governance | The policies that control how data is collected, stored, and used |
| Data lineage | Being able to trace where data came from and what happened to it |
| DataFrame | A table of data being manipulated in code |
| Data profiling | Automatically summarising a dataset before cleaning |
| Deduplication | Removing duplicate records |
| EAN-13 | The 13-digit barcode standard used on most retail products |
| E.164 | International format for phone numbers (+44...) |
| ETL | Extract, Transform, Load - the standard pattern for data processing |
| Feature | An input variable used to make a prediction in a machine learning model |
| GIGO | Garbage In, Garbage Out - dirty data produces wrong outputs |
| HS code | Harmonised System code for classifying traded goods internationally |
| ICD-10 | International disease classification system for medical diagnoses |
| ISO 3166-1 | International standard for two-letter country codes |
| ISO 4217 | International standard for three-letter currency codes |
| JSON | A text format for sending data between systems |
| Modulus 11 | A mathematical algorithm for generating check digits |
| NHS number | The unique 10-digit identifier for every NHS patient |
| Normalisation | Making data consistent in format and values |
| Null | A missing value |
| Outlier | A value unusually far from the typical range |
| Overfitting | When a model memorises training data instead of learning patterns |
| Pandas | The main Python library for working with tabular data |
| Pipeline | An automated sequence of data processing steps |
| Python | The main programming language used in data science |
| Regex | A pattern for checking whether text matches a defined format |
| Schema | The definition of a dataset's structure and rules |
| SKU | Stock Keeping Unit - a unique product identifier |
| SQL | The standard language for querying databases |
| Standardisation | Converting values to a single agreed format |
| TARIC | The EU's extended tariff code for traded goods |
| Trial balance | An accounting check that total debits must equal total credits |
| Utilisation rate | Billable hours as a percentage of total hours worked |
| Validation | Checking whether a value meets a rule |
| VAT code | A code identifying which VAT rate applies to a transaction |

---

*This manual was written as a companion to ColtraDataAI, built by Coltrane Ltd. It is intended to give non-technical readers a genuine working understanding of data quality - not a superficial overview, but enough to participate in the conversations that matter.*
