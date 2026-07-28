"""
Healthcare IT & Information Security Audit Tool.

    python audit.py new      -- open a new audit engagement
    python audit.py fieldwork <audit.json>   -- work through the control programme
    python audit.py status   <audit.json>    -- progress and score so far
    python audit.py report   <audit.json>    -- render the HTML report + CAPA csv
    python audit.py demo     -- generate a fully worked example audit and report
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from datetime import date
from pathlib import Path

from engine import Audit, STATUSES, DOWNGRADE
from report import render_html, render_markdown, export_capa_csv

if hasattr(sys.stdout, "reconfigure"):          # keep box drawing readable on Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
DEFAULT_CHECKLIST = HERE / "checklists" / "healthcare_it_grc.json"

STATUS_KEYS = {
    "c": "compliant",
    "p": "partial",
    "n": "non_compliant",
    "x": "not_applicable",
    "s": "not_tested",       # skip - leave untested
}


def rule(char="=", width=78):
    print(char * width)


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


# --------------------------------------------------------------------------
# new
# --------------------------------------------------------------------------

def cmd_new(args):
    checklist = Path(args.checklist)
    if not checklist.exists():
        sys.exit(f"Checklist not found: {checklist}")

    print()
    rule()
    print(" NEW AUDIT ENGAGEMENT")
    rule()
    entity = args.entity or ask("Organisation being audited", "Northgate Health Group")
    site = args.site or ask("Site / scope", "All sites - central IT")
    auditor = args.auditor or ask("Lead auditor")
    start = args.start or ask("Audit period start (YYYY-MM-DD)")
    end = args.end or ask("Audit period end (YYYY-MM-DD)", date.today().isoformat())
    notes = args.notes if args.notes is not None else ask("Additional scope notes (optional)", "")

    audit = Audit.from_checklist(
        checklist, entity=entity, site=site, lead_auditor=auditor,
        period_start=start, period_end=end, scope_notes=notes,
    )
    out = Path(args.out or f"audit_{audit.audit_ref}.json")
    audit.save(out)
    print(f"\nCreated {audit.audit_ref} covering {sum(1 for _ in audit.all_checks())} controls.")
    print(f"Working file: {out}")
    print(f"\nNext:  python audit.py fieldwork \"{out}\"")


# --------------------------------------------------------------------------
# fieldwork
# --------------------------------------------------------------------------

def cmd_fieldwork(args):
    path = Path(args.audit)
    audit = Audit.load(path)

    print()
    rule()
    print(f" FIELDWORK - {audit.audit_ref} - {audit.entity}")
    rule()
    print(" c = compliant   p = partial   n = non-compliant   x = n/a   s = skip")
    print(" q = save and quit at any prompt\n")

    for section in audit.framework["sections"]:
        pending = [c for c in section["checks"]
                   if args.all or audit.results[c["id"]].status == "not_tested"]
        if not pending:
            continue

        print()
        rule("-")
        print(f" {section['id']} - {section['title'].upper()}")
        print(f" Objective: {section['objective']}")
        rule("-")

        for check in pending:
            result = audit.results[check["id"]]
            print(f"\n[{check['id']}]  {check['title']}   ({check.get('severity','medium').upper()})")
            print(f"  Objective : {check['control_objective']}")
            print(f"  Test      : {check['test_procedure']}")
            print(f"  Evidence  : {'; '.join(check.get('evidence_expected', []))}")
            if result.status != "not_tested":
                print(f"  Recorded  : {STATUSES[result.status]}")

            choice = ""
            while choice not in STATUS_KEYS and choice != "q":
                choice = input("  Result (c/p/n/x/s/q) > ").strip().lower()
            if choice == "q":
                audit.save(path)
                print(f"\nSaved to {path}.")
                return

            status = STATUS_KEYS[choice]
            if status == "not_tested":
                continue

            fields = {"evidence_ref": ask("  Working paper / evidence ref", result.evidence_ref)}
            if status in ("compliant", "not_applicable"):
                fields["observation"] = ask("  Note (optional)", result.observation)
            else:
                fields["sample_size"] = ask("  Sample tested", result.sample_size)
                fields["observation"] = ask("  Observation (what was found)", result.observation)
                fields["root_cause"] = ask("  Root cause", result.root_cause)
                fields["risk_statement"] = ask("  Risk / impact", result.risk_statement)
                fields["corrective_action"] = ask("  Recommendation", result.corrective_action)
                fields["action_owner"] = ask("  Action owner", result.action_owner)
                control_sev = check.get("severity", "medium")
                default_sev = DOWNGRADE.get(control_sev, control_sev) if status == "partial" \
                    else control_sev
                fields["severity_override"] = ask(
                    f"  Finding severity (blank = {default_sev})", result.severity_override)
                fields["due_date"] = ask("  Target date (blank = SLA default)", result.due_date)

            audit.record(check["id"], status, **fields)
            if audit.results[check["id"]].is_finding():
                print(f"  -> finding raised, target date {audit.results[check['id']].due_date}")
            audit.save(path)

    audit.save(path)
    print("\nProgramme complete.")
    _print_status(audit)
    print(f"\nNext:  python audit.py report \"{path}\"")


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------

def _print_status(audit: Audit):
    o = audit.overall()
    print()
    rule()
    print(f" {audit.audit_ref} - {audit.entity} ({audit.site})")
    rule()
    print(f" Controls tested   : {o['tested']}/{o['total']}")
    score = f"{o['score']}%" if o["score"] is not None else "n/a"
    label = f"{o['rating']} assurance" if o["score"] is not None else o["rating"]
    print(f" Compliance score  : {score}   [{label}]")
    print(f" Findings          : {o['counts']['non_compliant']} failed, "
          f"{o['counts']['partial']} partial")
    sev = o["findings_by_severity"]
    print(f" By severity       : critical {sev['critical']}, high {sev['high']}, "
          f"medium {sev['medium']}, low {sev['low']}")
    print(f" Risk exposure     : {o['risk']} (weighted)")
    print()
    print(f" {'DOMAIN':<44}{'TESTED':>8}{'SCORE':>8}  ASSURANCE")
    rule("-")
    for section in audit.framework["sections"]:
        s = audit.section_stats(section)
        sc = f"{s['score']}%" if s["score"] is not None else "-"
        print(f" {s['id']} {s['title'][:40]:<41}{s['assessed']}/{s['total']:<5}{sc:>8}  {s['rating']}")
    rule("-")
    print(f" OVERALL OPINION: {o['opinion']}")

    overdue = audit.overdue_actions()
    if overdue:
        print(f"\n {len(overdue)} corrective action(s) past their target date:")
        for row in overdue:
            print(f"   {row['check']['id']:<8} due {row['result'].due_date}  "
                  f"{row['result'].action_owner or 'unassigned'}")


def cmd_status(args):
    _print_status(Audit.load(args.audit))


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def cmd_report(args):
    audit = Audit.load(args.audit)
    if args.report_date:
        audit.report_date = args.report_date
    stem = args.out or f"{audit.audit_ref}_report"
    html_path = render_html(audit, Path(f"{stem}.html"))
    csv_path = export_capa_csv(audit, Path(f"{stem}_action_plan.csv"))
    _print_status(audit)
    print(f"\nReport      : {html_path.resolve()}")
    print(f"Action plan : {csv_path.resolve()}")
    if args.markdown:
        md_path = render_markdown(audit, Path(f"{stem}.md"))
        print(f"Markdown    : {md_path.resolve()}")
    if not args.no_open:
        webbrowser.open(html_path.resolve().as_uri())


# --------------------------------------------------------------------------
# demo
# --------------------------------------------------------------------------

def cmd_demo(args):
    from demo_data import build_demo
    audit = build_demo(DEFAULT_CHECKLIST)
    work = Path(args.out or "demo_audit.json")
    audit.save(work)
    html_path = render_html(audit, work.with_name(f"{work.stem}_report.html"))
    csv_path = export_capa_csv(audit, work.with_name(f"{work.stem}_action_plan.csv"))
    # docs/ is what GitHub serves: the Markdown copy renders in the repo browser,
    # and index.html is published as the live site by GitHub Pages.
    md_path = render_markdown(audit, HERE / "docs" / "EXAMPLE_REPORT.md")
    site_path = render_html(audit, HERE / "docs" / "index.html")
    _print_status(audit)
    print(f"\nWorking file : {work.resolve()}")
    print(f"Report       : {html_path.resolve()}")
    print(f"Action plan  : {csv_path.resolve()}")
    print(f"Markdown     : {md_path.resolve()}")
    print(f"Pages site   : {site_path.resolve()}")
    if not args.no_open:
        webbrowser.open(html_path.resolve().as_uri())


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="open a new audit engagement")
    n.add_argument("--checklist", default=str(DEFAULT_CHECKLIST))
    n.add_argument("--entity"); n.add_argument("--site"); n.add_argument("--auditor")
    n.add_argument("--start"); n.add_argument("--end"); n.add_argument("--out")
    n.add_argument("--notes", help="scope notes (pass to avoid the prompt)")
    n.set_defaults(func=cmd_new)

    f = sub.add_parser("fieldwork", help="work through the control programme")
    f.add_argument("audit")
    f.add_argument("--all", action="store_true", help="revisit controls already tested")
    f.set_defaults(func=cmd_fieldwork)

    s = sub.add_parser("status", help="progress and score so far")
    s.add_argument("audit")
    s.set_defaults(func=cmd_status)

    r = sub.add_parser("report", help="render the HTML report and CAPA csv")
    r.add_argument("audit")
    r.add_argument("--out", help="output stem (no extension)")
    r.add_argument("--report-date")
    r.add_argument("--markdown", action="store_true",
                   help="also write a Markdown copy of the report")
    r.add_argument("--no-open", action="store_true")
    r.set_defaults(func=cmd_report)

    d = sub.add_parser("demo", help="generate a fully worked example audit")
    d.add_argument("--out"); d.add_argument("--no-open", action="store_true")
    d.set_defaults(func=cmd_demo)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
