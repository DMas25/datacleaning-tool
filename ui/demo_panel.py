"""Live Demo panel — ColtraDataAi.

Self-contained panel that runs each domain cleaner on pre-built messy
sample data. No file upload, no email gate, no subscription required.
Renders via pages/2_Live_Demo.py.
"""
from __future__ import annotations

import io
from typing import Any

import pandas as pd
import streamlit as st

from config.branding_config import branding as BRAND

PRIMARY = BRAND["primary_colour"]
ACCENT  = BRAND.get("accent_colour", "#2E86AB")
SUCCESS = BRAND.get("success_colour", "#46D324")
WARNING = BRAND.get("warning_colour", "#F59E0B")
DANGER  = BRAND.get("danger_colour", "#DC2626")


# =============================================================================
# EMBEDDED SAMPLE DATA — one messy CSV per domain
# =============================================================================

_FINANCE_CSV = """\
account_code,debit,credit,vat_code,journal_ref,period,cost_centre,narrative
1,500.00,,T1,JNL 001,1,,
100,,500.00,T1,JNL001,1,200,Invoice payment received
45,125.00,,T99,jnl-002,Feb,ABC,
45,125.00,,T99,jnl-002,Feb,ABC,
1200,300.00,,T1,JNL  003,2,100,payment
,50.00,,ZZ,JNL004,2,,N/A
4000,250.00,,T1,JNL005,3,100,material purchase
2200,,200.00,T1,JNL006,3,100,VAT control
3000,1000.00,,T1,JNL007,3,100,equity contribution
4100,,800.00,T1,JNL008,3,100,consulting fees
"""

_LOGISTICS_CSV = """\
tracking_number,carrier,status,dispatch_date,delivery_date,weight,weight_unit
TRK001,DHL,In Transit,2024-01-10,2024-01-15,25.5,KG
TRK002,fedex,delivered,2024-01-12,2024-01-14,3.2,lbs
TRK003,UPS,in-transit,2024-01-11,2024-01-09,10.0,kg
TRK004,DHL Express,DELIVERED,2024-01-13,2024-01-16,500,g
TRK001,DHL,In Transit,2024-01-10,2024-01-15,25.5,KG
TRK005,Royal Mail,pending,2024-01-14,,8.1,Kg
TRK006,fedex express,intransit,2024-01-15,2024-01-18,2.0,LBS
TRK007,UPS,Out For Delivery,2024-01-16,2024-01-17,15.0,kg
TRK008,DHL,returned,2024-01-10,2024-01-20,7.3,KG
TRK009,Yodel,lost,2024-01-09,2024-01-09,4.5,kg
TRK010,Hermes,Attempted Delivery,2024-01-11,2024-01-13,1.8,kg
"""

_TRADE_CSV = """\
hs_code,country,currency,declared_value,shipment_ref
9401,United Kingdom,GBP,15000.00,SHP-001
8471.30,USA,USD$,8500.00,SHP-002
8517,Germany,EUR,22000.00,SHP-003
0901.21.00,France,EUR,4500.00,SHP-004
2701,China,CNY,1200000.00,SHP-005
030200,JPN,JPY,850000.00,SHP-006
852872,UK,GBP,-500.00,SHP-007
611020,United States of America,US$,3200.00,SHP-008
300490,Deutschland,EUR,0.00,SHP-009
851762,Peoples Republic of China,CNY,650000.00,SHP-010
940130,GB,GBP,8900.00,SHP-011
220421,Brazil,BRL,25000.00,SHP-012
"""

_RETAIL_CSV = """\
sku,product_name,price,cost,stock_level,reorder_point,barcode
SKU001,Blue T-Shirt,15.99,12.50,45,10,5012345678900
SKU002,Red Jeans,49.99,60.00,8,5,4006381333931
SKU003,White Trainer,89.99,45.00,-12,20,0012345678905
SKU001,Blue T-Shirt,15.99,12.50,45,10,5012345678900
SKU004,Green Hoodie,35.00,35.00,2,15,9780201379624
SKU005,Black Cap,12.50,8.00,30,10,
SKU006,Yellow Shorts,25.00,18.00,100,25,1234567890128
SKU007,Grey Socks,5.99,2.50,250,50,5012345678901
SKU008,Purple Bag,45.00,48.00,0,10,4006381333948
SKU009,Orange Hat,19.99,15.00,3,10,007301000111
SKU010,Pink Scarf,22.00,16.00,85,20,9780201379624
"""

