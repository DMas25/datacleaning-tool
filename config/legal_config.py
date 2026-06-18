"""Privacy, GDPR, cookies and terms text shown in the app's legal notices panel.

Mirrors the pattern in branding_config.py: all legal copy lives here so it can
be updated in one place and reused by any UI surface (footer expander,
exports, future legal pages) without duplicating text.
"""

legal = {
    "last_updated": "18 June 2026",
    "privacy_email": "privacy@coltradata.com",

    "data_controller": (
        "Coltrane Ltd (trading as ColtraDataAi), registered in England and Wales, "
        "Company No. 09088932, registered office: Kemp House, 128 City Road, "
        "London EC1V 2NX."
    ),

    "privacy_policy": (
        "**What we collect**\n\n"
        "- *Uploaded datasets*: processed entirely in memory for the duration of your "
        "browser session. Files are not written to disk or any database, and are "
        "discarded when the session ends or the app restarts.\n"
        "- *Account/billing data*: if you purchase a paid plan, your email address, "
        "licence key, plan tier and usage (run count) are stored in our subscription "
        "database so your licence can be validated on return visits. Payment card "
        "details are handled entirely by our payment processor, Lemon Squeezy — we "
        "never see or store card numbers.\n"
        "- *Login credentials*: if app access is password-protected, the password "
        "you enter is checked against app configuration and is not logged or stored "
        "alongside your identity.\n\n"
        "**Why we collect it**\n\n"
        "Billing data is processed to provide the paid service you've subscribed to "
        "(performance of a contract). Uploaded data is processed only to deliver the "
        "cleaning/reporting output you requested, at your direction, and is not used "
        "for any other purpose.\n\n"
        "**Who else sees it**\n\n"
        "- Lemon Squeezy (payment processing and licence issuance) — see their own "
        "privacy policy at lemonsqueezy.com/privacy.\n"
        "- Streamlit Community Cloud (application hosting) — the infrastructure "
        "provider for running this app; see Streamlit/Snowflake's privacy policy.\n"
        "We do not sell, rent, or share your data with any other third party.\n\n"
        "**How long we keep it**\n\n"
        "Uploaded datasets: not retained — cleared at the end of your session. "
        "Billing/account records: retained for as long as your licence is active, "
        "plus the period required by UK accounting and tax record-keeping rules "
        "(typically up to 6 years after the relevant tax year).\n\n"
        "**Privacy or data protection questions**: contact privacy@coltradata.com."
    ),

    "gdpr_notice": (
        "**Data controller**: Coltrane Ltd (see registration details above).\n\n"
        "**Lawful basis for processing**\n\n"
        "- Billing/account data — performance of a contract (Article 6(1)(b) GDPR).\n"
        "- Uploaded dataset processing — performed at your direction as part of the "
        "service you requested; we act on your instructions and do not independently "
        "decide how that data is used.\n\n"
        "**Your rights**\n\n"
        "Under UK GDPR / EU GDPR you have the right to access, correct, delete, "
        "restrict, or export your personal data, and to object to processing. To "
        "exercise any of these rights, contact us at privacy@coltradata.com.\n\n"
        "**If you upload data belonging to other people** (e.g. customer or employee "
        "records), you remain the data controller for that data and ColtraDataAi "
        "acts only as a data processor on your instructions. You are responsible for "
        "having a lawful basis to process that data and for informing the relevant "
        "individuals as required under Articles 13/14 GDPR before uploading it."
    ),

    "cookies_notice": (
        "This app uses only the strictly necessary session cookie set by the "
        "Streamlit framework to keep you logged in and maintain your session state "
        "while the app is open. We do not use analytics, advertising, or third-party "
        "tracking cookies."
    ),

    "terms_summary": (
        "ColtraDataAi provides automated data cleaning, validation and reporting "
        "only. It does not provide legal, financial, tax, accounting or compliance "
        "advice, and outputs are informational. You remain responsible for "
        "independently reviewing all outputs and obtaining professional advice "
        "before making decisions based on them. By using this app you confirm you "
        "have the right to upload and process any data you submit."
    ),
}
