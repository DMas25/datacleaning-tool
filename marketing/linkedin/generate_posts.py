"""
ColtraDataAi LinkedIn Post Generator
======================================
CLI runner that generates all 30 LinkedIn posts using the two-agent pipeline.

Usage:
  python -m marketing.linkedin.generate_posts                    # all 30 days
  python -m marketing.linkedin.generate_posts --day 5            # single day
  python -m marketing.linkedin.generate_posts --day 1 --day 7    # multiple days
  python -m marketing.linkedin.generate_posts --type use_case    # filter by type

Outputs:
  marketing/linkedin/posts/day_{N:02d}_{content_type}.txt        # individual posts
  marketing/linkedin/posts/all_posts.md                          # combined markdown
"""

import argparse
import os
import sys
import time
from pathlib import Path

from marketing.linkedin.content_calendar import CALENDAR, ContentDay
from marketing.linkedin.linkedin_agent import run_pipeline, AgentResult

POSTS_DIR = Path(__file__).parent / "posts"


def _save_post(result: AgentResult) -> Path:
    POSTS_DIR.mkdir(exist_ok=True)
    filename = f"day_{result.day:02d}_{result.content_type}.txt"
    path = POSTS_DIR / filename
    path.write_text(result.post, encoding="utf-8")
    return path


def _build_combined_markdown(results: list[AgentResult], days: list) -> str:
    day_map = {d.day: d for d in days}
    lines = [
        "# ColtraDataAi - 30-Day LinkedIn Content Plan\n",
        "**Routing key:** PERSONAL = David's personal profile | COMPANY = ColtraDataAi company page\n",
    ]
    for r in sorted(results, key=lambda x: x.day):
        d = day_map.get(r.day)
        account = ("PERSONAL PROFILE" if d and d.post_from == "personal" else "COMPANY PAGE") if d else "UNKNOWN"
        lines.append(f"## Day {r.day} - {r.content_type.replace('_', ' ').title()}")
        lines.append(f"**Post from:** {account}")
        lines.append(f"**Topic:** {r.topic}")
        lines.append(f"**Characters:** {r.char_count} | **Review passed:** {r.passed_review}")
        lines.append("")
        lines.append("```")
        lines.append(r.post)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _print_result(result: AgentResult, post_from: str) -> None:
    status = "PASS" if result.passed_review else "WARN"
    account = "PERSONAL PROFILE" if post_from == "personal" else "COMPANY PAGE"
    print(f"\n{'='*60}")
    print(f"Day {result.day:02d} | {result.content_type:20s} | {result.char_count} chars | {status}")
    print(f"Post from: {account}")
    print(f"Topic: {result.topic[:70]}")
    print("-" * 60)
    print(result.post)
    print(f"{'='*60}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate ColtraDataAi LinkedIn posts using Claude agents."
    )
    parser.add_argument(
        "--day",
        type=int,
        action="append",
        metavar="N",
        help="Day number(s) to generate (1-30). Repeatable. Default: all days.",
    )
    parser.add_argument(
        "--type",
        dest="content_type",
        choices=[
            "thought_leadership",
            "ai_insights",
            "product_feature",
            "use_case",
            "industry_commentary",
            "success_story",
        ],
        help="Filter to a specific content type.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        default=True,
        help="Save posts to marketing/linkedin/posts/ (default: True).",
    )
    parser.add_argument(
        "--no-save",
        dest="save",
        action="store_false",
        help="Do not save posts to disk.",
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        default=True,
        help="Save combined all_posts.md after generation (default: True).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds to wait between API calls (default: 1.5).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress post output - only show progress.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # Select days to process
    days: list[ContentDay] = CALENDAR
    if args.day:
        day_set = set(args.day)
        days = [d for d in days if d.day in day_set]
    if args.content_type:
        days = [d for d in days if d.content_type == args.content_type]

    if not days:
        print("No days matched the filters provided.", file=sys.stderr)
        sys.exit(1)

    print(f"\nColtraDataAi LinkedIn Agent")
    print(f"Generating {len(days)} post(s) using claude-sonnet-4-6 (writer) + claude-haiku-4-5 (reviewer)")
    print(f"Output directory: {POSTS_DIR.resolve()}\n")

    results: list[AgentResult] = []
    failed: list[int] = []

    for i, day in enumerate(days, start=1):
        print(f"[{i}/{len(days)}] Day {day.day:02d}: {day.topic[:55]}...", end=" ", flush=True)
        try:
            result = run_pipeline(day, api_key=api_key, verbose=False)
            results.append(result)
            account = "PERSONAL" if day.post_from == "personal" else "COMPANY PAGE"
            status = "OK" if result.passed_review else "WARN"
            print(f"{result.char_count} chars - {status} - {account}")
            if not args.quiet:
                _print_result(result, day.post_from)
            if args.save:
                saved_path = _save_post(result)
                if args.quiet:
                    print(f"  Saved: {saved_path.name}")
        except Exception as exc:
            print(f"ERROR: {exc}")
            failed.append(day.day)

        if i < len(days):
            time.sleep(args.delay)

    # Save combined markdown
    if args.save and args.combined and results:
        combined_path = POSTS_DIR / "all_posts.md"
        combined_path.write_text(_build_combined_markdown(results, days), encoding="utf-8")
        print(f"\nCombined markdown saved: {combined_path.resolve()}")

    # Summary
    print(f"\n--- Summary ---")
    print(f"Generated: {len(results)} posts")
    if failed:
        print(f"Failed days: {failed} (rerun with --day N to retry)")
    warns = [r for r in results if not r.passed_review]
    if warns:
        print(f"Review warnings: Day(s) {[r.day for r in warns]} - check character count or em dashes manually")
    else:
        print("All posts passed brand compliance review.")


if __name__ == "__main__":
    main()
