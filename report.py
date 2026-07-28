"""Report rendering: self-contained HTML report and CSV action-plan export."""

from __future__ import annotations

import csv
import html
from datetime import date
from pathlib import Path

from engine import Audit, STATUSES

RATING_CLASS = {
    "Substantial": "r-sub",
    "Reasonable": "r-rea",
    "Limited": "r-lim",
    "No assurance": "r-non",
    "Not assessed": "r-na",
}

STATUS_CLASS = {
    "compliant": "s-ok",
    "partial": "s-part",
    "non_compliant": "s-fail",
    "not_applicable": "s-na",
    "not_tested": "s-untested",
}

CSS = """
:root{
  --bg:#04080f; --panel:rgba(10,26,42,.62); --panel-2:rgba(8,20,34,.9);
  --fg:#cfe9f7; --bright:#eaf7ff; --muted:#6f93ab;
  --cy:#3fd0f5; --cy-dim:rgba(63,208,245,.28); --cy-faint:rgba(63,208,245,.09);
  --ok:#3ce6a8; --part:#f7b23b; --fail:#ff5f56; --crit:#ff2d55;
  --mono:ui-monospace,"Cascadia Mono","Consolas","SF Mono",monospace;
}
*{box-sizing:border-box}
body{margin:0;color:var(--fg);background:var(--bg);
font:14px/1.6 "Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background-image:
  radial-gradient(900px 500px at 15% -8%,rgba(63,208,245,.13),transparent 62%),
  radial-gradient(700px 460px at 92% 4%,rgba(63,208,245,.07),transparent 60%),
  linear-gradient(rgba(63,208,245,.032) 1px,transparent 1px),
  linear-gradient(90deg,rgba(63,208,245,.032) 1px,transparent 1px);
background-size:auto,auto,44px 44px,44px 44px;background-attachment:fixed}

.page{max-width:1120px;margin:0 auto;padding:40px 46px 56px;position:relative;
background:linear-gradient(180deg,rgba(8,22,38,.72),rgba(4,10,18,.72));
border-left:1px solid var(--cy-dim);border-right:1px solid var(--cy-dim)}

h1{font-size:26px;line-height:1.24;margin:0 0 6px;color:var(--bright);font-weight:600;
letter-spacing:.005em;text-shadow:0 0 26px rgba(63,208,245,.4)}
h2{font-size:13px;margin:44px 0 14px;padding:0 0 8px;color:var(--cy);font-weight:700;
text-transform:uppercase;letter-spacing:.16em;font-family:var(--mono);
border-bottom:1px solid var(--cy-dim);position:relative}
h2::after{content:"";position:absolute;left:0;bottom:-1px;width:64px;height:1px;
background:var(--cy);box-shadow:0 0 10px var(--cy)}
h3{font-size:12px;margin:26px 0 10px;color:var(--bright);font-family:var(--mono);
text-transform:uppercase;letter-spacing:.13em}
p{margin:0 0 12px}
ul,ol{margin:0 0 12px;padding-left:20px}
li{margin:4px 0}
.sub{color:var(--muted);font-size:12.5px}

/* --- masthead ------------------------------------------------------ */
.masthead{position:relative;padding:20px 0 20px 20px;margin-bottom:6px;
border-bottom:1px solid var(--cy-dim);border-left:2px solid var(--cy)}
.masthead::before{content:"";position:absolute;left:-2px;top:0;width:16px;height:1px;
background:var(--cy);box-shadow:0 0 8px var(--cy)}
.tag{display:inline-block;color:var(--cy);background:var(--cy-faint);
border:1px solid var(--cy-dim);font-family:var(--mono);font-size:10px;letter-spacing:.22em;
text-transform:uppercase;padding:4px 12px;margin-bottom:12px}

/* --- key/value grid ------------------------------------------------ */
.meta{display:grid;grid-template-columns:repeat(2,1fr);gap:0 34px;margin:20px 0 4px}
.meta div{display:flex;justify-content:space-between;gap:16px;padding:7px 0;
border-bottom:1px solid rgba(63,208,245,.13)}
.meta span:first-child{color:var(--muted);font-family:var(--mono);font-size:11px;
text-transform:uppercase;letter-spacing:.1em;white-space:nowrap}
.meta span:last-child{color:var(--bright);font-weight:600;text-align:right}

/* --- stat panels --------------------------------------------------- */
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}
.card{position:relative;background:var(--panel);border:1px solid var(--cy-dim);
padding:16px 16px 14px;overflow:hidden}
.card::before,.card::after{content:"";position:absolute;width:11px;height:11px;
border:1px solid var(--cy);opacity:.85}
.card::before{top:5px;left:5px;border-right:0;border-bottom:0}
.card::after{bottom:5px;right:5px;border-left:0;border-top:0}
.card .l{font-family:var(--mono);font-size:10px;text-transform:uppercase;
letter-spacing:.16em;color:var(--muted);margin-bottom:6px}
.card .v{font-family:var(--mono);font-size:30px;font-weight:700;line-height:1.1;
color:var(--cy);text-shadow:0 0 22px rgba(63,208,245,.5);margin-bottom:6px}

.opinion{position:relative;background:var(--panel-2);border:1px solid var(--cy-dim);
border-left:3px solid var(--cy);padding:16px 20px;margin:18px 0}
.opinion b{color:var(--cy);font-family:var(--mono);text-transform:uppercase;
letter-spacing:.1em;font-size:11.5px}

/* --- tables -------------------------------------------------------- */
.tw{overflow-x:auto;margin:12px 0 4px;border:1px solid var(--cy-dim);background:var(--panel)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:620px}
th,td{padding:9px 12px;text-align:left;vertical-align:top;
border-bottom:1px solid rgba(63,208,245,.11)}
th{background:rgba(63,208,245,.07);color:var(--cy);font-family:var(--mono);font-weight:600;
font-size:10.5px;text-transform:uppercase;letter-spacing:.13em;
border-bottom:1px solid var(--cy-dim);white-space:nowrap}
tbody tr:hover{background:rgba(63,208,245,.045)}
tbody tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;white-space:nowrap;font-family:var(--mono)}

/* --- meters -------------------------------------------------------- */
.bar{position:relative;height:6px;background:rgba(63,208,245,.12);min-width:110px;
overflow:hidden;margin-bottom:5px}
.bar i{display:block;height:100%;background:var(--ok);box-shadow:0 0 12px var(--ok)}
.bar.warn i{background:var(--part);box-shadow:0 0 12px var(--part)}
.bar.bad i{background:var(--fail);box-shadow:0 0 12px var(--fail)}
.bar+.sub{font-family:var(--mono);font-size:11.5px;color:var(--bright)}

/* --- state chips --------------------------------------------------- */
.pill{display:inline-block;padding:3px 10px;font-family:var(--mono);font-size:10px;
font-weight:700;letter-spacing:.1em;text-transform:uppercase;white-space:nowrap;
border:1px solid currentColor}
.r-sub{color:var(--ok);background:rgba(60,230,168,.1)}
.r-rea{color:var(--cy);background:var(--cy-faint)}
.r-lim{color:var(--part);background:rgba(247,178,59,.1)}
.r-non{color:var(--fail);background:rgba(255,95,86,.1)}
.r-na{color:var(--muted);background:rgba(111,147,171,.1)}
.s-ok{color:var(--ok);font-weight:600} .s-part{color:var(--part);font-weight:600}
.s-fail{color:var(--fail);font-weight:700} .s-na,.s-untested{color:var(--muted)}
.sev{display:inline-block;padding:3px 8px;font-family:var(--mono);font-size:9.5px;
font-weight:700;text-transform:uppercase;letter-spacing:.13em;border:1px solid currentColor}
.sev-critical{color:var(--crit);background:rgba(255,45,85,.14)}
.sev-high{color:var(--fail);background:rgba(255,95,86,.12)}
.sev-medium{color:var(--part);background:rgba(247,178,59,.12)}
.sev-low{color:var(--muted);background:rgba(111,147,171,.12)}

/* --- finding modules ----------------------------------------------- */
.finding{position:relative;margin:20px 0;background:var(--panel);
border:1px solid var(--cy-dim);border-left:3px solid var(--fail)}
.finding.partial{border-left-color:var(--part)}
.finding .hd{display:flex;justify-content:space-between;align-items:center;gap:14px;
padding:12px 16px;background:rgba(63,208,245,.06);
border-bottom:1px solid var(--cy-dim)}
.finding .hd b{font-size:13.5px;color:var(--bright);letter-spacing:.01em}
.finding .bd{padding:6px 16px 14px}
.finding dl{margin:0;display:grid;grid-template-columns:158px 1fr;gap:0}
.finding dt{color:var(--cy);font-family:var(--mono);font-size:10px;text-transform:uppercase;
letter-spacing:.13em;padding:11px 14px 11px 0;
border-bottom:1px solid rgba(63,208,245,.09)}
.finding dd{margin:0;padding:11px 0;border-bottom:1px solid rgba(63,208,245,.09)}
.finding dl>:nth-last-child(-n+2){border-bottom:0}

.map{font-family:var(--mono);font-size:10.5px;color:var(--muted);letter-spacing:.04em}
.map code{color:var(--cy);background:var(--cy-faint);border:1px solid rgba(63,208,245,.16);
padding:1px 6px;font-size:10.5px}
.overdue{color:var(--crit);font-weight:700;font-family:var(--mono)}

.foot{margin-top:48px;padding-top:16px;border-top:1px solid var(--cy-dim);
font-size:11.5px;color:var(--muted);line-height:1.7}

@media (max-width:960px){.page{padding:24px 18px 40px;border:0}
.cards{grid-template-columns:repeat(2,1fr)}.meta{grid-template-columns:1fr}
.finding dl{grid-template-columns:1fr}
.finding dt{padding-bottom:0;border:0}
.finding .hd{flex-direction:column;align-items:flex-start;gap:6px}}

/* Printed copies flatten to ink-friendly light. */
@media print{
  body{background:#fff;background-image:none;color:#16202b}
  .page{max-width:none;padding:0;border:0;background:none}
  h1,.card .v,.finding .hd b{color:#16202b;text-shadow:none}
  h2,h3,.finding dt,.map code,.opinion b{color:#1f3a5f}
  .card,.opinion,.finding,.tw,th{background:#f6f8fa}
  .card::before,.card::after{display:none}
  th,td,.tw,.card,.finding,.opinion,h2{border-color:#c9d3de}
  .bar i{box-shadow:none}
  .tw{overflow:visible}table{min-width:0}
  h2{page-break-after:avoid}.finding{page-break-inside:avoid}
}
"""