_CONSULTANT_CSV = """\
consultant_name,project_code,hours,day_rate,billable,budget_hours,client
Alice Smith,PROJ-001,8.0,650.00,True,40.0,Acme Corp
Bob Jones,PROJ-001,26.5,550.00,True,40.0,Acme Corp
Carol White,PROJ-002,7.5,700.00,False,30.0,Globex Ltd
Dan Brown,PROJ-002,8.0,0.00,True,30.0,Globex Ltd
Emma Davis,PROJ-003,48.0,800.00,True,100.0,Initech
Frank Wilson,PROJ-003,8.0,-500.00,True,100.0,Initech
Grace Lee,PROJ-004,7.0,600.00,True,20.0,Umbrella
Henry Taylor,PROJ-004,7.5,600.00,True,20.0,Umbrella
Iris Clark,PROJ-005,8.0,450.00,True,16.0,Massive Dynamics
Jack Moore,PROJ-005,9.0,450.00,True,16.0,Massive Dynamics
"""

_HEALTHCARE_CSV = """\
nhs_number,icd10_code,appointment_status,appointment_date,waiting_days
943 476 5919,J18.9,Attended,2024-01-15,42
9434765929,A0,Did Not Attend,2024-01-20,28
012 345 6789,F32.1,attended,2024-01-22,15
123 456 7890,Z00.0,CANCELLED,2024-01-25,7
401 023 2137,G35,Attended,2024-01-28,63
943 476 5919,J18.9,Attended,2024-01-15,42
999 999 9999,K29.7,dna,2024-02-01,130
432 109 8765,B20,Booked,2024-02-05,14
876 543 2109,H40.1,attended,2024-02-08,21
111 222 3333,M79.3,Cancelled,2024-02-10,35
"""

_SME_CSV = """\
company_name,postcode,vat_number,company_number,invoice_number,invoice_date,due_date,amount,phone
Acme Supplies Ltd,SW1A 1AA,GB123456789,12345678,INV-001,2024-01-05,2024-01-19,2500.00,07700 900123
Beta Services,EC2A 4NE,GB987654321,87654321,INV-002,2024-01-10,2024-01-24,1800.00,+44 20 7946 0958
Gamma Tech,ZZ9 9ZZ,GB123,9999999,INV-003,2024-01-15,2024-01-29,3200.00,0800 555 0199
Delta Consulting,W1A 0AX,GB111222333,1234567A,INV-004,2024-01-20,2024-02-03,950.00,07700900456
Epsilon Ltd,,GB444555666,11223344,INV-005,2024-01-25,2024-01-11,4100.00,07700 900 789
Zeta Corp,NW1 4NE,444555666,22334455,INV-006,2024-02-01,2024-02-15,720.00,02079460000
Eta Ltd,SW1A 2AA,GB777888999,33445566,INV-007,2024-01-08,2024-01-22,600.00,07700900111
Theta Ltd,M1 1AE,GB000111222,44556677,INV-008,2024-01-12,2024-01-26,1500.00,(0161) 555-1234
Iota Systems,E14 5AB,GB333444555,55667788,INV-009,2024-01-18,2024-02-01,890.00,07700900222
Kappa Ltd,BS1 4DJ,GB666777888,66778899,INV-010,2024-01-22,2024-02-05,2200.00,07700900333
"""

_HOSPITALITY_CSV = """\
booking_ref,room_type,check_in,check_out,rate,guests,status,channel
BK001,SGL,2024-03-01,2024-03-03,89.00,1,Confirmed,Direct
BK002,DBL,2024-03-05,2024-03-08,129.00,2,confirmed,Booking.com
BK003,twin,2024-03-10,2024-03-09,95.00,2,CONFIRMED,OTA
BK004,SUPERIOR DBL,2024-03-12,2024-03-15,159.00,0,Cancelled,corp
BK005,suite,2024-03-18,2024-03-20,350.00,2,no show,direct
BK001,SGL,2024-03-01,2024-03-03,89.00,1,Confirmed,Direct
BK006,family rm,2024-03-22,2024-03-25,175.00,-1,confirmed,Airbnb
BK007,executive,2024-03-28,2024-03-31,220.00,2,BOOKED,corporate
BK008,DBL,2024-04-02,2024-04-05,135.00,2,Cancelled,booking.com
BK009,STD,2024-04-08,2024-04-12,99.00,3,checked in,DIRECT
BK010,Pent house,2024-04-15,2024-04-20,850.00,4,Pending,Travel agent
"""

