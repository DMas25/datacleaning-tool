"""
ColtraDataAi LinkedIn Agent System
====================================
Two-agent pipeline:
  PostWriterAgent  - generates a LinkedIn post from a ContentDay brief
  ReviewerAgent    - checks brand voice compliance and refines if needed

Usage:
  from marketing.linkedin.linkedin_agent import run_pipeline
  result = run_pipeline(content_day)
"""

import os
import re
from dataclasses import dataclass

import anthropic

from marketing.linkedin.content_calendar import ContentDay

# ---------------------------------------------------------------------------
# Brand context injected into every agent call
# ---------------------------------------------------------------------------

_BRAND_CONTEXT = """
BRAND: ColtraDataAi by Coltrane Ltd
WEBSITE: app.coltradata.com
ENTERPRISE API: coltradata-api.onrender.com

FOUNDER: David Maswodza. Former tax specialist (Zimbabwe). Then UK trade consultant
focusing on AfCFTA and UK-Africa trade corridors. Built ColtraDataAi to solve the data
quality problem he observed first-hand: small business data arriving at accountants and
bookkeepers in a chaotic, inconsistent state.

PRODUCT: A domain-specific data cleaning engine with eight industry cleaners:
Finance & Accounting, Logistics & Supply Chain, Retail & Inventory, Import/Export & Trade,
Healthcare (Operational), Consultants & Professional Services, SME & Small Business,
and Hospitality & Accommodation.

POSITIONING: Strictly a data cleaning and validation tool. NOT an advisory, analytics, or
consulting platform. Outputs are descriptive and observational. The tool tells you what
is wrong with the data - it does not tell you what to do about it as a business.

PRICING:
- Free: 3 runs, 5,000 rows
- Starter: £29/month - 50 runs, 50k rows, AI insights + Excel
- Professional: £99/month - 200 runs, 250k rows, API access, full reports
- Business: £299/month - 1,000 runs, 1M rows, branded reports, unlimited API
- Enterprise: £999/month contact-only (Book a Demo)
- Enterprise API: £499/month standalone REST API

TARGET AUDIENCE: SME owners, bookkeepers, accountants, operations managers,
logistics coordinators, healthcare operations staff, trade compliance teams,
consultants, and developers building data pipelines.

TONE: Professional, direct, practitioner-focused. No hype. No buzzwords for their own sake.
Credibility comes from specificity - cite real validation checks, real data problems, real
time savings. The founder voice is honest and grounded.

LINKEDIN FORMAT RULES:
- 150 to 1,900 characters total (aim for 800-1,400 for strong engagement)
- Start with a hook line that stands alone (no context needed)
- Use short paragraphs - max 3 lines each
- Line breaks between paragraphs for readability
- End with a clear CTA line
- Append hashtags on a separate final line (5-7 hashtags)
- NEVER use em dashes (--) - use hyphens (-) or restructure the sentence
- NEVER use advisory language: "you should", "we recommend", "you must", "action required"
- NEVER claim the tool provides business advice or interpretation
- The tool describes what the data shows. That is all.
"""

_WRITER_SYSTEM = f"""
You are the LinkedIn content writer for ColtraDataAi.

{_BRAND_CONTEXT}

Your job: write a single LinkedIn post based on the brief provided.
Return ONLY the post text - no preamble, no metadata, no explanation.

FORMATTING:
- Hook line first (short, standalone)
- Body in short paragraphs separated by blank lines
- CTA line near the end
- Hashtag line last (start with a blank line before hashtags)
- Never use em dashes (--). Use hyphens (-) or rewrite.
- Keep it human and specific. Avoid generic AI-sounding phrases.
"""

_REVIEWER_SYSTEM = f"""
You are the brand compliance reviewer for ColtraDataAi LinkedIn content.

{_BRAND_CONTEXT}

REVIEW CHECKLIST - flag and fix any of these issues:
1. Em dashes (--) present - replace with hyphen (-) or rewrite the clause
2. Advisory language: "you should", "we recommend", "you must" - remove or reframe
3. Claims that the tool provides business interpretation - rewrite to descriptive only
4. Post exceeds 1,900 characters - trim
5. Post is under 400 characters - too short, expand
6. Missing CTA - add one
7. Missing or misplaced hashtags - fix format
8. Hyperbolic claims ("the best", "the only", "revolutionary") - tone down
9. UK spelling violations (favour, colour, licence, etc.) - correct to UK English

Return the reviewed and corrected post ONLY.
If the post passes all checks without changes, return it unchanged.
Do not add any commentary before or after the post text.
"""


@dataclass
class AgentResult:
    day: int
    content_type: str
    topic: str
    post: str
    char_count: int
    passed_review: bool


def _has_em_dash(text: str) -> bool:
    return "—" in text or "--" in text


def _char_count(text: str) -> int:
    return len(text)


def _build_writer_prompt(day: ContentDay) -> str:
    return f"""
Day {day.day} - {day.content_type.replace("_", " ").title()}

TOPIC: {day.topic}

ANGLE (use this as your content foundation):
{day.angle}

CTA TO USE: {day.cta}

HASHTAGS TO INCLUDE: {", ".join("#" + h for h in day.hashtags)}

Write the LinkedIn post now.
""".strip()


def _build_reviewer_prompt(post: str, day: ContentDay) -> str:
    return f"""
Review this LinkedIn post for Day {day.day} ({day.content_type}):

---
{post}
---

Apply the brand compliance checklist and return the corrected post.
""".strip()


class PostWriterAgent:
    """Generates a LinkedIn post from a ContentDay brief using claude-sonnet-4-6."""

    def __init__(self, client: anthropic.Anthropic, model: str = "claude-sonnet-4-6"):
        self.client = client
        self.model = model

    def write(self, day: ContentDay) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=_WRITER_SYSTEM,
            messages=[{"role": "user", "content": _build_writer_prompt(day)}],
        )
        return response.content[0].text.strip()


class ReviewerAgent:
    """Checks brand voice compliance and returns a corrected post using claude-haiku-4-5."""

    def __init__(self, client: anthropic.Anthropic, model: str = "claude-haiku-4-5-20251001"):
        self.client = client
        self.model = model

    def review(self, post: str, day: ContentDay) -> tuple[str, bool]:
        """Returns (reviewed_post, changed) where changed=True if the reviewer made edits."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=_REVIEWER_SYSTEM,
            messages=[{"role": "user", "content": _build_reviewer_prompt(post, day)}],
        )
        reviewed = response.content[0].text.strip()
        changed = reviewed != post
        return reviewed, changed


def run_pipeline(
    day: ContentDay,
    api_key: str | None = None,
    verbose: bool = False,
) -> AgentResult:
    """
    Full two-agent pipeline: write then review.
    Returns an AgentResult with the final post and metadata.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set and no api_key provided.")

    client = anthropic.Anthropic(api_key=key)

    writer = PostWriterAgent(client)
    reviewer = ReviewerAgent(client)

    if verbose:
        print(f"  [Writer] Generating Day {day.day}: {day.topic[:60]}...")
    draft = writer.write(day)

    if verbose:
        print(f"  [Reviewer] Reviewing Day {day.day}...")
    final_post, changed = reviewer.review(draft, day)

    if verbose and changed:
        print(f"  [Reviewer] Edits applied on Day {day.day}.")

    passed = not _has_em_dash(final_post) and 400 <= _char_count(final_post) <= 1900

    return AgentResult(
        day=day.day,
        content_type=day.content_type,
        topic=day.topic,
        post=final_post,
        char_count=_char_count(final_post),
        passed_review=passed,
    )
