"""
ColtraDataAi - 30-Day LinkedIn Content Calendar
================================================
Six content types rotated across 30 days:
  1. ai_insights        - AI and data trends
  2. use_case           - Domain-specific data analytics use cases
  3. industry_commentary - Market problems ColtraDataAi solves
  4. success_story      - Client/composite success stories
  5. product_feature    - Feature walkthroughs and demonstrations
  6. thought_leadership - Founder POV and bigger-picture articles

Posting account routing:
  personal - David's personal LinkedIn profile (voice-driven, opinion-led content)
  company  - ColtraDataAi company page (brand/product content)

Rule: thought_leadership, ai_insights, industry_commentary -> personal
      product_feature, use_case, success_story              -> company
"""

from dataclasses import dataclass
from typing import Literal

ContentType = Literal[
    "thought_leadership",
    "ai_insights",
    "product_feature",
    "use_case",
    "industry_commentary",
    "success_story",
]

PostFrom = Literal["personal", "company"]

# Maps each content type to the correct LinkedIn account
_ROUTING: dict[str, PostFrom] = {
    "thought_leadership": "personal",
    "ai_insights": "personal",
    "industry_commentary": "personal",
    "product_feature": "company",
    "use_case": "company",
    "success_story": "company",
}


@dataclass
class ContentDay:
    day: int
    content_type: ContentType
    topic: str
    angle: str
    cta: str
    hashtags: list[str]

    @property
    def post_from(self) -> PostFrom:
        return _ROUTING[self.content_type]