_CLINICAL_CSV = """\
Trial_ID,Principal_Investigator,Facility_Site,Phase,Status
nct 49211,Dr. John Smith,Mayo Clinic,Phase II,Recruiting
NCT-051122,J. Smith,Mayo Clinic,Phase II,Recruiting
nct0049211,Smith John,Mayo Clinic,Phase II,Completed
NCT:88231,John A. Smith MD,Mayo Clinic,Phase I,Active
NCT 00511220,Dr. Sarah Jones,Stanford Med,Phase III,Completed
NCT 39100,Sarah Jones MD,Stanford Med,Phase III,Completed
NCT 10044,S. Jones,Stanford Med,Phase I,Active
NCT 88823,Sarah E. Jones,Johns Hopkins,Phase II,Recruiting
NCT 22201,Dr. Emily Carter,Cleveland Clinic,Phase II,Active
NCT 33902,James Okafor PhD,Johns Hopkins,Phase III,Recruiting
"""


# =============================================================================
# SCENARIO DEFINITIONS
# =============================================================================

def _make_scenarios() -> list[dict]:
    """Build the ordered list of demo scenarios with their runner functions."""

    # Import cleaners lazily so import errors don't break the whole panel
    from core.cleaner import CleaningOptions, apply_cleaning
    from core.finance_cleaner import apply_finance_cleaning
    from core.logistics_cleaner import apply_logistics_cleaning
    from core.trade_cleaner import apply_trade_cleaning
    from core.retail_cleaner import apply_retail_cleaning
    from core.consultant_cleaner import apply_consultant_cleaning
    from core.healthcare_cleaner import apply_healthcare_cleaning
    from core.sme_cleaner import apply_sme_cleaning
    from core.hospitality_cleaner import apply_hospitality_cleaning
    from core.clinical_cleaner import apply_clinical_cleaning

    def _base_options(dataset_type: str = "General") -> CleaningOptions:
        return CleaningOptions(
            remove_duplicates=True,
            trim_whitespace=True,
            standardise_headers=True,
            dataset_type=dataset_type,
        )

    def _run_finance(raw_df: pd.DataFrame) -> dict:
        from core.cleaner import apply_cleaning
        base = apply_cleaning(raw_df, _base_options("Finance"))
        domain = apply_finance_cleaning(base.cleaned_df)
        return {"base": base, "domain": domain, "kind": "finance"}

    def _run_logistics(raw_df: pd.DataFrame) -> dict:
        base = apply_cleaning(raw_df, _base_options("Logistics"))
        domain = apply_logistics_cleaning(base.cleaned_df)
        return {"base": base, "domain": domain, "kind": "logistics"}

    def _run_trade(raw_df: pd.DataFrame) -> dict:
        base = apply_cleaning(raw_df, _base_options("Trade"))
        domain = apply_trade_cleaning(base.cleaned_df)
        return {"base": base, "domain": domain, "kind": "trade"}

    def _run_retail(raw_df: pd.DataFrame) -> dict:
        base = apply_cleaning(raw_df, _base_options("Retail"))
        domain = apply_retail_cleaning(base.cleaned_df)
        return {"base": base, "domain": domain, "kind": "retail"}

    def _run_consultant(raw_df: pd.DataFrame) -> dict:
        base = apply_cleaning(raw_df, _base_options("Consultant"))
        domain = apply_consultant_cleaning(base.cleaned_df)
        return {"base": base, "domain": domain, "kind": "consultant"}

    def _run_healthcare(raw_df: pd.DataFrame) -> dict:
        base = apply_cleaning(raw_df, _base_options("Healthcare"))
        domain = apply_healthcare_cleaning(base.cleaned_df)
        return {"base": base, "domain": domain, "kind": "healthcare"}

    def _run_sme(raw_df: pd.DataFrame) -> dict:
        base = apply_cleaning(raw_df, _base_options("SME"))
        domain = apply_sme_cleaning(base.cleaned_df)
        return {"base": base, "domain": domain, "kind": "sme"}

    def _run_hospitality(raw_df: pd.DataFrame) -> dict:
        base = apply_cleaning(raw_df, _base_options("Hospitality"))
        domain = apply_hospitality_cleaning(base.cleaned_df)
        return {"base": base, "domain": domain, "kind": "hospitality"}

    def _run_clinical(raw_df: pd.DataFrame) -> dict:
        from core.cleaner import apply_cleaning
        base = apply_cleaning(raw_df, _base_options("Clinical Research"))
        # standardise_headers lowercases column names, so use the post-clean names
        domain = apply_clinical_cleaning(
            base.cleaned_df,
            nct_col="trial_id",
            researcher_name_col="principal_investigator",
        )
        return {"base": base, "domain": domain, "kind": "clinical"}

    return [
        {
            "key": "finance",
            "label": "Finance & Accounting",
            "icon": "💰",
            "tagline": "GL exports from accounting systems often arrive with inconsistent nominal codes, invalid VAT codes, and narratives that wouldn't survive an audit.",
            "checks": [
                "Pads UK nominal account codes to 4 digits (e.g. 45 → 0045)",
                "Validates VAT/tax codes against recognised UK schemes (Sage, Xero)",
                "Normalises journal references and period labels",
                "Flags missing or non-numeric cost centres",
                "Checks trial balance — total debits vs total credits",
                "Flags blank or generic narrative descriptions",
            ],
            "raw_csv": _FINANCE_CSV,
            "run_fn": _run_finance,
        },
        {
            "key": "logistics",
            "label": "Logistics & Supply Chain",
            "icon": "📦",
            "tagline": "Shipment data exported from multiple carrier portals typically contains mixed status labels, inconsistent weight units, and impossible date sequences.",
            "checks": [
                "Standardises shipment status labels across carriers",
                "Normalises carrier names and codes",
                "Converts all weight units to a consistent format",
                "Calculates transit time from dispatch and delivery dates",
                "Flags impossible date orders (delivery before dispatch)",
                "Identifies duplicate tracking numbers",
            ],
            "raw_csv": _LOGISTICS_CSV,
            "run_fn": _run_logistics,
        },
        {
            "key": "trade",
            "label": "Import/Export & Trade",
            "icon": "🌐",
            "tagline": "Customs and trade data from multiple systems often contains short HS codes, country name variants, and declared values that would fail a customs declaration.",
            "checks": [
                "Validates HS codes (minimum 6 digits)",
                "Maps country names and codes to ISO 3166-1 alpha-2 standard",
                "Standardises currency symbols (USD$, US$, € → ISO codes)",
                "Flags negative or zero declared values",
                "Flags non-standard currency codes",
            ],
            "raw_csv": _TRADE_CSV,
            "run_fn": _run_trade,
        },
        {
            "key": "retail",
            "label": "Retail & Inventory",
            "icon": "🛍️",
            "tagline": "Product catalogue exports frequently show items sold below cost, negative stock levels, and barcodes that fail checksum validation.",
            "checks": [
                "Flags items where cost price exceeds selling price",
                "Detects negative stock levels",
                "Identifies items below reorder point",
                "Validates EAN-13 and UPC-A barcodes including check digit",
                "Detects duplicate SKUs",
            ],
            "raw_csv": _RETAIL_CSV,
            "run_fn": _run_retail,
        },
        {
            "key": "sme",
            "label": "SME & Small Business",
            "icon": "🏢",
            "tagline": "Small business records often contain invalid UK postcodes, incorrectly formatted VAT numbers, and overdue invoices that haven't been flagged.",
            "checks": [
                "Validates UK postcodes (format only)",
                "Validates UK VAT numbers (GB + 9 digits)",
                "Validates Companies House numbers (8 characters)",
                "Detects overdue invoices (due date passed, no payment recorded)",
                "Standardises UK phone numbers to E.164 format",
                "Normalises payment terms (Net 30, Net 60, etc.)",
            ],
            "raw_csv": _SME_CSV,
            "run_fn": _run_sme,
        },
        {
            "key": "consultant",
            "label": "Consultants & Professional Services",
            "icon": "💼",
            "tagline": "Timesheet exports from consulting firms frequently contain hours exceeding 24 per day, zero or negative day rates, and budget overruns that aren't surfaced.",
            "checks": [
                "Flags timesheet entries exceeding 24 hours per day",
                "Checks day rates and hourly rates for zeros or negatives",
                "Formats project codes consistently",
                "Calculates utilisation rate (billable vs total hours)",
                "Detects budget overruns where actual hours exceed budgeted",
            ],
            "raw_csv": _CONSULTANT_CSV,
            "run_fn": _run_consultant,
        },
        {
            "key": "healthcare",
            "label": "Healthcare (Operational)",
            "icon": "🏥",
            "tagline": "NHS appointment registers commonly contain NHS numbers that fail Mod 11 validation, inconsistent ICD-10 codes, and mixed status labels.",
            "checks": [
                "Validates NHS numbers using the Modulus 11 check digit algorithm",
                "Checks ICD-10 diagnosis code format",
                "Standardises appointment status labels",
                "Identifies patients waiting over 18 weeks",
                "Calculates waiting time statistics",
            ],
            "raw_csv": _HEALTHCARE_CSV,
            "run_fn": _run_healthcare,
        },
        {
            "key": "hospitality",
            "label": "Hospitality & Accommodation",
            "icon": "🏨",
            "tagline": "Booking extracts from PMS systems often contain check-out dates before check-in, zero guest counts, and inconsistent room type and status labels.",
            "checks": [
                "Standardises booking references to uppercase",
                "Detects duplicate booking references",
                "Flags impossible date orders (checkout before check-in)",
                "Flags zero or negative guest counts",
                "Normalises room types, booking status, and booking channel labels",
                "Calculates average daily rate and length-of-stay statistics",
            ],
            "raw_csv": _HOSPITALITY_CSV,
            "run_fn": _run_hospitality,
        },
        {
            "key": "clinical",
            "label": "Clinical Research",
            "icon": "🧬",
            "tagline": "Trial registers pulled from multiple registry sources contain inconsistently formatted NCT IDs and the same researcher appearing under several name variants.",
            "checks": [
                "Normalises NCT trial IDs to standard format (NCT + 8 digits)",
                "Standardises researcher names using fuzzy matching",
                "Groups trial records by resolved researcher identity",
                "Detects duplicate or near-duplicate trial entries",
                "Builds a researcher-to-trial register for audit",
            ],
            "raw_csv": _CLINICAL_CSV,
            "run_fn": _run_clinical,
        },
    ]


