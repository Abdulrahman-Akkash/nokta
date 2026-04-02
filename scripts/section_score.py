#!/usr/bin/env python3
"""
section_score.py — Nokta program.md Ratchet Scorer

Reads checklist YAMLs and scores the corresponding section in program.md,
or scores an entire specs/*.md file against checklists/spec_generic.yml.
Used by CI to auto-merge or reject PRs.

Usage:
    python scripts/section_score.py --section 4
    python scripts/section_score.py --all
    python scripts/section_score.py --section 4 --main-score 65
    python scripts/section_score.py --spec-file specs/my-feature.md
    python scripts/section_score.py --spec-file specs/my-feature.md --ci-comment
"""

import argparse
import re
import sys
import os

try:
    import yaml
except ImportError:
    # CI environments may need: pip install pyyaml
    print("ERROR: PyYAML required. Run: pip install pyyaml")
    sys.exit(1)


def load_checklist(section_num: int) -> dict:
    """Load checklist YAML for a given section number."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "checklists", f"section_{section_num:02d}.yml"
    )
    if not os.path.exists(path):
        print(f"ERROR: Checklist not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_spec_checklist() -> dict:
    """Load the generic spec checklist YAML for specs/*.md files."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "checklists", "spec_generic.yml"
    )
    if not os.path.exists(path):
        print(f"ERROR: spec_generic.yml not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_section(md_content: str, section_pattern: str) -> str:
    """Extract content of a specific section from program.md."""
    # Find section start
    start_match = re.search(re.escape(section_pattern), md_content)
    if not start_match:
        return ""

    start_pos = start_match.end()

    # Find next section (## N.) or end of file
    next_section = re.search(r"\n## \d+\.", md_content[start_pos:])
    if next_section:
        end_pos = start_pos + next_section.start()
    else:
        end_pos = len(md_content)

    return md_content[start_pos:end_pos].strip()


def check_pattern(content: str, check: dict) -> bool:
    """Evaluate a single checklist item against section content."""
    pattern = check.get("pattern", "")
    inverted = check.get("inverted", False)

    # Skip TODO-only sections (but not for inverted checks — those catch TODOs)
    if not inverted:
        stripped = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()
        if stripped.startswith("> TODO") and len(stripped) < 100:
            return False

    # Check minimum occurrences
    if "min_occurrences" in check:
        p = check.get("min_occurrences_pattern", pattern)
        matches = re.findall(p, content, re.IGNORECASE)
        result = len(matches) >= check["min_occurrences"]
        return (not result) if inverted else result

    # Check minimum list items
    if "min_list_items" in check:
        list_items = re.findall(r"^[\s]*[-*]\s+.+", content, re.MULTILINE)
        result = len(list_items) >= check["min_list_items"]
        return (not result) if inverted else result

    # Check min lines with pattern
    if "min_lines_with_pattern" in check:
        matching_lines = [
            line
            for line in content.split("\n")
            if re.search(pattern, line, re.IGNORECASE)
        ]
        result = len(matching_lines) >= check["min_lines_with_pattern"]
        return (not result) if inverted else result

    # Default: pattern exists anywhere in content
    if pattern:
        result = bool(re.search(pattern, content, re.IGNORECASE))
        return (not result) if inverted else result

    return False


def score_spec_file(file_content: str, checklist: dict) -> dict:
    """Score an entire specs/*.md file against spec_generic.yml."""
    words = len(file_content.split())
    min_words = checklist.get("min_words", 0)
    word_check_pass = words >= min_words

    results = []
    total_weight = 0
    earned_weight = 0

    for check in checklist.get("checks", []):
        weight = check.get("weight", 10)
        total_weight += weight
        passed = check_pattern(file_content, check)
        if passed:
            earned_weight += weight
        results.append(
            {
                "id": check["id"],
                "description": check["description"],
                "passed": passed,
                "weight": weight,
                "inverted": check.get("inverted", False),
            }
        )

    if not word_check_pass and min_words > 0:
        score = 0
    elif total_weight > 0:
        score = round((earned_weight / total_weight) * 100)
    else:
        score = 0

    return {
        "section": "spec",
        "title": checklist.get("title", "GENERIC SPEC"),
        "score": score,
        "word_count": words,
        "min_words": min_words,
        "word_check_pass": word_check_pass,
        "checks": results,
    }


def score_section(md_content: str, checklist: dict) -> dict:
    """Score a section against its checklist. Returns score details."""
    section_content = extract_section(md_content, checklist["file_pattern"])

    # Word count check
    words = len(section_content.split())
    min_words = checklist.get("min_words", 0)
    word_check_pass = words >= min_words

    results = []
    total_weight = 0
    earned_weight = 0

    for check in checklist.get("checks", []):
        weight = check.get("weight", 10)
        total_weight += weight
        passed = check_pattern(section_content, check)
        if passed:
            earned_weight += weight
        results.append(
            {
                "id": check["id"],
                "description": check["description"],
                "passed": passed,
                "weight": weight,
            }
        )

    # Word count is a gate, not weighted
    if not word_check_pass and min_words > 0:
        score = 0
    elif total_weight > 0:
        score = round((earned_weight / total_weight) * 100)
    else:
        score = 0

    return {
        "section": checklist["section"],
        "title": checklist["title"],
        "score": score,
        "word_count": words,
        "min_words": min_words,
        "word_check_pass": word_check_pass,
        "checks": results,
    }


def format_report(result: dict) -> str:
    """Format scoring result as a readable report."""
    lines = []
    lines.append(f"## Section {result['section']}: {result['title']}")
    lines.append(f"**Score: {result['score']}/100**")
    lines.append(
        f"Words: {result['word_count']}/{result['min_words']} "
        f"({'✅' if result['word_check_pass'] else '❌ GATE FAIL'})"
    )
    lines.append("")

    for check in result["checks"]:
        icon = "✅" if check["passed"] else "❌"
        lines.append(
            f"  {icon} [{check['weight']}pt] {check['description']}"
        )

    lines.append("")
    return "\n".join(lines)


def format_ci_comment(results: list, main_scores: dict = None) -> str:
    """Format results as a GitHub PR comment."""
    lines = ["# 🎯 Nokta program.md Ratchet Score\n"]

    any_regression = False

    for r in results:
        main_score = main_scores.get(r["section"], 0) if main_scores else 0
        delta = r["score"] - main_score
        status = "✅" if delta >= 0 else "❌ REGRESSION"
        if delta < 0:
            any_regression = True

        lines.append(
            f"| Section {r['section']} | {r['title']} | "
            f"**{r['score']}** | main: {main_score} | {delta:+d} | {status} |"
        )

    lines.insert(1, "| Section | Title | Score | Main | Delta | Status |")
    lines.insert(2, "|---------|-------|-------|------|-------|--------|")

    lines.append("")
    if any_regression:
        lines.append("## ❌ REJECTED — Score regression detected. Fix and push again.")
    else:
        lines.append("## ✅ ELIGIBLE FOR MERGE — All sections maintained or improved.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Score Nokta program.md sections or specs/*.md files")
    parser.add_argument("--section", type=int, help="Score a specific section (0-12)")
    parser.add_argument("--all", action="store_true", help="Score all sections")
    parser.add_argument(
        "--main-score",
        type=int,
        default=None,
        help="Current main branch score for comparison",
    )
    parser.add_argument(
        "--md-file",
        default="program.md",
        help="Path to program.md (default: program.md)",
    )
    parser.add_argument(
        "--spec-file",
        default=None,
        help="Path to a specs/*.md file to score against spec_generic.yml",
    )
    parser.add_argument(
        "--ci-comment", action="store_true", help="Output as GitHub PR comment format"
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 if any section regresses",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (only for --all or --spec-file)",
    )

    args = parser.parse_args()

    # --- spec-file mode ---
    if args.spec_file is not None:
        if not os.path.exists(args.spec_file):
            print(f"ERROR: {args.spec_file} not found")
            sys.exit(1)
        with open(args.spec_file, "r", encoding="utf-8") as f:
            spec_content = f.read()
        checklist = load_spec_checklist()
        result = score_spec_file(spec_content, checklist)
        
        if args.json:
            import json
            print(json.dumps(result, indent=2))
            return

        if args.ci_comment:
            main_scores = {}
            if args.main_score is not None:
                main_scores["spec"] = args.main_score
            print(format_ci_comment([result], main_scores))
        else:
            print(format_report(result))

        if args.fail_on_regression and args.main_score is not None:
            if result["score"] < args.main_score:
                sys.exit(1)
        return

    # --- program.md section mode ---
    if not os.path.exists(args.md_file):
        print(f"ERROR: {args.md_file} not found")
        sys.exit(1)

    with open(args.md_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Determine which sections to score
    if args.all:
        sections = range(0, 13)
    elif args.section is not None:
        sections = [args.section]
    else:
        print("ERROR: Specify --section N or --all or --spec-file <path>")
        sys.exit(1)

    results = []
    for sec_num in sections:
        checklist = load_checklist(sec_num)
        result = score_section(md_content, checklist)
        results.append(result)

    # Output
    if args.json:
        import json
        total = sum(r["score"] for r in results)
        avg = round(total / len(results)) if results else 0
        output = {
            "total_average": avg,
            "sections": results
        }
        print(json.dumps(output, indent=2))
        return

    if args.ci_comment:
        main_scores = {}
        if args.main_score is not None and args.section is not None:
            main_scores[args.section] = args.main_score
        print(format_ci_comment(results, main_scores))
    else:
        for r in results:
            print(format_report(r))

    # Exit code for CI
    if args.fail_on_regression and args.main_score is not None:
        for r in results:
            if r["score"] < args.main_score:
                sys.exit(1)

    # Print total score
    if len(results) > 1:
        total = sum(r["score"] for r in results)
        avg = round(total / len(results))
        print(f"\n**TOTAL AVERAGE: {avg}/100**")



if __name__ == "__main__":
    main()
