import streamlit as st

from config.plans import PLAN_CONFIG, PLAN_ORDER
from services.billing import checkout_url, payments_live

_ANNUAL_CONFIG: dict[str, dict] = {
    "starter":      {"price": "£290/year", "monthly_equiv": "£24.17/mo", "saving": "Save £58 - 2 months free"},
    "professional": {"price": "£990/year", "monthly_equiv": "£82.50/mo", "saving": "Save £198 - 2 months free"},
    "business":     {"price": "£2,990/year", "monthly_equiv": "£249.17/mo", "saving": "Save £598 - 2 months free"},
    "enterprise":   {"price": "Contact Sales", "monthly_equiv": "", "saving": "Custom annual pricing available"},
}

_SUPPORT_TIERS: dict[str, list[str]] = {
    "free":         ["Email support (48–72h)"],
    "starter":      ["Email support (24–48h)"],
    "professional": ["Priority email support (12–24h)"],
    "business":     ["Priority support (same-day)"],
    "enterprise":   ["Dedicated support + SLA (&lt;4h)"],
    "premium":      ["Priority support (same-day)"],  # legacy grandfathered only
}

_CTA_LABELS: dict[str, str] = {
    "starter":      "Get Starter",
    "professional": "Get Professional",
    "business":     "Get Business",
    "enterprise":   "Book a Demo",
    "premium":      "Scale with Premium",  # legacy grandfathered only — no active checkout
}

_ENTERPRISE_FEATURES = [
    "Unlimited runs and unlimited rows",
    "White-label deployment",
    "Custom validation rules",
    "Private API endpoints",
    "Dedicated infrastructure",
    "SLA-backed support (&lt;4h response)",
    "Bespoke AI workflows",
    "Onboarding and training included",
]

_FEATURE_BULLETS: list[tuple[str, str]] = [
    ("can_download_excel",         "Excel export"),
    ("can_download_pdf",           "PDF reports"),
    ("can_view_advanced_insights", "AI insights &amp; analytics"),
    ("can_view_premium_charts",    "Premium chart gallery"),
    ("can_brand_reports",          "Branded client reports"),
]


def render_pricing_page() -> None:
    from utils.session_helpers import get_plan_key
    render_pricing_cards(current_plan_key=get_plan_key())


def render_pricing_cards(current_plan_key: str = "free") -> None:
    """Full conversion-optimised pricing table."""
    _inject_pricing_css()

    st.markdown("## ColtraDataAi Plans")
    st.caption("Trusted for structured data processing and reporting.")

    # Billing period toggle
    billing_col1, billing_col2, billing_col3 = st.columns([1.5, 1, 1.5])
    with billing_col2:
        billing_period = st.radio(
            "Billing period",
            options=["Monthly", "Annual (2 months free)"],
            horizontal=True,
            label_visibility="collapsed",
            key="_pricing_billing_period",
        )
    annual = billing_period == "Annual (2 months free)"

    cols = st.columns(len(PLAN_ORDER), gap="small")
    for col, plan_key in zip(cols, PLAN_ORDER):
        plan       = PLAN_CONFIG[plan_key]
        is_current = plan_key == current_plan_key
        featured   = plan_key == "professional"

        with col:
            _render_card(plan_key, plan, is_current, featured, annual=annual)

    _render_reassurance_row()
    _render_enterprise_api_callout()


# ── Private helpers ───────────────────────────────────────────────────────────

