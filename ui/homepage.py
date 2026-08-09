"""Login gate, app header and page footer rendering for ColtraDataAi.

Authentication model
────────────────────
Passwordless email OTP.  No shared password; no passwords stored at all.

Sign-in flow:
  Step 1 — user enters their email → "Send verification code"
  Step 2 — a 6-digit code arrives in their inbox → they enter it → authenticated

Security properties:
  • The 6-digit code is generated with secrets.randbelow (CSPRNG).
  • Only the SHA-256 hash of the code is stored in Supabase — no admin or
    backend viewer can read or replay the code.
  • Codes expire in 10 minutes and are single-use.
  • Rate-limited to 3 requests per email per 10 minutes.

Admin access:
  Admin privileges (is_admin flag + enterprise plan) are granted when the
  authenticated email matches [admin] admin_email in secrets.toml / Render
  env vars.  The fault dashboard retains its own dashboard_password gate
  inside the sidebar expander — that is unchanged.
"""
from __future__ import annotations

import base64
import os

import streamlit as st


def check_password(branding: dict) -> bool:
    """Email OTP authentication gate. Returns True when authenticated."""
    if st.session_state.get("authenticated"):
        return True

    _inject_login_css(branding)

    # Show branded landing page first; login form revealed when user clicks CTA.
    if not st.session_state.get("_show_login"):
        _render_landing_page(branding)
        return False

    _render_login_header(branding)

    step = st.session_state.get("_otp_step", "email")
    if step == "email":
        _render_email_step(branding)
    else:
        _render_verify_step(branding)

    _render_signup_guide(branding)
    _render_login_features(branding)
    return False


def render_sign_out_button() -> None:
    """Sidebar control letting an authenticated user end their session."""
    if st.sidebar.button("Sign out", use_container_width=True):
        st.session_state.clear()
        st.rerun()