def e(text) -> str:
    return html.escape(str(text or ""))


def _bar(score):
    if score is None:
        return '<span class="sub">n/a</span>'
    cls = "" if score >= 80 else ("warn" if score >= 60 else "bad")
    return (f'<div class="bar {cls}"><i style="width:{score}%"></i></div>'
            f'<span class="sub">{score}%</span>')


def _mappings(check) -> str:
    maps = check.get("mappings", {})
    labels = {"iso27001": "ISO 27001", "dspt": "DSPT", "cyber_essentials": "Cyber Essentials",
              "uk_gdpr": "UK GDPR", "hipaa_security": "HIPAA Security"}
    parts = [f"{labels.get(k, k)}: <code>{e(v)}</code>" for k, v in maps.items() if v]
    return " &nbsp;|&nbsp; ".join(parts)


def render_html(audit: Audit, out_path: str | Path) -> Path:
    o = audit.overall()
    fw = audit.framework
    findings = audit.findings()
    overdue_ids = {r["check"]["id"] for r in audit.overdue_actions()}
    report_date = audit.report_date or date.today().isoformat()

    p: list[str] = []
    p.append(f"<style>{CSS}</style><div class='page'>")

    # --- masthead -------------------------------------------------
    p.append(f"""
<div class="masthead">
  <div class="tag">Internal Audit Report &middot; Confidential</div>
  <h1>IT &amp; Information Security Audit &mdash; {e(audit.entity)}</h1>
  <div class="sub">{e(fw['framework_name'])} v{e(fw['version'])} &middot;
  Reference {e(audit.audit_ref)}</div>
</div>
<div class="meta">
  <div><span>Auditee / site</span><span>{e(audit.site)}</span></div>
  <div><span>Report date</span><span>{e(report_date)}</span></div>
  <div><span>Lead auditor</span><span>{e(audit.lead_auditor)}</span></div>
  <div><span>Audit period</span><span>{e(audit.period_start)} to {e(audit.period_end)}</span></div>
  <div><span>Controls in programme</span><span>{o['total']}</span></div>
  <div><span>Controls tested</span><span>{o['tested']}</span></div>
</div>""")

    # --- executive summary ---------------------------------------
    counts = o["counts"]
    p.append("<h2>1. Executive Summary</h2>")
    p.append(f"""
<div class="cards">
  <div class="card"><div class="l">Compliance score</div>
    <div class="v">{o['score'] if o['score'] is not None else '&ndash;'}%</div>
    <span class="pill {RATING_CLASS[o['rating']]}">{e(o['rating'])}{' assurance' if o['score'] is not None else ''}</span></div>
  <div class="card"><div class="l">Findings raised</div>
    <div class="v">{len(findings)}</div>
    <span class="sub">{counts['non_compliant']} failed, {counts['partial']} partial</span></div>
  <div class="card"><div class="l">Critical / high</div>
    <div class="v">{o['findings_by_severity']['critical']} / {o['findings_by_severity']['high']}</div>
    <span class="sub">by finding severity</span></div>
  <div class="card"><div class="l">Risk exposure</div>
    <div class="v">{o['risk']}</div>
    <span class="sub">weighted score</span></div>
</div>
<div class="opinion"><b>Audit opinion.</b> {e(o['opinion'])}</div>""")

    if findings:
        top = findings[:5]
        p.append("<h3>Key matters for management attention</h3><ol>")
        for row in top:
            p.append(f"<li><b>{e(row['check']['id'])} &ndash; {e(row['check']['title'])}.</b> "
                     f"{e(row['result'].observation)}</li>")
        p.append("</ol>")

    # --- scope ----------------------------------------------------
    p.append("<h2>2. Scope, Objective &amp; Methodology</h2>")
    p.append(f"<p>{e(fw.get('scope_statement',''))}</p>")
    if audit.scope_notes:
        p.append(f"<p>{e(audit.scope_notes)}</p>")
    p.append("<p>Testing was performed through a combination of enquiry of responsible officers, "
             "observation of processes in operation, inspection of system configuration and "
             "documentary evidence, and re-performance of selected control activities on a sample "
             "basis. Controls were assessed against the following frameworks:</p><ul>")
    for f in fw.get("primary_frameworks", []):
        p.append(f"<li>{e(f)}</li>")
    p.append("</ul>")
    p.append("<p>Each control is rated <b>Compliant</b> (designed and operating effectively), "
             "<b>Partially compliant</b> (control exists but with gaps in design or operation), "
             "<b>Non-compliant</b> (control absent or ineffective), or <b>Not applicable</b>. "
             "The compliance score is calculated as (compliant + 0.5 &times; partial) &divide; "
             "controls assessed.</p>")
    p.append("<p>Each finding is rated at the severity of the underlying control where the "
             "control was absent or ineffective, and one level below it where the control "
             "exists but operates with gaps, unless the auditor has judged otherwise. "
             "Remediation deadlines follow the finding severity: "
             + ", ".join(f"{k} {v} days" for k, v in
                         fw.get("severity_sla_days", {}).items()) + ".</p>")

    # --- domain results ------------------------------------------
    p.append("<h2>3. Results by Control Domain</h2>")
    p.append("<div class='tw'><table><thead><tr><th>Ref</th><th>Control domain</th>"
             "<th class='num'>Tested</th><th class='num'>Pass</th><th class='num'>Partial</th>"
             "<th class='num'>Fail</th><th>Score</th><th>Assurance</th></tr></thead><tbody>")
    for section in fw["sections"]:
        s = audit.section_stats(section)
        c = s["counts"]
        p.append(f"""<tr><td><b>{e(s['id'])}</b></td><td>{e(s['title'])}</td>
<td class="num">{s['assessed']}/{s['total']}</td>
<td class="num s-ok">{c['compliant']}</td>
<td class="num s-part">{c['partial']}</td>
<td class="num s-fail">{c['non_compliant']}</td>
<td>{_bar(s['score'])}</td>
<td><span class="pill {RATING_CLASS[s['rating']]}">{e(s['rating'])}</span></td></tr>""")
    p.append("</tbody></table></div>")

    # --- findings register ---------------------------------------
    p.append("<h2>4. Findings &amp; Recommendations</h2>")
    if not findings:
        p.append("<p>No exceptions were identified in the controls tested.</p>")
    for i, row in enumerate(findings, 1):
        check, res, section = row["check"], row["result"], row["section"]
        sev = row["severity"]
        cls = "finding partial" if res.status == "partial" else "finding"
        due = e(res.due_date)
        if check["id"] in overdue_ids:
            due = f'<span class="overdue">{due} &mdash; OVERDUE</span>'
        p.append(f"""
<div class="{cls}">
  <div class="hd">
    <b>Finding {i:02d} &middot; {e(check['id'])} &mdash; {e(check['title'])}</b>
    <span><span class="sev sev-{e(sev)}">{e(sev)}</span>
    <span class="{STATUS_CLASS[res.status]}">{e(STATUSES[res.status])}</span></span>
  </div>
  <div class="bd"><dl>
    <dt>Domain</dt><dd>{e(section['id'])} &ndash; {e(section['title'])}</dd>
    <dt>Control objective</dt><dd>{e(check['control_objective'])}</dd>
    <dt>Test performed</dt><dd>{e(check['test_procedure'])}
      {f"<br><span class='sub'>Sample: {e(res.sample_size)}</span>" if res.sample_size else ""}</dd>
    <dt>Observation</dt><dd>{e(res.observation)}</dd>
    <dt>Root cause</dt><dd>{e(res.root_cause) or '<span class="sub">Not determined</span>'}</dd>
    <dt>Risk / impact</dt><dd>{e(res.risk_statement)}</dd>
    <dt>Recommendation</dt><dd>{e(res.corrective_action)}</dd>
    <dt>Management response</dt><dd>{e(res.management_response) or '<span class="sub">Awaiting response</span>'}</dd>
    <dt>Owner</dt><dd>{e(res.action_owner) or '<span class="sub">Unassigned</span>'}</dd>
    <dt>Target date</dt><dd>{due or '<span class="sub">Not set</span>'}</dd>
    <dt>Evidence ref</dt><dd>{e(res.evidence_ref) or '<span class="sub">&ndash;</span>'}</dd>
  </dl>
  <div class="map" style="padding-top:8px">{_mappings(check)}</div>
  </div>
</div>""")

    # --- action plan ---------------------------------------------
    p.append("<h2>5. Corrective Action Plan</h2>")
    if findings:
        p.append("<div class='tw'><table><thead><tr><th>Ref</th><th>Severity</th><th>Agreed action</th>"
                 "<th>Owner</th><th>Target date</th></tr></thead><tbody>")
        for row in findings:
            check, res = row["check"], row["result"]
            sev = row["severity"]
            due = e(res.due_date) or "&ndash;"
            if check["id"] in overdue_ids:
                due = f'<span class="overdue">{due}</span>'
            p.append(f"""<tr><td><b>{e(check['id'])}</b></td>
<td><span class="sev sev-{e(sev)}">{e(sev)}</span></td>
<td>{e(res.corrective_action)}</td><td>{e(res.action_owner) or '&ndash;'}</td>
<td>{due}</td></tr>""")
        p.append("</tbody></table></div>")
    else:
        p.append("<p>No corrective actions arising.</p>")

    # --- full control log ----------------------------------------
    p.append("<h2>Appendix A &ndash; Detailed Control Test Log</h2>")
    p.append("<div class='tw'><table><thead><tr><th>Ref</th><th>Control</th><th>Control severity</th>"
             "<th>Result</th><th>Evidence ref</th></tr></thead><tbody>")
    for section in fw["sections"]:
        p.append(f"<tr><td colspan='5' style='background:#f6f8fa'><b>{e(section['id'])} &ndash; "
                 f"{e(section['title'])}</b></td></tr>")
        for check in section["checks"]:
            res = audit.results.get(check["id"])
            status = res.status if res else "not_tested"
            p.append(f"""<tr><td>{e(check['id'])}</td><td>{e(check['title'])}</td>
<td><span class="sev sev-{e(check.get('severity','medium'))}">{e(check.get('severity','medium'))}</span></td>
<td class="{STATUS_CLASS[status]}">{e(STATUSES[status])}</td>
<td class="sub">{e(res.evidence_ref) if res else ''}</td></tr>""")
    p.append("</tbody></table></div>")

    p.append(f"""<div class="foot">
Prepared by {e(audit.lead_auditor)} &middot; {e(audit.entity)} &middot; Report reference {e(audit.audit_ref)}<br>
This report is issued for the internal use of management and the audit committee. It reflects the
control environment observed during the audit period and does not constitute a guarantee that all
weaknesses have been identified. Distribution outside the organisation requires the approval of the
Senior Information Risk Owner.
</div></div>""")

    out_path = Path(out_path)
    out_path.write_text("\n".join(p), encoding="utf-8")
    return out_path