def _render_card(
    plan_key: str,
    plan: dict,
    is_current: bool,
    featured: bool,
    annual: bool = False,
) -> None:
    card_class = "pricing-card pricing-card--featured" if featured else "pricing-card"
    if annual and plan_key in _ANNUAL_CONFIG:
        ann = _ANNUAL_CONFIG[plan_key]
        monthly_note = (
            f'<span style="display:block;font-size:0.7rem;color:#6B7280;font-weight:400;margin-top:2px;">'
            f'{ann["monthly_equiv"]}, billed annually</span>'
            if ann["monthly_equiv"] else ""
        )
        price_display = (
            f'{ann["price"]}'
            f'{monthly_note}'
        )
    else:
        price_display = plan["price"]

    # ── Badges ────────────────────────────────────────────────────────────────
    badges_html = ""
    if featured:
        badges_html += '<span class="badge badge--popular">Most Popular</span>'
        badges_html += '<span class="badge badge--sme">Best for SMEs</span>'
    if is_current:
        badges_html += '<span class="badge badge--current">Your plan</span>'
    if annual and plan_key in _ANNUAL_CONFIG:
        saving_text = _ANNUAL_CONFIG[plan_key]["saving"]
        badges_html += f'<span class="badge badge--saving">{saving_text}</span>'
    badges_section = (
        f'<div class="card-badges">{badges_html}</div>'
        if badges_html else
        '<div class="card-badges-empty"></div>'
    )

    # ── Feature bullets ───────────────────────────────────────────────────────
    runs = plan["monthly_runs"]
    runs_label = (
        "Unlimited cleaning runs/month"
        if runs is None
        else f"Up to {runs:,} cleaning runs/month"
    )
    rows = plan["max_rows_backend"]
    rows_label = (
        "Unlimited rows per dataset"
        if rows is None
        else f"Up to {rows:,} rows per dataset"
    )

    bullets = (
        f'<li>{runs_label}</li>'
        f'<li>{rows_label}</li>'
        f'<li>{plan["max_file_mb_backend"]} MB file size</li>'
    )

    if plan_key == "enterprise":
        for feat in _ENTERPRISE_FEATURES:
            bullets += f"<li>{feat}</li>"
    else:
        for feat_key, label in _FEATURE_BULLETS:
            if plan.get(feat_key):
                bullets += f"<li>{label}</li>"

    for line in _SUPPORT_TIERS.get(plan_key, []):
        bullets += f'<li class="support-line">{line}</li>'

    # ── Assemble full card HTML ───────────────────────────────────────────────
    html = (
        f'<div class="{card_class}">'
        f'{badges_section}'
        f'<p class="card-name">{plan["label"]}</p>'
        f'<p class="card-price">{price_display}</p>'
        f'<p class="card-blurb">{plan["blurb"]}</p>'
        f'<hr class="card-rule" />'
        f'<ul class="card-features">{bullets}</ul>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    # ── CTA button (must be a Streamlit widget, rendered outside the HTML) ────
    if is_current:
        st.button(
            "Current Plan",
            disabled=True,
            use_container_width=True,
            key=f"_pricing_current_{plan_key}",
        )
    elif plan_key == "free":
        pass
    else:
        url   = checkout_url(plan_key)
        label = _CTA_LABELS.get(plan_key, f"Get {plan['label']}")
        if annual and plan_key in _ANNUAL_CONFIG and plan_key != "enterprise":
            subject = f"Annual%20Plan%20Enquiry%20-%20{plan['label']}"
            ann_label = f"{label} (Annual)"
            st.link_button(
                ann_label,
                f"mailto:sales@coltradata.com?subject={subject}",
                use_container_width=True,
                type="primary",
            )
            st.markdown(
                '<p style="text-align:center;font-size:0.68rem;color:#9CA3AF;margin-top:2px;">'
                'Annual invoicing via sales team</p>',
                unsafe_allow_html=True,
            )
        elif url:
            st.link_button(label, url, use_container_width=True, type="primary")
        elif plan_key == "enterprise":
            st.link_button(
                "Contact Sales →",
                "mailto:sales@coltradata.com?subject=Enterprise%20Enquiry",
                use_container_width=True,
                type="primary",
            )
        elif payments_live():
            st.button(
                label,
                disabled=True,
                use_container_width=True,
                key=f"_pricing_btn_{plan_key}",
            )
        else:
            st.caption("Coming soon")


def _render_reassurance_row() -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    items = [
        ("Cancel anytime", c1),
        ("No long-term contracts", c2),
        ("REST API available on paid plans", c3),
        ("Secure checkout via Lemon Squeezy", c4),
    ]
    for text, col in items:
        with col:
            st.markdown(
                f'<p style="text-align:center;font-size:0.8rem;color:#657286;">{text}</p>',
                unsafe_allow_html=True,
            )


def _render_enterprise_api_callout() -> None:
    """Horizontal banner advertising the standalone Enterprise API developer product."""
    from services.billing import checkout_url
    api_url = checkout_url("enterprise_api")
    cta_html = (
        f'<a href="{api_url}" target="_blank" rel="noopener" '
        f'style="display:inline-block;background:#2E86AB;color:white;font-weight:700;'
        f'font-size:0.85rem;padding:0.65rem 1.5rem;border-radius:9px;text-decoration:none;'
        f'white-space:nowrap;">Get API Access &#8594;</a>'
        f'<p style="font-size:0.7rem;color:#5a6a7a;text-align:center;margin:5px 0 0;">API key delivered by email</p>'
        if api_url else
        f'<a href="mailto:sales@coltradata.com?subject=Enterprise%20API%20Enquiry" '
        f'style="display:inline-block;background:#2E86AB;color:white;font-weight:700;'
        f'font-size:0.85rem;padding:0.65rem 1.5rem;border-radius:9px;text-decoration:none;'
        f'white-space:nowrap;">Contact Sales &#8594;</a>'
    )

    st.markdown(
        f"""
        <div style="
            background:linear-gradient(135deg,#EBF4FF 0%,#E0F4F8 100%);
            border:1.5px solid #2E86AB;
            border-radius:16px;
            padding:1.35rem 1.6rem;
            margin-top:0.5rem;
        ">
            <div style="display:flex;gap:0.6rem;align-items:center;margin-bottom:0.7rem;">
                <span style="background:#2E86AB;color:white;font-size:0.62rem;font-weight:700;
                    letter-spacing:0.08em;text-transform:uppercase;padding:3px 10px;
                    border-radius:100px;">For Developers</span>
                <span style="font-size:0.75rem;color:#2E86AB;font-weight:600;">
                    Standalone REST API — no app subscription required
                </span>
            </div>
            <div style="display:grid;grid-template-columns:1fr auto;gap:2rem;align-items:center;">
                <div>
                    <p style="font-size:1.05rem;font-weight:800;color:#1F4E79;margin:0 0 4px;">
                        Enterprise API
                        <span style="font-size:0.88rem;font-weight:500;color:#111827;">
                            &nbsp;&#8212;&nbsp;&#163;499<span style="font-size:0.78rem;
                            font-weight:400;color:#5a6a7a;">/month</span>
                        </span>
                    </p>
                    <p style="font-size:0.78rem;color:#4B5563;margin:0 0 0.7rem;line-height:1.55;">
                        Integrate ColtraDataAi's cleaning engine directly into your own systems or pipelines.
                        All 8 domain cleaners as REST endpoints. API key auto-delivered on purchase.
                    </p>
                    <div style="display:flex;flex-wrap:wrap;gap:3px 1.8rem;">
                        <span style="font-size:0.74rem;color:#374151;">&#10003; All 8 domain cleaners (Logistics, Finance, Retail, Healthcare &amp; more)</span>
                        <span style="font-size:0.74rem;color:#374151;">&#10003; CSV &amp; JSON input support</span>
                        <span style="font-size:0.74rem;color:#374151;">&#10003; Unlimited API calls</span>
                        <span style="font-size:0.74rem;color:#374151;">&#10003; Bearer token authentication</span>
                        <span style="font-size:0.74rem;color:#374151;">&#10003; Swagger / OpenAPI docs</span>
                        <span style="font-size:0.74rem;color:#374151;">&#10003; Usage analytics dashboard</span>
                    </div>
                </div>
                <div style="text-align:center;flex-shrink:0;">
                    {cta_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _inject_pricing_css() -> None:
    st.markdown(
        """
        <style>
        /* ── Responsive grid ────────────────────────────────── */
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 150px;
        }
        div[data-testid="stHorizontalBlock"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }

        /* ── Base card ──────────────────────────────────────── */
        .pricing-card {
            background: #FFFFFF;
            border: 1px solid #E6ECF0;
            border-radius: 14px;
            padding: 1.1rem 1rem 1rem 1rem;
            margin-bottom: 0.5rem;
        }

        /* ── Featured (Professional) card ───────────────────── */
        .pricing-card--featured {
            border: 2px solid #1F4E79;
            background: #F0F6FF;
            box-shadow: 0 4px 18px rgba(31, 78, 121, 0.12);
        }

        /* ── Badge row ──────────────────────────────────────── */
        .card-badges {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 0.55rem;
            min-height: 22px;
        }
        .card-badges-empty {
            min-height: 22px;
            margin-bottom: 0.55rem;
        }
        .badge {
            font-size: 0.6rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 20px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .badge--popular {
            background: #1F4E79;
            color: #FFFFFF;
        }
        .badge--current {
            background: #D1FAE5;
            color: #065F46;
        }
        .badge--sme {
            background: #D1FAE5;
            color: #065F46;
        }
        .badge--saving {
            background: #FEF3C7;
            color: #92400E;
            font-size: 0.58rem;
        }

        /* ── Plan name & price ──────────────────────────────── */
        .card-name {
            font-size: 0.95rem;
            font-weight: 700;
            color: #1F4E79;
            margin: 0 0 2px 0;
        }
        .card-price {
            font-size: 1.4rem;
            font-weight: 800;
            color: #111827;
            margin: 0 0 4px 0;
            white-space: nowrap;
        }
        .card-blurb {
            font-size: 0.75rem;
            color: #4B5563;
            margin: 0 0 0 0;
            line-height: 1.4;
        }

        /* ── Divider ─────────────────────────────────────────── */
        .card-rule {
            border: none;
            border-top: 1px solid #E6ECF0;
            margin: 0.65rem 0 0.5rem 0;
        }

        /* ── Feature list ───────────────────────────────────── */
        .card-features {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .card-features li {
            font-size: 0.75rem;
            color: #374151;
            padding: 2px 0;
            line-height: 1.45;
        }
        .card-features li::before {
            content: "✓ ";
            color: #1F4E79;
            font-weight: 700;
        }
        .card-features li.support-line {
            color: #6B7280;
            font-style: italic;
        }
        .card-features li.support-line::before {
            content: "◎ ";
            color: #9CA3AF;
            font-weight: normal;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