def render_header(branding: dict) -> None:
    """Render the branded app header: logo | divider | tagline block."""
    logo_path = branding.get("logo_path", "assets/logo/coltradata_logo.png")
    logo_b64 = _encode_logo(logo_path)

    if logo_b64:
        img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="width:234px;height:auto;display:block;flex-shrink:0;border:none;outline:none;" />'
    else:
        img_tag = f'<div style="font-size:1.4rem;font-weight:800;color:{branding["primary_colour"]};">{branding["app_name"]}</div>'

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:0;padding:32px 0 12px 0;">
            {img_tag}
            <div style="width:1.5px;height:68px;background:#C8D6DF;margin:0 22px;flex-shrink:0;align-self:center;"></div>
            <div style="display:flex;flex-direction:column;align-items:center;max-width:360px;">
                <h3 style="margin:0;color:{branding['primary_colour']};letter-spacing:1.5px;font-size:1.05em;text-align:center;white-space:nowrap;">
                    DATA &nbsp;&bull;&nbsp; INSIGHTS &nbsp;&bull;&nbsp; INTELLIGENCE
                </h3>
                <p style="margin:4px 0 0 0;color:{branding['primary_colour']};font-size:0.9em;font-weight:700;letter-spacing:0.04em;text-align:center;">
                    {branding.get('platform_line', 'Navigate the DataMaze.')}
                </p>
                <p style="margin:5px 0 0 0;color:#657286;font-size:0.78em;line-height:1.5;text-align:center;">
                    From raw, tangled data to clean, validated reports —<br/>wherever your team works.
                </p>
            </div>
        </div>
        <hr style="margin:0 0 16px 0;border:none;border-top:1px solid #E6ECF0;" />
        """,
        unsafe_allow_html=True,
    )


def render_legal_notices(legal: dict) -> None:
    """Render expandable Privacy/GDPR/Cookies/Terms sections above the footer."""
    with st.expander("Privacy, GDPR & Legal Notices", expanded=False):
        st.markdown(f"*Last updated: {legal['last_updated']}*")
        st.markdown("#### Privacy Policy")
        st.markdown(legal["privacy_policy"])
        st.markdown("#### GDPR Notice")
        st.markdown(legal["gdpr_notice"])
        st.markdown("#### Cookies")
        st.markdown(legal["cookies_notice"])
        st.markdown("#### Terms of Use Summary")
        st.markdown(legal["terms_summary"])


def render_footer(branding: dict) -> None:
    """Render the branded page footer with contact link and disclaimer."""
    st.markdown(
        f"""
        <div style="margin-top:3rem;padding:20px 0 8px 0;border-top:1px solid #E6ECF0;text-align:center;">
            <div style="font-size:0.875rem;color:#657286;margin-bottom:10px;">
                <strong style="color:{branding['primary_colour']};">{branding['app_name']}</strong>
                &nbsp;&nbsp;|&nbsp;&nbsp;
                Navigate the DataMaze &nbsp;&middot;&nbsp; Data Cleaning, Validation &amp; Reporting
                &nbsp;&nbsp;|&nbsp;&nbsp;
                <a href="mailto:{branding['contact_email']}"
                   style="color:{branding['primary_colour']};text-decoration:none;">
                   {branding['contact_email']}
                </a>
            </div>
            <div style="font-size:0.75rem;color:#9CA3AF;max-width:740px;margin:0 auto;line-height:1.65;">
                This tool performs automated data cleaning and structuring only. It does not provide
                legal, financial, tax, or compliance advice. Users remain responsible for reviewing
                all outputs and obtaining professional guidance where required.
                &copy; 2026 {branding.get('company', 'Coltrane Ltd')}. All rights reserved.
            </div>
            <div style="font-size:0.7rem;color:#B0B7C3;max-width:740px;margin:8px auto 0;line-height:1.5;">
                {branding.get('legal_line', '')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Login steps ───────────────────────────────────────────────────────────────

def _render_email_step(branding: dict) -> None:
    """Step 1: email input form."""
    primary = branding["primary_colour"]
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #DCE6EE;border-radius:16px;
                        box-shadow:0 4px 28px rgba(31,78,121,0.10);padding:2rem 2rem 1.6rem 2rem;
                        margin-top:0.5rem;">
                <div style="font-size:1.05rem;font-weight:700;color:{primary};
                            margin-bottom:0.3rem;letter-spacing:0.01em;">
                    Sign in or get started
                </div>
                <div style="font-size:0.78rem;color:#657286;margin-bottom:1.1rem;">
                    Enter your email — we'll send a 6-digit verification code.
                    No password needed.
                </div>
            """,
            unsafe_allow_html=True,
        )
        email = st.text_input(
            "Email address",
            label_visibility="collapsed",
            placeholder="your@email.com",
            key="_login_email",
        )
        if st.button("Send verification code →", use_container_width=True, type="primary"):
            _handle_send_otp(email.strip(), branding)
        st.markdown(
            """
            <div style="margin-top:1rem;text-align:center;font-size:0.72rem;color:#9CA3AF;">
                First time here? Enter your email and we'll create your account automatically.
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_verify_step(branding: dict) -> None:
    """Step 2: 6-digit OTP entry form."""
    primary = branding["primary_colour"]
    otp_email = st.session_state.get("_otp_email", "")
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #DCE6EE;border-radius:16px;
                        box-shadow:0 4px 28px rgba(31,78,121,0.10);padding:2rem 2rem 1.6rem 2rem;
                        margin-top:0.5rem;">
                <div style="font-size:1.05rem;font-weight:700;color:{primary};
                            margin-bottom:0.45rem;letter-spacing:0.01em;">
                    Enter your verification code
                </div>
                <div style="font-size:0.8rem;color:#657286;margin-bottom:1.1rem;line-height:1.55;">
                    A 6-digit code was sent to
                    <strong style="color:#1F2937;">{otp_email}</strong>.<br/>
                    Check your spam / junk folder if it hasn't arrived within a minute.
                </div>
            """,
            unsafe_allow_html=True,
        )
        code = st.text_input(
            "6-digit code",
            label_visibility="collapsed",
            placeholder="e.g.  8 4 7  2 9 3",
            max_chars=7,
            key="_login_otp_code",
        )
        if st.button("Verify & Sign in", use_container_width=True, type="primary"):
            _handle_verify_otp(otp_email, code, branding)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="text-align:center;margin-top:0.75rem;font-size:0.73rem;color:#9CA3AF;">
                Code expires in 10 minutes. &nbsp;
                <span style="color:{primary};cursor:pointer;" id="_otp_resend">
                    Need a new code?
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("← Use a different email", key="_otp_back", use_container_width=False):
            st.session_state.pop("_otp_step", None)
            st.session_state.pop("_otp_email", None)
            st.rerun()


def _handle_send_otp(email: str, branding: dict) -> None:
    """Process the 'Send code' submission: trigger Supabase Auth OTP, advance step.

    Supabase Auth handles code generation, secure storage, rate-limiting, and
    email delivery — no Resend call or plaintext code is needed here.
    """
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        st.error("Please enter a valid email address.")
        return

    from services.auth_service import issue_otp

    with st.spinner("Sending verification code…"):
        ok, error = issue_otp(email)

    if not ok:
        st.error(error)
        return

    st.session_state["_otp_email"] = email
    st.session_state["_otp_step"] = "verify"
    st.rerun()


def _handle_verify_otp(email: str, code: str, branding: dict) -> None:
    """Process the 'Verify' submission: validate OTP, set authenticated session."""
    code = code.replace(" ", "").strip()

    from services.auth_service import verify_otp

    with st.spinner("Verifying…"):
        valid, error = verify_otp(email, code)

    if not valid:
        st.error(error)
        return

    # ── Authenticated ──────────────────────────────────────────────────────────
    # Guarantee a subscription row exists before we read the plan from it.
    # Non-fatal — if the row already exists the upsert is a no-op.
    try:
        from services.licence_manager_pg import ensure_free_subscriber
        ensure_free_subscriber(email)
    except Exception:
        pass

    st.session_state["authenticated"] = True
    st.session_state["customer_email"] = email
    st.session_state["user_email"] = email

    # Grant admin privileges if the email matches the configured admin email.
    # Admin still uses the same OTP flow — no separate shared password needed.
    admin_email = _get_admin_email()
    if admin_email and email.lower() == admin_email.lower():
        st.session_state["is_admin"] = True
        st.session_state["plan_key"] = "enterprise"

    # Auto-activate paid plan from subscription record — no licence key entry needed.
    # The webhook stores the plan against the email; we load it here on first sign-in.
    _PLAN_DISPLAY = {
        "starter": "Starter", "professional": "Professional",
        "premium": "Premium", "enterprise": "Enterprise",
    }
    try:
        from services.licence_manager_pg import get_by_email
        sub = get_by_email(email)
        if sub and sub.get("status") == "active" and sub.get("plan") not in (None, "", "free"):
            plan_key = sub["plan"]
            st.session_state["account_tier"] = _PLAN_DISPLAY.get(plan_key, plan_key.capitalize())
            st.session_state["plan_key"] = plan_key
    except Exception:
        pass  # Non-fatal — free plan remains default; user can still enter a key manually.

    # Clean up OTP step state
    st.session_state.pop("_otp_step", None)
    st.session_state.pop("_otp_email", None)

    st.rerun()


# ── Pre-login landing page ────────────────────────────────────────────────────

def _render_landing_page(branding: dict) -> None:
    """Branded marketing page shown before the sign-in form."""
    primary = branding["primary_colour"]
    logo_path = branding.get("logo_path", "assets/logo/coltradata_logo.png")
    logo_b64 = _encode_logo(logo_path)
    store_url = "https://app.coltradata.com/Pricing"
    contact = branding.get("contact_email", "support@coltradata.com")

    if logo_b64:
        brand_html = (
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="height:60px;width:auto;display:block;margin:0 auto 14px auto;" />'
        )
    else:
        brand_html = (
            f'<div style="font-size:2.4rem;font-weight:800;color:{primary};'
            f'letter-spacing:-0.5px;line-height:1;">{branding["app_name"]}</div>'
        )

    st.markdown(
        f"""
        <div style="text-align:center;padding:56px 0 24px 0;">
            {brand_html}
            <div style="font-size:11.5px;letter-spacing:.28em;color:#657286;
                        text-transform:uppercase;margin-top:10px;">
                {branding['tagline']}
            </div>
            <div style="font-size:1.7rem;font-weight:800;color:{primary};margin-top:18px;
                        line-height:1.3;max-width:580px;margin-left:auto;margin-right:auto;">
                Turn spreadsheets into boardroom-ready insights
            </div>
            <div style="font-size:1rem;color:#657286;margin-top:10px;line-height:1.7;
                        max-width:500px;margin-left:auto;margin-right:auto;">
                Without hiring a data analyst. Upload a file, get a clean dataset and
                a professional report in minutes — on any device.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1.5, 1, 1.5])
    with mid:
        if st.button("Sign in / Get started →", use_container_width=True, type="primary", key="_landing_signin"):
            st.session_state["_show_login"] = True
            st.rerun()

    _render_login_features(branding)

    st.markdown(
        f"""
        <div style="text-align:center;margin-top:2rem;padding-bottom:2rem;">
            <a href="{store_url}" target="_blank"
               style="display:inline-block;padding:10px 28px;
                      border:2px solid {primary};color:{primary};border-radius:8px;
                      font-size:0.85rem;font-weight:600;text-decoration:none;
                      letter-spacing:0.02em;">
                View Plans &amp; Pricing →
            </a>
            <div style="margin-top:1.2rem;font-size:0.73rem;color:#9CA3AF;">
                &copy; 2026 {branding.get('company', 'Coltrane Ltd')} &nbsp;&mdash;&nbsp;
                <a href="mailto:{contact}" style="color:{primary};text-decoration:none;">{contact}</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Informational sections on the login page ──────────────────────────────────

def _render_signup_guide(branding: dict) -> None:
    """'How to get started' guide shown below the sign-in card."""
    primary = branding["primary_colour"]
    store_url = "https://app.coltradata.com/Pricing"
    contact = branding.get("contact_email", "support@coltradata.com")

    st.markdown(
        f"""
        <div style="max-width:520px;margin:1.4rem auto 0 auto;
                    background:#F0F6FF;border:1px solid #C7D9F0;border-radius:14px;
                    padding:1.4rem 1.6rem;">
            <div style="font-size:0.92rem;font-weight:700;color:{primary};
                        margin-bottom:1rem;letter-spacing:0.01em;">
                New here? How to sign up
            </div>
            <div style="display:flex;flex-direction:column;gap:0.8rem;">
                <div style="display:flex;align-items:flex-start;gap:0.75rem;">
                    <div style="min-width:26px;height:26px;border-radius:50%;
                                background:{primary};color:#fff;
                                display:flex;align-items:center;justify-content:center;
                                font-size:0.76rem;font-weight:700;flex-shrink:0;margin-top:1px;">1</div>
                    <div>
                        <div style="font-size:0.83rem;font-weight:600;color:#1F2937;">
                            Choose a plan &amp; pay securely
                        </div>
                        <div style="font-size:0.76rem;color:#657286;margin-top:2px;line-height:1.5;">
                            Click <em>View Plans &amp; Pricing</em> below.
                            Select Starter, Professional, Premium, or Enterprise
                            and complete checkout via Lemon Squeezy.
                            A subscription confirmation email will be sent to you —
                            if it doesn't arrive, check your <strong>spam&nbsp;/&nbsp;junk</strong> folder.
                        </div>
                    </div>
                </div>
                <div style="display:flex;align-items:flex-start;gap:0.75rem;">
                    <div style="min-width:26px;height:26px;border-radius:50%;
                                background:{primary};color:#fff;
                                display:flex;align-items:center;justify-content:center;
                                font-size:0.76rem;font-weight:700;flex-shrink:0;margin-top:1px;">2</div>
                    <div>
                        <div style="font-size:0.83rem;font-weight:600;color:#1F2937;">
                            Return here &amp; sign in
                        </div>
                        <div style="font-size:0.76rem;color:#657286;margin-top:2px;line-height:1.5;">
                            Enter the email you used at checkout above.
                            We'll send a 6-digit verification code to that address.
                        </div>
                    </div>
                </div>
                <div style="display:flex;align-items:flex-start;gap:0.75rem;">
                    <div style="min-width:26px;height:26px;border-radius:50%;
                                background:{primary};color:#fff;
                                display:flex;align-items:center;justify-content:center;
                                font-size:0.76rem;font-weight:700;flex-shrink:0;margin-top:1px;">3</div>
                    <div>
                        <div style="font-size:0.83rem;font-weight:600;color:#1F2937;">
                            Your plan activates automatically
                        </div>
                        <div style="font-size:0.76rem;color:#657286;margin-top:2px;line-height:1.5;">
                            Once verified, your paid plan is detected from your account.
                            No licence key entry needed — your subscription is linked
                            to your email address.
                        </div>
                    </div>
                </div>
            </div>
            <div style="margin-top:1.1rem;padding-top:0.9rem;border-top:1px solid #C7D9F0;
                        text-align:center;">
                <a href="{store_url}" target="_blank"
                   style="display:inline-block;padding:9px 24px;
                          background:{primary};color:#fff;border-radius:8px;
                          font-size:0.83rem;font-weight:600;text-decoration:none;
                          letter-spacing:0.02em;">
                    View Plans &amp; Pricing →
                </a>
                <div style="margin-top:0.65rem;font-size:0.7rem;color:#9CA3AF;">
                    Want to explore first? Enter any email above — you'll start on the free plan.<br/>
                    Questions? <a href="mailto:{contact}"
                        style="color:{primary};text-decoration:none;">{contact}</a>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── CSS & visual components ───────────────────────────────────────────────────

def _inject_login_css(branding: dict) -> None:
    primary = branding["primary_colour"]
    st.markdown(
        f"""
        <style>
            [data-testid="stSidebar"] {{ display: none !important; }}
            [data-testid="collapsedControl"] {{ display: none !important; }}
            header {{ visibility: hidden !important; }}
            [data-testid="stHeader"] {{ display: none !important; }}
            [data-testid="stSidebarNav"] {{ display: none !important; }}
            #MainMenu {{ visibility: hidden !important; }}
            footer {{ visibility: hidden !important; }}
            [data-testid="stVerticalBlockBorderWrapper"] {{
                border-left: none !important;
                border: none !important;
                box-shadow: none !important;
                background: transparent !important;
                border-radius: 0 !important;
                margin-bottom: 0 !important;
            }}
            .block-container {{
                padding-top: 0 !important;
                max-width: 860px !important;
                margin: 0 auto !important;
            }}
            .stButton > button {{
                border-radius: 10px;
                height: 46px;
                background-color: {primary};
                color: white;
                font-weight: 600;
                border: none;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_login_header(branding: dict) -> None:
    primary = branding["primary_colour"]
    logo_path = branding.get("logo_path", "assets/logo/coltradata_logo.png")
    logo_b64 = _encode_logo(logo_path)

    if logo_b64:
        brand_html = (
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="height:52px;width:auto;display:block;margin:0 auto 8px auto;" />'
        )
    else:
        brand_html = (
            f'<div style="font-size:2.4rem;font-weight:800;color:{primary};'
            f'letter-spacing:-0.5px;line-height:1;">{branding["app_name"]}</div>'
        )

    st.markdown(
        f"""
        <div style="text-align:center;padding:56px 0 32px 0;">
            {brand_html}
            <div style="font-size:11.5px;letter-spacing:.28em;color:#657286;
                        text-transform:uppercase;margin-top:10px;">
                {branding['tagline']}
            </div>
            <div style="font-size:1rem;font-weight:700;color:{primary};margin-top:7px;letter-spacing:0.03em;">
                {branding.get('platform_line', 'Navigate the DataMaze.')}
            </div>
            <div style="font-size:0.87rem;color:#657286;margin-top:10px;line-height:1.6;">
                From raw, tangled data to clean, validated reports —<br/>
                built for the hybrid workforce.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("← Back", key="_login_back_to_landing", use_container_width=False):
        st.session_state.pop("_show_login", None)
        st.session_state.pop("_otp_step", None)
        st.session_state.pop("_otp_email", None)
        st.rerun()


def _render_login_features(branding: dict) -> None:
    primary = branding["primary_colour"]
    features = [
        ("🧭", "Find your way through messy data", "Upload any CSV or Excel — ColtraDataAi handles missing values, duplicates, and mixed types automatically."),
        ("✅", "Instant cleaning & validation", "AI-powered rules map your path through the DataMaze, fixing quality issues in seconds."),
        ("📊", "Boardroom-ready reports, on any device", "Export cleaned datasets with PDF summaries and chart galleries — delivered to your inbox or home screen."),
    ]
    cols = st.columns(3)
    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(
                f"""
                <div style="background:#FFFFFF;border:1px solid #E6ECF0;border-radius:14px;
                            padding:1.4rem 1.2rem;text-align:center;margin-top:1.6rem;
                            box-shadow:0 2px 10px rgba(0,0,0,0.04);">
                    <div style="font-size:1.7rem;margin-bottom:0.55rem;">{icon}</div>
                    <div style="font-size:0.9rem;font-weight:700;color:{primary};
                                margin-bottom:0.4rem;">{title}</div>
                    <div style="font-size:0.78rem;color:#657286;line-height:1.55;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown(
        f"""
        <div style="text-align:center;margin-top:2.8rem;font-size:0.73rem;color:#9CA3AF;">
            &copy; 2026 {branding.get('company', 'Coltrane Ltd')} &nbsp;&mdash;&nbsp;
            <a href="mailto:{branding['contact_email']}"
               style="color:{primary};text-decoration:none;">{branding['contact_email']}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Secrets helpers ───────────────────────────────────────────────────────────

def _get_email_cfg() -> dict:
    """Load Resend transactional email config from secrets / env vars."""
    try:
        cfg = st.secrets.get("email", {})
        return {
            "resend_api_key": cfg.get("resend_api_key", os.environ.get("RESEND_API_KEY", "")),
            "from_name": cfg.get("from_name", "ColtraDataAi"),
            "from_email": cfg.get("from_email", os.environ.get("FROM_EMAIL", "noreply@coltradata.com")),
        }
    except Exception:
        return {
            "resend_api_key": os.environ.get("RESEND_API_KEY", ""),
            "from_name": "ColtraDataAi",
            "from_email": os.environ.get("FROM_EMAIL", "noreply@coltradata.com"),
        }


def _get_admin_email() -> str:
    """Return the admin email from secrets, or '' if not configured."""
    try:
        return st.secrets.get("admin", {}).get("admin_email", os.environ.get("ADMIN_EMAIL", ""))
    except Exception:
        return os.environ.get("ADMIN_EMAIL", "")


# ── Logo helper ───────────────────────────────────────────────────────────────

def _encode_logo(logo_path: str) -> str:
    """Return base64-encoded logo string, or empty string if file not found."""
    if not os.path.exists(logo_path):
        return ""
    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode()