# =============================================================================
# CSS
# =============================================================================

def _inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; }}

        .demo-hero {{
            text-align: center;
            padding: 1.6rem 0 1rem 0;
        }}
        .demo-hero-title {{
            font-size: 2rem;
            font-weight: 900;
            color: {PRIMARY};
            letter-spacing: -0.5px;
            line-height: 1.2;
            margin-bottom: 0.4rem;
        }}
        .demo-hero-sub {{
            font-size: 1.05rem;
            color: #4B5563;
            max-width: 580px;
            margin: 0 auto 0.75rem;
        }}
        .demo-trust-strip {{
            display: flex;
            gap: 1.2rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 0.5rem;
        }}
        .demo-trust-item {{
            font-size: 0.75rem;
            color: #6B7280;
            display: flex;
            align-items: center;
            gap: 0.3rem;
            font-weight: 500;
        }}
        .demo-trust-dot {{
            width: 6px;
            height: 6px;
            background: {SUCCESS};
            border-radius: 50%;
            display: inline-block;
            flex-shrink: 0;
        }}

        .demo-tagline {{
            background: #F8FAFC;
            border-left: 4px solid {PRIMARY};
            border-radius: 0 10px 10px 0;
            padding: 0.8rem 1.1rem;
            font-size: 0.92rem;
            color: #374151;
            margin-bottom: 0.8rem;
            line-height: 1.55;
        }}

        .demo-checks {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-bottom: 1rem;
        }}
        .demo-check-pill {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: #EFF6FF;
            border: 1px solid #DBEAFE;
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 0.78rem;
            color: #1D4ED8;
            font-weight: 500;
        }}

        .demo-section-label {{
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: {PRIMARY};
            margin: 1rem 0 0.35rem 0;
        }}

        .demo-issue-row {{
            display: flex;
            align-items: flex-start;
            gap: 0.6rem;
            padding: 0.45rem 0;
            border-bottom: 1px solid #F3F4F6;
            font-size: 0.875rem;
        }}
        .demo-issue-badge {{
            display: inline-block;
            background: #FEF3C7;
            color: #92400E;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.72rem;
            font-weight: 700;
            white-space: nowrap;
            flex-shrink: 0;
        }}
        .demo-issue-badge-ok {{
            background: #D1FAE5;
            color: #065F46;
        }}

        .demo-kpi {{
            background: white;
            border-radius: 12px;
            border: 1px solid #E6ECF0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            padding: 0.85rem 1rem;
            text-align: center;
        }}
        .demo-kpi-value {{
            font-size: 1.6rem;
            font-weight: 900;
            color: {PRIMARY};
            line-height: 1.1;
            display: block;
        }}
        .demo-kpi-label {{
            font-size: 0.7rem;
            color: #657286;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-top: 3px;
            display: block;
        }}

        .demo-cta-box {{
            background: linear-gradient(135deg, {PRIMARY}08 0%, {ACCENT}12 100%);
            border: 2px solid {PRIMARY}30;
            border-radius: 14px;
            padding: 1.5rem 1.8rem;
            text-align: center;
            margin-top: 1.8rem;
        }}
        .demo-cta-title {{
            font-size: 1.15rem;
            font-weight: 800;
            color: {PRIMARY};
            margin-bottom: 0.25rem;
        }}
        .demo-cta-sub {{
            color: #4B5563;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# HELPERS
# =============================================================================

def _kpi(label: str, value: str) -> None:
    st.markdown(
        f'<div class="demo-kpi">'
        f'<span class="demo-kpi-value">{value}</span>'
        f'<span class="demo-kpi-label">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _section(label: str) -> None:
    st.markdown(f'<div class="demo-section-label">{label}</div>', unsafe_allow_html=True)


def _render_issues(issues: list[dict]) -> None:
    """Render the domain cleaner issues list."""
    if not issues:
        st.success("No issues detected in this sample.", icon="✅")
        return

    active = [i for i in issues if i.get("count", 0) > 0]
    clean  = [i for i in issues if i.get("count", 0) == 0]

    for issue in active:
        count = issue.get("count", 0)
        badge_text = f"{count} found" if isinstance(count, int) else str(count)
        st.markdown(
            f'<div class="demo-issue-row">'
            f'<span class="demo-issue-badge">{badge_text}</span>'
            f'<span style="color:#374151;">'
            f'<strong>{issue.get("type","")}</strong> — {issue.get("description","")}'
            f'</span></div>',
            unsafe_allow_html=True,
        )

    for issue in clean:
        st.markdown(
            f'<div class="demo-issue-row">'
            f'<span class="demo-issue-badge demo-issue-badge-ok">✓ Clean</span>'
            f'<span style="color:#374151;">'
            f'<strong>{issue.get("type","")}</strong> — {issue.get("description","")}'
            f'</span></div>',
            unsafe_allow_html=True,
        )


def _render_base_changes(base_result: Any, raw_row_count: int = 0) -> None:
    """Summarise what the base cleaner changed (duplicates removed, etc.)."""
    cleaned_rows = base_result.cleaned_df.shape[0]
    rows_removed = max(0, raw_row_count - cleaned_rows)

    msgs = []
    if rows_removed > 0:
        msgs.append(f"**{rows_removed}** duplicate row(s) removed by base cleaner")
    if not msgs:
        msgs.append("Whitespace trimming and header standardisation applied")

    st.info(" · ".join(msgs), icon="ℹ️")


def _render_clinical_result(result: dict) -> None:
    """Specialist display for the clinical research cleaner."""
    domain       = result["domain"]
    profiles     = getattr(domain, "profiles", [])
    base         = result["base"]
    cleaned_df   = domain.cleaned_df
    raw_row_count = result.get("_raw_row_count", base.cleaned_df.shape[0])
    raw_name_count = result.get("_raw_name_count", raw_row_count)

    # How many name variants were merged?
    variants_resolved = max(0, int(raw_name_count) - len(profiles)) if isinstance(raw_name_count, int) else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        _kpi("Trial Rows Processed", str(base.cleaned_df.shape[0]))
    with col2:
        _kpi("Unique Researchers", str(len(profiles)))
    with col3:
        _kpi("Name Variants Merged", str(variants_resolved))

    # Show NCT normalisation note if the column was processed
    # (standardise_headers lowercases column names)
    nct_col_name = next((c for c in ("trial_id", "Trial_ID") if c in cleaned_df.columns), None)
    if nct_col_name:
        nct_standardised = cleaned_df[nct_col_name].astype(str).str.startswith("NCT").sum()
        if nct_standardised > 0:
            st.success(
                f"{nct_standardised} Trial ID(s) normalised to standard NCT format "
                f"(e.g. 'nct 49211' → 'NCT00049211')",
                icon="✅",
            )

    if profiles:
        _section("Resolved Researcher Register")
        for profile in profiles:
            researcher_id = getattr(profile, "researcher_id", "Unknown")
            trials        = getattr(profile, "trials", []) or []
            n_trials      = len(trials)

            # Find name variants for this researcher from the cleaned df
            variants_col = next(
                (c for c in ("canonical_researcher", "standardized_researcher")
                 if c in cleaned_df.columns),
                None,
            )
            pi_col = next(
                (c for c in ("principal_investigator", "Principal_Investigator")
                 if c in cleaned_df.columns),
                None,
            )
            if variants_col and pi_col:
                mask     = cleaned_df[variants_col] == researcher_id
                raw_names = cleaned_df.loc[mask, pi_col].unique().tolist()
            else:
                raw_names = []

            with st.expander(f"**{researcher_id}** — {n_trials} trial record(s)"):
                if len(raw_names) > 1:
                    st.caption(
                        "Name variants resolved: "
                        + ", ".join(f"`{v}`" for v in raw_names)
                    )
                for trial in trials:
                    tid    = trial.get("trial_id", "—")
                    phase  = trial.get("phase", "—")
                    status = trial.get("status", "—")
                    badge  = {"completed": "🟢", "active": "🔵", "recruiting": "🔵"}.get(
                        str(status).lower(), "⚪"
                    )
                    unverified = "" if trial.get("researcher_valid", True) else "  ⚠ researcher ID unverified"
                    st.write(f"{badge} **{tid}** · Phase: {phase} · Status: {status}{unverified}")

    _render_base_changes(base, raw_row_count)


def _render_standard_result(result: dict, scenario: dict) -> None:
    """Standard display for all non-clinical domain cleaners."""
    domain = result["domain"]
    base   = result["base"]
    metrics = getattr(domain, "metrics", {})
    issues  = getattr(domain, "issues", [])

    # — KPI row ----------------------------------------------------------------
    total_key = next(
        (k for k in ("total_entries", "total_shipments", "total_records",
                     "total_bookings", "total_rows", "total_timesheets")
         if k in metrics),
        None,
    )
    issues_found = metrics.get("issues_found", sum(1 for i in issues if i.get("count", 0) > 0))

    raw_row_count = result.get("_raw_row_count", base.cleaned_df.shape[0])

    col1, col2, col3 = st.columns(3)
    with col1:
        total_val = metrics.get(total_key, base.cleaned_df.shape[0]) if total_key else base.cleaned_df.shape[0]
        _kpi("Rows Processed", f"{total_val:,}" if isinstance(total_val, int) else str(total_val))
    with col2:
        _kpi("Issues Detected", str(issues_found))
    with col3:
        checks_passed = len([i for i in issues if i.get("count", 0) == 0])
        _kpi("Checks Passed", str(checks_passed))

    # — Domain-specific headline metrics (Finance trial balance) ---------------
    tb = metrics.get("trial_balance")
    if tb:
        bal_cols = st.columns(3)
        with bal_cols[0]:
            st.metric("Total Debits",   f"{tb.get('total_debits', 0):,.2f}")
        with bal_cols[1]:
            st.metric("Total Credits",  f"{tb.get('total_credits', 0):,.2f}")
        with bal_cols[2]:
            diff = tb.get("difference", 0)
            st.metric(
                "Balance Difference",
                f"{diff:,.2f}",
                delta="In Balance" if tb.get("in_balance") else f"{tb.get('pct_diff', '?')}% off",
                delta_color="normal" if tb.get("in_balance") else "inverse",
            )

    # — Findings ---------------------------------------------------------------
    _section("Findings")
    _render_issues(issues)

    # — Base cleaner summary ---------------------------------------------------
    _render_base_changes(base, raw_row_count)


# =============================================================================
# TAB RENDERER
# =============================================================================

def _render_scenario_tab(scenario: dict) -> None:
    cache_key = f"_demo_result_{scenario['key']}"

    # — Tagline ----------------------------------------------------------------
    st.markdown(
        f'<div class="demo-tagline">{scenario["tagline"]}</div>',
        unsafe_allow_html=True,
    )

    # — What this cleaner checks -----------------------------------------------
    pills_html = "".join(
        f'<span class="demo-check-pill">✓ {c}</span>'
        for c in scenario["checks"]
    )
    st.markdown(
        f'<div class="demo-checks">{pills_html}</div>',
        unsafe_allow_html=True,
    )

    # — Raw data ---------------------------------------------------------------
    raw_df = pd.read_csv(io.StringIO(scenario["raw_csv"]))

    _section("Raw data — before cleaning")
    st.dataframe(raw_df, use_container_width=True, height=320)

    # — Run button -------------------------------------------------------------
    col_btn, col_reset = st.columns([2, 1])
    with col_btn:
        run = st.button(
            f"Run Demo - See what ColtraDataAi finds",
            key=f"demo_run_{scenario['key']}",
            type="primary",
            use_container_width=True,
        )
    with col_reset:
        if st.button("Reset", key=f"demo_reset_{scenario['key']}", use_container_width=True):
            st.session_state.pop(cache_key, None)
            st.rerun()

    if run:
        with st.spinner("Running cleaning pipeline..."):
            try:
                result = scenario["run_fn"](raw_df)
                result["_raw_row_count"] = len(raw_df)
                if scenario["key"] == "clinical":
                    # Column 1 is Principal_Investigator in the raw CSV (before header standardisation)
                    pi_raw = raw_df.iloc[:, 1] if raw_df.shape[1] > 1 else pd.Series([], dtype=str)
                    result["_raw_name_count"] = int(pi_raw.nunique())
                st.session_state[cache_key] = result
            except Exception as exc:
                st.error(f"Demo run failed: {exc}")
                return

    result = st.session_state.get(cache_key)
    if result is None:
        return

    # — Results ----------------------------------------------------------------
    st.markdown("---")
    _section("Results")

    if scenario["key"] == "clinical":
        _render_clinical_result(result)
    else:
        _render_standard_result(result, scenario)

    # — Cleaned data -----------------------------------------------------------
    _section("Cleaned data — after processing")
    domain = result["domain"]
    cleaned_df = getattr(domain, "cleaned_df", result["base"].cleaned_df)
    st.dataframe(cleaned_df, use_container_width=True, height=320)

    # — CTA --------------------------------------------------------------------
    _render_cta()


# =============================================================================
# UPGRADE CTA
# =============================================================================

def _render_cta() -> None:
    from services.billing import checkout_url, append_affiliate

    # checkout_url() already calls append_affiliate() internally.
    # app_url is not a LS URL so needs manual affiliate append.
    starter_url = checkout_url("starter")
    pro_url     = checkout_url("professional")
    app_url     = append_affiliate("https://app.coltradata.com")

    st.markdown(
        f'<div class="demo-cta-box">'
        f'<div class="demo-cta-title">Ready to run this on your own data?</div>'
        f'<div class="demo-cta-sub">'
        f'Start free - no credit card required. Upload your own file and get the same results instantly.'
        f'</div>',
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
    with btn_col1:
        st.link_button(
            "Start Free - No Card Required",
            app_url,
            use_container_width=True,
            type="primary",
        )
    with btn_col2:
        if starter_url:
            st.link_button("Get Starter - £29/month", starter_url, use_container_width=True)
        else:
            st.link_button("View Pricing", "https://coltradata.com/#pricing", use_container_width=True)
    with btn_col3:
        if pro_url:
            st.link_button("Get Professional - £99/month", pro_url, use_container_width=True)
        else:
            st.link_button("Back to ColtraDataAi", "https://coltradata.com", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# PUBLIC ENTRY POINT
# =============================================================================

def render_demo_panel() -> None:
    """Render the complete live demo panel. Call from a Streamlit page."""
    _inject_css()

    # — Hero header ------------------------------------------------------------
    st.markdown(
        f"""
        <div class="demo-hero">
            <div class="demo-hero-title">See ColtraDataAi in action</div>
            <div class="demo-hero-sub">
                Select a domain below and click <strong>Run Demo</strong> to see
                real cleaning rules applied to intentionally messy sample data -
                no upload required.
            </div>
            <div class="demo-trust-strip">
                <span class="demo-trust-item"><span class="demo-trust-dot"></span>No data stored permanently</span>
                <span class="demo-trust-item"><span class="demo-trust-dot"></span>GDPR compliant</span>
                <span class="demo-trust-item"><span class="demo-trust-dot"></span>UK-based processing</span>
                <span class="demo-trust-item"><span class="demo-trust-dot"></span>Free plan - no card required</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # — Load scenarios (imports happen once) -----------------------------------
    if "demo_scenarios" not in st.session_state:
        try:
            st.session_state["demo_scenarios"] = _make_scenarios()
        except Exception as exc:
            st.error(f"Could not load demo scenarios: {exc}")
            return

    scenarios = st.session_state["demo_scenarios"]

    # — Tab bar ----------------------------------------------------------------
    tab_labels = [f"{s['icon']} {s['label']}" for s in scenarios]
    tabs = st.tabs(tab_labels)

    for tab, scenario in zip(tabs, scenarios):
        with tab:
            _render_scenario_tab(scenario)