CALENDAR: list[ContentDay] = [
    # --- WEEK 1: Foundation and brand introduction ---
    ContentDay(
        day=1,
        content_type="thought_leadership",
        topic="The founder story: from a Zimbabwe tax desk to a UK data cleaning platform",
        angle=(
            "Personal narrative. Former tax specialist in Zimbabwe watching small business "
            "clients arrive with chaotic, inconsistent spreadsheets. That experience — combined "
            "with UK trade consulting work across AfCFTA corridors — is what ColtraDataAi was "
            "built to solve. The problem is not new; the tool finally is."
        ),
        cta="Follow for 30 days of content on AI, data quality, and what clean data actually means for your business.",
        hashtags=["DataQuality", "FounderStory", "SME", "UKBusiness", "AfCFTA", "ColtraDataAi"],
    ),
    ContentDay(
        day=2,
        content_type="ai_insights",
        topic="AI cannot fix what dirty data breaks",
        angle=(
            "AI models are only as good as the data fed into them. Garbage in, garbage out — "
            "this is not a new principle, but it is being re-learned at scale as businesses rush "
            "to deploy AI tools without first standardising their inputs. The first step is not "
            "AI adoption. It is data readiness."
        ),
        cta="What does your data look like before it goes into your reports? Drop a comment.",
        hashtags=["AI", "DataQuality", "MachineLearning", "DataStrategy", "ColtraDataAi"],
    ),
    ContentDay(
        day=3,
        content_type="product_feature",
        topic="What ColtraDataAi actually does: a plain-language overview",
        angle=(
            "Not another analytics platform. ColtraDataAi is a domain-specific data cleaning engine "
            "with eight industry cleaners: Finance, Logistics, Retail, Trade, Healthcare, SME, "
            "Consultant, and Hospitality. Upload a CSV or connect via API. Get a cleaned dataset, "
            "a flagged issues report, KPI summary, and exportable Excel and PDF outputs. That is it."
        ),
        cta="Start free at app.coltradata.com - no card required.",
        hashtags=["DataCleaning", "ColtraDataAi", "SME", "DataTools", "Productivity"],
    ),
    ContentDay(
        day=4,
        content_type="use_case",
        topic="Finance and Accounting cleaner: what it catches and what it produces",
        angle=(
            "The Finance cleaner validates: duplicate transaction IDs, inconsistent debit/credit "
            "labelling, missing amounts, currency format mismatches, and negative balance anomalies. "
            "Output: flagged rows, a clean dataset, and a summary of financial data quality issues "
            "ready for your bookkeeper or accountant."
        ),
        cta="Try the Finance cleaner free - link in comments.",
        hashtags=["AccountingTech", "Bookkeeping", "FinanceData", "DataQuality", "ColtraDataAi", "SME"],
    ),
    ContentDay(
        day=5,
        content_type="industry_commentary",
        topic="The hidden cost of dirty data in UK SME finance",
        angle=(
            "UK SMEs spend an estimated 20-30% of accounting time correcting data before any "
            "analysis can begin. That is not analysis time. That is clean-up time. At a typical "
            "bookkeeper hourly rate, a small business owner is paying for someone to fix their "
            "spreadsheets, not interpret them. There is a cheaper way to get to interpretation."
        ),
        cta="How much time does your team spend cleaning before reporting? Tell me below.",
        hashtags=["SME", "UKBusiness", "Bookkeeping", "DataQuality", "FinancialOperations", "ColtraDataAi"],
    ),
    ContentDay(
        day=6,
        content_type="success_story",
        topic="How a UK-based SME cut pre-accountant data prep from 4 hours to 20 minutes",
        angle=(
            "A retail SME owner was spending four hours every month sorting, deduplicating, and "
            "reformatting transaction data before sending it to their bookkeeper. After uploading "
            "to ColtraDataAi with the SME cleaner, the same dataset was cleaned, validated, and "
            "exported in under 20 minutes. The bookkeeper received a structured Excel file with "
            "flagged issues highlighted. No back-and-forth required."
        ),
        cta="Book a demo or start free at app.coltradata.com.",
        hashtags=["ClientSuccess", "SME", "DataCleaning", "UKBusiness", "Bookkeeping", "ColtraDataAi"],
    ),
    ContentDay(
        day=7,
        content_type="thought_leadership",
        topic="The 80/20 rule in data work: why analysts spend most of their time cleaning",
        angle=(
            "Industry surveys consistently report that data professionals spend 60-80% of their "
            "time on data preparation, not analysis. This is not a skills gap. It is an infrastructure "
            "gap. Businesses invest in dashboards and analytics tools before solving the input problem. "
            "The question to ask is not 'what does our data show?' but 'is our data ready to show anything?'"
        ),
        cta="What percentage of your team's time goes to data prep? Honest answers only.",
        hashtags=["DataAnalytics", "DataEngineering", "Productivity", "ThoughtLeadership", "ColtraDataAi"],
    ),

    # --- WEEK 2: Domain depth and practitioner voice ---
    ContentDay(
        day=8,
        content_type="ai_insights",
        topic="AI-powered validation vs manual spreadsheet checking: a practical comparison",
        angle=(
            "Manual checking: time-intensive, inconsistent, relies on the checker knowing what "
            "to look for. Rule-based AI validation: fast, reproducible, domain-aware. ColtraDataAi "
            "runs 40-plus validation checks per domain in seconds. A human auditing the same dataset "
            "row by row takes hours and still misses systematic issues like silent duplicates or "
            "normalisation drift across columns."
        ),
        cta="See the validation check list for your industry at app.coltradata.com.",
        hashtags=["AI", "DataValidation", "Automation", "DataQuality", "ColtraDataAi"],
    ),
    ContentDay(
        day=9,
        content_type="use_case",
        topic="Logistics and Supply Chain cleaner: what breaks in supply chain data and how we flag it",
        angle=(
            "Common logistics data issues: duplicate shipment IDs, impossible transit times (negative "
            "or zero days), missing carrier codes, weight/unit inconsistencies, and destination "
            "format mismatches. The ColtraDataAi Logistics cleaner catches all of these and produces "
            "a flagged report ready for your operations or planning team."
        ),
        cta="Supply chain teams: try the Logistics cleaner free. Link in comments.",
        hashtags=["Logistics", "SupplyChain", "DataQuality", "Operations", "ColtraDataAi"],
    ),
    ContentDay(
        day=10,
        content_type="industry_commentary",
        topic="Bookkeepers are the first line of data defence - and they should not have to be",
        angle=(
            "Every bookkeeper knows the feeling: a client sends over three months of transactions "
            "in a spreadsheet with five different date formats, inconsistent category labels, and "
            "duplicate rows. The bookkeeper fixes it before they can even begin. This is skilled "
            "time spent on unskilled work. It is also a missed opportunity for the client, whose "
            "data could have been clean on arrival."
        ),
        cta="Bookkeepers: what is the most common data error you fix for clients? Comment below.",
        hashtags=["Bookkeeping", "AccountingTech", "SME", "DataQuality", "UKAccounting", "ColtraDataAi"],
    ),
    ContentDay(
        day=11,
        content_type="success_story",
        topic="Import/Export company: trade data cleaned before customs submission",
        angle=(
            "A UK-based import/export SME was losing time to inconsistent product code formatting, "
            "missing country-of-origin fields, and duplicate shipment records before each customs "
            "filing. Using the ColtraDataAi Trade cleaner, they validated and standardised their "
            "shipping dataset in minutes. Issues were flagged with row-level detail so the ops "
            "team could correct only what needed correcting, not rebuild the whole file."
        ),
        cta="Trade and import/export teams: start free at app.coltradata.com.",
        hashtags=["ImportExport", "TradeData", "Customs", "SupplyChain", "ColtraDataAi", "UKBusiness"],
    ),
    ContentDay(
        day=12,
        content_type="product_feature",
        topic="Why domain-specific cleaners outperform generic data cleaning tools",
        angle=(
            "A generic cleaner can spot blank cells and duplicate rows. A domain cleaner knows "
            "that a negative ADR in hospitality data is an error, that a zero-night hotel stay "
            "is impossible, and that 'OTA' and 'Online Travel Agency' are the same channel. "
            "Context-aware validation is what separates useful cleaning from checkbox cleaning."
        ),
        cta="See all eight domain cleaners at app.coltradata.com.",
        hashtags=["DataCleaning", "DomainExpertise", "DataQuality", "AI", "ColtraDataAi"],
    ),
    ContentDay(
        day=13,
        content_type="thought_leadership",
        topic="AfCFTA and the data quality challenge hiding inside African cross-border trade",
        angle=(
            "The African Continental Free Trade Area creates enormous opportunity - and enormous "
            "data complexity. Cross-border trade data across AfCFTA corridors arrives in multiple "
            "formats, classification systems, and naming conventions. Businesses trying to report "
            "on or analyse that data face a cleaning problem before they face an analytics problem. "
            "This is not unique to Africa. It is simply more visible there because the systems are "
            "newer and the standards are still being harmonised."
        ),
        cta="Coltrane Ltd and ColtraDataAi were both built with this corridor in mind.",
        hashtags=["AfCFTA", "AfricanTrade", "TradeData", "DataQuality", "ColtraDataAi", "UKAfrica"],
    ),
    ContentDay(
        day=14,
        content_type="ai_insights",
        topic="What large language models can and cannot do with structured data",
        angle=(
            "LLMs are impressive at language tasks. They are not reliable validators of structured "
            "tabular data. They hallucinate missing values, miss systematic duplicates, and cannot "
            "apply domain-aware rules consistently. For structured data quality work, rule-based "
            "validation with domain context outperforms general-purpose AI every time. Use LLMs "
            "for interpretation. Use structured validation for cleaning."
        ),
        cta="See how domain-aware validation differs from AI summarisation at app.coltradata.com.",
        hashtags=["LLM", "AI", "DataValidation", "StructuredData", "DataQuality", "ColtraDataAi"],
    ),

    # --- WEEK 3: Scale, API, and analytics depth ---
    ContentDay(
        day=15,
        content_type="product_feature",
        topic="The ColtraDataAi Enterprise API: clean data at scale via REST",
        angle=(
            "For teams that cannot afford manual upload workflows at volume, the Enterprise API "
            "exposes all eight domain cleaners via a single REST endpoint: POST /v1/clean/{domain}. "
            "Accepts CSV or JSON. Returns a cleaned dataset and a structured findings object. "
            "Bearer token auth, usage logging per call, and Swagger docs included. Built on FastAPI, "
            "deployed at coltradata-api.onrender.com."
        ),
        cta="Enterprise API starts at £499/month. Docs at coltradata-api.onrender.com/docs.",
        hashtags=["API", "EnterpriseData", "DataEngineering", "FastAPI", "ColtraDataAi", "DataQuality"],
    ),
    ContentDay(
        day=16,
        content_type="use_case",
        topic="Retail and Inventory cleaner: catching stock data errors before they reach the P&L",
        angle=(
            "Retail data errors that the ColtraDataAi cleaner catches: negative stock quantities, "
            "duplicate SKUs, price fields in wrong currency format, missing product categories, "
            "and inconsistent unit-of-measure labels. These errors, left unchecked, distort inventory "
            "valuations, reorder signals, and margin calculations."
        ),
        cta="Retail teams: try the Inventory cleaner free at app.coltradata.com.",
        hashtags=["Retail", "Inventory", "DataQuality", "StockManagement", "ColtraDataAi", "RetailTech"],
    ),
    ContentDay(
        day=17,
        content_type="industry_commentary",
        topic="Excel is still the backbone of SME finance - and that is not a problem",
        angle=(
            "There is a tendency in the technology space to treat Excel as a legacy problem to be "
            "replaced. For most UK SMEs, Excel is not legacy - it is practical. The problem is not "
            "that businesses use spreadsheets. The problem is that the spreadsheets arrive messy. "
            "A tool that works with Excel rather than against it is more useful than one that demands "
            "businesses change how they work."
        ),
        cta="ColtraDataAi accepts CSV uploads and exports cleaned Excel files. Meet the user where they are.",
        hashtags=["Excel", "SME", "UKBusiness", "DataQuality", "FinancialOperations", "ColtraDataAi"],
    ),
    ContentDay(
        day=18,
        content_type="success_story",
        topic="Healthcare operations manager: audit-ready data in half the time",
        angle=(
            "A healthcare operations team was preparing for a quarterly audit and found their patient "
            "appointment and billing data riddled with inconsistent status codes, duplicate patient "
            "records, and date format mismatches across two systems. Using the ColtraDataAi Healthcare "
            "cleaner, they identified and flagged 340 issues across 4,200 rows in minutes. The cleaned "
            "export was structured and ready for the auditor without a manual review pass."
        ),
        cta="Healthcare operations teams: start free at app.coltradata.com.",
        hashtags=["Healthcare", "DataQuality", "HealthcareOperations", "Audit", "ColtraDataAi"],
    ),
    ContentDay(
        day=19,
        content_type="product_feature",
        topic="What is in the output: Excel reports, PDF executive summaries, and KPI banners",
        angle=(
            "After cleaning, ColtraDataAi produces three outputs: a multi-sheet Excel report "
            "(cleaned data, flagged issues, summary statistics, and charts), a PDF executive "
            "summary with KPI highlights, and a dashboard view with visual breakdowns. All outputs "
            "are branded and ready to share with a client or senior stakeholder without further "
            "formatting work."
        ),
        cta="See a sample report - link in comments.",
        hashtags=["DataReporting", "ExcelReports", "PDF", "DataQuality", "ColtraDataAi", "BusinessIntelligence"],
    ),
    ContentDay(
        day=20,
        content_type="thought_leadership",
        topic="Data cleaning is not glamorous. It is essential.",
        angle=(
            "Nobody builds a career by talking about data cleaning. The conferences are about AI, "
            "analytics, and insights. But every insight in every dashboard sits on top of a dataset "
            "that someone had to clean. The unglamorous first step is the one that determines whether "
            "everything after it is trustworthy. Until the industry starts treating data quality as "
            "infrastructure rather than overhead, this will remain the invisible problem."
        ),
        cta="What is your take: is data quality finally getting the attention it deserves?",
        hashtags=["DataQuality", "ThoughtLeadership", "DataStrategy", "Analytics", "ColtraDataAi"],
    ),
    ContentDay(
        day=21,
        content_type="ai_insights",
        topic="Real-time data validation: where automated cleaning is heading",
        angle=(
            "Batch cleaning - upload, process, download - is the current standard for most teams. "
            "The direction of travel is toward real-time validation at the point of entry: forms "
            "that flag issues as data is entered, APIs that validate on ingestion, and pipelines "
            "that reject malformed records before they land. The ColtraDataAi API is a step in this "
            "direction: validate at the point your data moves, not after it has settled."
        ),
        cta="Explore the Enterprise API at coltradata-api.onrender.com/docs.",
        hashtags=["RealTimeData", "DataValidation", "API", "DataEngineering", "AI", "ColtraDataAi"],
    ),

    # --- WEEK 4: Broader reach, pricing, and CTA push ---
    ContentDay(
        day=22,
        content_type="use_case",
        topic="Healthcare operational data: the validation checks that matter most",
        angle=(
            "Healthcare operational datasets - not clinical records, but appointment logs, billing "
            "records, and staff scheduling data - share common data quality problems: status code "
            "drift, duplicate patient IDs, impossible appointment sequences, and missing billing "
            "amounts. The ColtraDataAi Healthcare cleaner applies 35-plus checks built around these "
            "operational realities."
        ),
        cta="Healthcare ops teams: see the full check list at app.coltradata.com.",
        hashtags=["HealthcareTech", "DataQuality", "HealthcareOperations", "NHS", "ColtraDataAi"],
    ),
    ContentDay(
        day=23,
        content_type="industry_commentary",
        topic="The data quality gap that is costing UK SMEs access to growth capital",
        angle=(
            "When a UK SME applies for finance - whether from a bank, investor, or grant body - "
            "one of the first things a lender reviews is financial data. Inconsistent transaction "
            "records, unexplained gaps, and formatting errors create doubt before the numbers are "
            "even read. A clean, structured financial dataset is not just good hygiene. It is a "
            "credibility signal."
        ),
        cta="How does your financial data look to an outsider? Start a free clean at app.coltradata.com.",
        hashtags=["SMEFinance", "UKBusiness", "StartupFunding", "DataQuality", "ColtraDataAi", "BusinessGrowth"],
    ),
    ContentDay(
        day=24,
        content_type="success_story",
        topic="Consulting practice: client deliverables without the pre-delivery data scramble",
        angle=(
            "A management consulting team was preparing a client data deliverable and received source "
            "data in three different formats with inconsistent column naming across submissions. "
            "Rather than manually harmonising the files, they ran each through the ColtraDataAi "
            "Consultant cleaner and merged the standardised outputs. Total prep time: 35 minutes "
            "instead of a half-day manual process."
        ),
        cta="Consultants and professional services teams: start free at app.coltradata.com.",
        hashtags=["Consulting", "ProfessionalServices", "DataQuality", "Productivity", "ColtraDataAi"],
    ),
    ContentDay(
        day=25,
        content_type="product_feature",
        topic="Pricing explained: from Free to Enterprise - what each tier gives you",
        angle=(
            "Free: 3 runs, 5,000 rows - enough to evaluate. "
            "Starter (£29/month): 50 runs, 50,000 rows, AI insights and Excel export. "
            "Professional (£99/month): 200 runs, 250,000 rows, API access, full reports. "
            "Business (£299/month): 1,000 runs, 1M rows, branded reports, unlimited API calls. "
            "Enterprise: contact for SLA, dedicated database, and onboarding. "
            "Every tier starts with the same domain-specific validation engine."
        ),
        cta="Start free - no card required. app.coltradata.com.",
        hashtags=["Pricing", "SaaS", "DataQuality", "SME", "ColtraDataAi", "DataTools"],
    ),
    ContentDay(
        day=26,
        content_type="thought_leadership",
        topic="Built for practitioners, not platforms: why ColtraDataAi does not try to do everything",
        angle=(
            "The data tooling market is full of all-in-one platforms that promise to clean, analyse, "
            "visualise, and predict. ColtraDataAi does one thing: it cleans domain-specific data and "
            "tells you exactly what was wrong and why. It does not interpret the results or tell you "
            "what to do next. That is the accountant's job, the analyst's job, the operator's job. "
            "A tool that knows its boundaries is more useful than one that overreaches."
        ),
        cta="What do you think: focused tools or all-in-one platforms? I would like to hear your view.",
        hashtags=["ProductPhilosophy", "SaaS", "DataTools", "ThoughtLeadership", "ColtraDataAi"],
    ),
    ContentDay(
        day=27,
        content_type="ai_insights",
        topic="Automation in accounting: where we are now and where the next five years lead",
        angle=(
            "Automated bank reconciliation, OCR receipt capture, and AI-categorised transactions "
            "are already live in major accounting platforms. The next wave: automated pre-submission "
            "data validation, anomaly detection at ingestion, and structured quality reporting built "
            "into the workflow rather than bolted on after. ColtraDataAi sits at the start of that wave."
        ),
        cta="What accounting automation are you already using? Comment below.",
        hashtags=["AccountingTech", "FinTech", "Automation", "AI", "ColtraDataAi", "FutureOfFinance"],
    ),
    ContentDay(
        day=28,
        content_type="use_case",
        topic="Hospitality and Accommodation cleaner: booking data validation before revenue reporting",
        angle=(
            "Hospitality data issues ColtraDataAi flags: duplicate booking references, impossible "
            "check-in/check-out sequences (zero-night or extended stays flagged), room type "
            "normalisation (Double, King, Suite variants unified), channel standardisation "
            "(OTA vs Direct vs Corporate), and ADR outlier detection. KPIs produced: cancellation "
            "rate, average daily rate, no-show rate, total revenue, average revenue per booking."
        ),
        cta="Hospitality operations teams: try the Hospitality cleaner free. app.coltradata.com.",
        hashtags=["Hospitality", "HotelData", "RevenueManagement", "DataQuality", "ColtraDataAi"],
    ),
    ContentDay(
        day=29,
        content_type="industry_commentary",
        topic="Clean data is not a nice-to-have. It is the prerequisite for every business decision.",
        angle=(
            "Every forecast, every budget, every investment decision, every operational change "
            "in a business traces back to data. If the data it rests on is inconsistent, duplicated, "
            "or incorrectly formatted, the decision built on it is unstable. Businesses that treat "
            "data quality as a downstream concern - something to fix when a problem surfaces - are "
            "building on an unverified foundation. Clean data first is not a methodology. It is common sense."
        ),
        cta="What is the biggest data quality issue your team deals with? Share it below.",
        hashtags=["DataQuality", "BusinessStrategy", "DataDriven", "Analytics", "ColtraDataAi"],
    ),
    ContentDay(
        day=30,
        content_type="thought_leadership",
        topic="30 days, one message: clean data is where good decisions start",
        angle=(
            "This is the final post in a 30-day series on data quality, AI, and what ColtraDataAi "
            "was built to solve. The consistent message across every post: you cannot analyse, "
            "report on, or trust data that has not been cleaned. Not with AI. Not with dashboards. "
            "Not with any tool. The foundation has to be solid. ColtraDataAi is that foundation layer - "
            "the step before the step everyone talks about. If this content was useful, follow for "
            "more. If you want to see what the tool can do, start free below."
        ),
        cta="Start free at app.coltradata.com. No card required.",
        hashtags=["DataQuality", "ColtraDataAi", "AI", "DataStrategy", "30DayChallenge", "UKBusiness"],
    ),
]