def _md(text) -> str:
    """Escape pipes and newlines so free text survives inside a Markdown table cell."""
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(audit: Audit, out_path: str | Path) -> Path:
    """The same report as Markdown, for viewing anywhere that renders it (e.g. GitHub)."""
    o = audit.overall()
    fw = audit.framework
    findings = audit.findings()
    overdue_ids = {r["check"]["id"] for r in audit.overdue_actions()}
    report_date = audit.report_date or date.today().isoformat()
    score = f"{o['score']}%" if o["score"] is not None else "n/a"

    m: list[str] = []
    m.append(f"# IT & Information Security Audit — {audit.entity}\n")
    m.append(f"*{fw['framework_name']} v{fw['version']} · Reference {audit.audit_ref}*\n")
    m.append("> **Internal audit report — confidential.** This is a worked example against a "
             "fictional auditee, produced by [`audit.py`](../audit.py) to show the tool's output.\n")

    m.append("| | |\n|---|---|")
    for label, value in [("Auditee / site", audit.site), ("Report date", report_date),
                         ("Lead auditor", audit.lead_auditor),
                         ("Audit period", f"{audit.period_start} to {audit.period_end}"),
                         ("Controls in programme", o["total"]),
                         ("Controls tested", o["tested"])]:
        m.append(f"| **{label}** | {_md(value)} |")

    # --- executive summary ---
    c = o["counts"]
    sev = o["findings_by_severity"]
    m.append("\n## 1. Executive Summary\n")
    m.append("| Compliance score | Findings raised | Critical / High | Risk exposure |")
    m.append("|---|---|---|---|")
    m.append(f"| **{score}** ({o['rating']} assurance) | **{len(findings)}** "
             f"({c['non_compliant']} failed, {c['partial']} partial) | "
             f"**{sev['critical']} / {sev['high']}** | **{o['risk']}** weighted |")
    m.append(f"\n**Audit opinion.** {o['opinion']}\n")

    if findings:
        m.append("### Key matters for management attention\n")
        for n, row in enumerate(findings[:5], 1):
            m.append(f"{n}. **{row['check']['id']} — "
                     f"{row['check']['title']}.** {_md(row['result'].observation)}")
        m.append("")

    # --- scope ---
    m.append("## 2. Scope, Objective & Methodology\n")
    m.append(f"{fw.get('scope_statement','')}\n")
    if audit.scope_notes:
        m.append(f"{audit.scope_notes}\n")
    m.append("Testing was performed through enquiry of responsible officers, observation of "
             "processes in operation, inspection of system configuration and documentary "
             "evidence, and re-performance of selected control activities on a sample basis. "
             "Controls were assessed against:\n")
    for f in fw.get("primary_frameworks", []):
        m.append(f"- {f}")
    m.append("\nEach control is rated **Compliant**, **Partially compliant**, **Non-compliant** "
             "or **Not applicable**. The compliance score is (compliant + 0.5 × partial) ÷ "
             "controls assessed. Findings take the severity of the underlying control where it "
             "was absent, and one level below where it exists but operates with gaps. "
             "Remediation deadlines follow finding severity: "
             + ", ".join(f"{k} {v} days" for k, v in fw.get("severity_sla_days", {}).items())
             + ".\n")

    # --- domain results ---
    m.append("## 3. Results by Control Domain\n")
    m.append("| Ref | Control domain | Tested | Pass | Partial | Fail | Score | Assurance |")
    m.append("|---|---|---|---|---|---|---|---|")
    for section in fw["sections"]:
        s = audit.section_stats(section)
        sc = f"{s['score']}%" if s["score"] is not None else "–"
        m.append(f"| **{s['id']}** | {_md(s['title'])} | {s['assessed']}/{s['total']} | "
                 f"{s['counts']['compliant']} | {s['counts']['partial']} | "
                 f"{s['counts']['non_compliant']} | {sc} | {s['rating']} |")

    # --- findings ---
    m.append("\n## 4. Findings & Recommendations\n")
    if not findings:
        m.append("No exceptions were identified in the controls tested.\n")
    for i, row in enumerate(findings, 1):
        check, res, section = row["check"], row["result"], row["section"]
        due = res.due_date + (" — **OVERDUE**" if check["id"] in overdue_ids else "")
        m.append(f"### Finding {i:02d} · {check['id']} — {check['title']}\n")
        m.append(f"`{row['severity'].upper()}` · **{STATUSES[res.status]}** · "
                 f"{section['id']} – {section['title']}\n")
        m.append("| | |\n|---|---|")
        rows = [("Control objective", check["control_objective"]),
                ("Test performed", check["test_procedure"]),
                ("Sample", res.sample_size), ("Observation", res.observation),
                ("Root cause", res.root_cause), ("Risk / impact", res.risk_statement),
                ("Recommendation", res.corrective_action),
                ("Management response", res.management_response),
                ("Owner", res.action_owner), ("Target date", due),
                ("Evidence ref", res.evidence_ref)]
        for label, value in rows:
            if str(value or "").strip():
                m.append(f"| **{label}** | {_md(value)} |")
        maps = " · ".join(f"{k}: `{v}`" for k, v in check.get("mappings", {}).items() if v)
        if maps:
            m.append(f"\n<sub>{maps}</sub>\n")

    # --- action plan ---
    m.append("## 5. Corrective Action Plan\n")
    if findings:
        m.append("| Ref | Severity | Agreed action | Owner | Target date |")
        m.append("|---|---|---|---|---|")
        for row in findings:
            check, res = row["check"], row["result"]
            due = res.due_date + (" ⚠" if check["id"] in overdue_ids else "")
            m.append(f"| **{check['id']}** | {row['severity']} | {_md(res.corrective_action)} | "
                     f"{_md(res.action_owner)} | {due} |")
    else:
        m.append("No corrective actions arising.\n")

    # --- appendix ---
    m.append("\n## Appendix A – Detailed Control Test Log\n")
    m.append("| Ref | Control | Control severity | Result | Evidence ref |")
    m.append("|---|---|---|---|---|")
    for section in fw["sections"]:
        m.append(f"| | **{section['id']} – {_md(section['title'])}** | | | |")
        for check in section["checks"]:
            res = audit.results.get(check["id"])
            status = res.status if res else "not_tested"
            m.append(f"| {check['id']} | {_md(check['title'])} | "
                     f"{check.get('severity','medium')} | {STATUSES[status]} | "
                     f"{_md(res.evidence_ref) if res else ''} |")

    m.append(f"\n---\n\n<sub>Prepared by {_md(audit.lead_auditor)} · {_md(audit.entity)} · "
             f"Report reference {audit.audit_ref}. This report is issued for the internal use of "
             "management and the audit committee. It reflects the control environment observed "
             "during the audit period and does not constitute a guarantee that all weaknesses "
             "have been identified.</sub>\n")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(m), encoding="utf-8")
    return out_path


def export_capa_csv(audit: Audit, out_path: str | Path) -> Path:
    """Action plan as CSV, for import into a GRC or issue tracker."""
    out_path = Path(out_path)
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Audit ref", "Finding ref", "Domain", "Control", "Finding severity", "Status",
                    "Observation", "Root cause", "Risk", "Agreed action", "Owner",
                    "Target date", "Management response", "Evidence ref",
                    "ISO 27001", "DSPT"])
        for row in audit.findings():
            c, r, s = row["check"], row["result"], row["section"]
            m = c.get("mappings", {})
            w.writerow([audit.audit_ref, c["id"], s["title"], c["title"],
                        row["severity"], STATUSES[r.status], r.observation, r.root_cause,
                        r.risk_statement, r.corrective_action, r.action_owner, r.due_date,
                        r.management_response, r.evidence_ref,
                        m.get("iso27001", ""), m.get("dspt", "")])
    return out_path
