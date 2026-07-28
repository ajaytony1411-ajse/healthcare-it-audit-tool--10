# Healthcare IT & Information Security Audit Tool

A checklist-driven IT audit tool for healthcare providers. You work through a control
programme, record what you tested and what you found, and it produces an audit report
with a compliance score, a findings register and a corrective action plan.

Built around UK healthcare IT assurance: **ISO/IEC 27001:2022**, **NHS DSPT**,
**Cyber Essentials**, **UK GDPR / DPA 2018**, with **HIPAA Security Rule** cross-references
for US-linked entities. Every control carries its framework mappings, so a finding can be
traced straight back to the clause it breaches.

No dependencies — Python 3.10+ standard library only.

### 🔗 [View the live example report →](https://ajaytony1411-ajse.github.io/healthcare-it-audit-tool--10/)

The full styled report as the tool produces it. Same thing as
[Markdown](docs/EXAMPLE_REPORT.md) if you'd rather stay in the repo.

A complete engagement against a fictional auditee: 58 controls tested, 18 findings, scored
by domain, with a full corrective action plan. That is the tool's actual output, not a mockup.

## Quick look

Generate a fully worked example engagement (fictional auditee, 58 controls, 18 findings):

```bash
python audit.py demo
```

That writes `demo_audit_report.html`, `demo_audit_action_plan.csv` and the working file
`demo_audit.json`, and opens the report in your browser.

## Running a real audit

**1. Open the engagement**

```bash
python audit.py new --auditor "A. Tony" --start 2025-07-01 --end 2026-06-30
```

Prompts for anything you don't pass on the command line, then writes a working file
(`audit_ITA-YYYYMM-XXXX.json`) holding the programme and your results.

**2. Fieldwork**

```bash
python audit.py fieldwork audit_ITA-202607-A1B2.json
```

Walks you control by control, showing the objective, the test procedure and the evidence
you should be asking for. For each one:

- `c` compliant · `p` partial · `n` non-compliant · `x` n/a · `s` skip · `q` save and quit

Where you record an exception it asks for sample size, observation, root cause, risk,
recommendation, owner and target date. It saves after every control, so you can stop and
resume across days. Re-running only shows untested controls; add `--all` to revisit.

**3. Check progress at any point**

```bash
python audit.py status audit_ITA-202607-A1B2.json
```

**4. Issue the report**

```bash
python audit.py report audit_ITA-202607-A1B2.json
```

Produces a self-contained HTML report (print or save to PDF from the browser — it flattens
to a light, ink-friendly layout when printed) plus a CSV action plan for import into a GRC
platform or issue tracker. Add `--markdown` for a Markdown copy as well, which is handy for
pasting into a ticket, a wiki or a pull request.

## How it scores

**Compliance score** = (compliant + 0.5 × partial) ÷ controls assessed. Controls marked
not applicable are excluded from the denominator, so scope decisions don't distort the result.

**Assurance rating** — ≥95% Substantial · ≥80% Reasonable · ≥60% Limited · below that,
No assurance. The overall opinion is floored at Limited where any critical finding exists,
regardless of score, so a good average can't bury a serious failure.

**Finding severity** takes the control's severity where the control is absent or ineffective,
and drops one level where the control exists but operates with gaps. Auditor judgement
overrides both. Target dates default from severity: critical 7 days, high 30, medium 60,
low 90. Actions past their date are flagged as overdue in the report and in `status`.

**Risk exposure** is a weighted count of open findings (critical 10, high 6, medium 3, low 1)
— useful for tracking direction of travel between audits rather than as an absolute figure.

## The control programme

`checklists/healthcare_it_grc.json` — 58 controls across 14 domains:

| | Domain | | Domain |
|---|---|---|---|
| ISG | Information security governance & policy | CHG | Change & development management |
| RSK | Risk management & compliance assurance | LOG | Logging, monitoring & detection |
| IAM | Identity & access management | BCP | Backup, resilience & disaster recovery |
| DPR | Data protection & privacy | TPR | Third party & supplier assurance |
| NET | Network & infrastructure security | IRM | Incident response & breach notification |
| END | Endpoint, mobile & connected medical device security | PHY | Physical & environmental security |
| VUL | Vulnerability & patch management | AWR | People, training & security culture |

Each control specifies a control objective, a test procedure with sample guidance, the
evidence to request, a severity, and its framework mappings.

## Using a different programme

The checklist is plain JSON — copy it, edit it, and point at it:

```bash
python audit.py new --checklist checklists/my_programme.json
```

Structure:

```json
{
  "framework_name": "...", "version": "1.0",
  "scope_statement": "...", "primary_frameworks": ["..."],
  "severity_sla_days": {"critical": 7, "high": 30, "medium": 60, "low": 90},
  "sections": [{
    "id": "ISG", "title": "...", "objective": "...",
    "checks": [{
      "id": "ISG-01", "title": "...",
      "control_objective": "what good looks like",
      "test_procedure": "how the auditor tests it",
      "evidence_expected": ["..."],
      "severity": "critical|high|medium|low",
      "mappings": {"iso27001": "A.5.2", "dspt": "1.3"}
    }]
  }]
}
```

Nothing in the code is healthcare-specific — the same engine runs a SOX ITGC programme,
a PCI DSS assessment or a supplier audit if you swap the JSON.

## Files

| File | |
|---|---|
| `audit.py` | CLI — `new`, `fieldwork`, `status`, `report`, `demo` |
| `engine.py` | Audit model, scoring, severity and SLA logic |
| `report.py` | HTML, Markdown and CSV rendering |
| `demo_data.py` | The worked example engagement |
| `checklists/healthcare_it_grc.json` | The control programme |
| `docs/EXAMPLE_REPORT.md` | The worked example, rendered |

## Note

The findings in the demo are illustrative and the auditee is fictional. The control
programme is a starting point for a real engagement, not a substitute for scoping the audit
against the organisation in front of you.

Live audit working files (`audit_*.json`) and issued reports are gitignored — they hold real
auditee findings and should never reach a repository.

## Licence

MIT — see [LICENSE](LICENSE).
