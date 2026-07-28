"""Core audit model: loading checklists, recording test results, scoring."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

# Result of testing a single control.
STATUSES = {
    "compliant": "Compliant",
    "partial": "Partially compliant",
    "non_compliant": "Non-compliant",
    "not_applicable": "Not applicable",
    "not_tested": "Not yet tested",
}

# Weight applied to an unmet control when calculating risk exposure.
SEVERITY_WEIGHT = {"critical": 10, "high": 6, "medium": 3, "low": 1}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# A control rated critical that is partially met is a lesser exposure than one
# that is absent entirely, so partial findings are rated one level down unless
# the auditor overrides it.
DOWNGRADE = {"critical": "high", "high": "medium", "medium": "low", "low": "low"}

DEFAULT_SLA_DAYS = {"critical": 7, "high": 30, "medium": 60, "low": 90}


class AuditError(Exception):
    pass


@dataclass
class Result:
    """The auditor's conclusion on one control."""

    check_id: str
    status: str = "not_tested"
    observation: str = ""          # what was actually found
    evidence_ref: str = ""         # working paper / document reference
    sample_size: str = ""          # e.g. "20 of 143 leavers"
    severity_override: str = ""    # auditor's rating of this finding, if not the default
    root_cause: str = ""
    risk_statement: str = ""       # business impact if left unaddressed
    corrective_action: str = ""
    action_owner: str = ""
    due_date: str = ""
    management_response: str = ""
    tested_on: str = ""

    def is_finding(self) -> bool:
        return self.status in ("non_compliant", "partial")


@dataclass
class Audit:
    """A single audit engagement against one checklist."""

    entity: str
    site: str
    lead_auditor: str
    period_start: str
    period_end: str
    framework: dict
    audit_ref: str = field(default_factory=lambda: f"ITA-{datetime.now():%Y%m}-{uuid.uuid4().hex[:4].upper()}")
    opened_on: str = field(default_factory=lambda: date.today().isoformat())
    report_date: str = ""
    scope_notes: str = ""
    notice: str = ""      # banner shown at the head of the report, e.g. a demo disclaimer
    results: dict = field(default_factory=dict)   # check_id -> Result

    # ---------- construction / persistence ----------

    @classmethod
    def from_checklist(cls, checklist_path: str | Path, **kwargs) -> "Audit":
        framework = json.loads(Path(checklist_path).read_text(encoding="utf-8"))
        audit = cls(framework=framework, **kwargs)
        for check in audit.all_checks():
            audit.results[check["id"]] = Result(check_id=check["id"])
        return audit

    @classmethod
    def load(cls, path: str | Path) -> "Audit":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        results = {k: Result(**v) for k, v in raw.pop("results", {}).items()}
        return cls(results=results, **raw)

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        payload = asdict(self)
        payload["results"] = {k: asdict(v) for k, v in self.results.items()}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    # ---------- navigation ----------

    def all_checks(self):
        for section in self.framework["sections"]:
            for check in section["checks"]:
                yield check

    def check(self, check_id: str) -> dict:
        for c in self.all_checks():
            if c["id"] == check_id:
                return c
        raise AuditError(f"Unknown check: {check_id}")

    def finding_severity(self, check_id: str) -> str:
        """Severity of the exception raised, which may differ from the control's rating."""
        result = self.results.get(check_id)
        if result and result.severity_override:
            return result.severity_override
        control_severity = self.check(check_id).get("severity", "medium")
        if result and result.status == "partial":
            return DOWNGRADE.get(control_severity, control_severity)
        return control_severity

    def sla_days(self, severity: str) -> int:
        return self.framework.get("severity_sla_days", DEFAULT_SLA_DAYS).get(
            severity, DEFAULT_SLA_DAYS.get(severity, 30)
        )

    # ---------- recording ----------

    def record(self, check_id: str, status: str, **fields) -> Result:
        if status not in STATUSES:
            raise AuditError(f"Invalid status '{status}'. Expected one of: {', '.join(STATUSES)}")
        if fields.get("severity_override") and fields["severity_override"] not in SEVERITY_WEIGHT:
            raise AuditError(f"Invalid severity '{fields['severity_override']}'. "
                             f"Expected one of: {', '.join(SEVERITY_WEIGHT)}")
        result = self.results.setdefault(check_id, Result(check_id=check_id))
        result.status = status
        for key, value in fields.items():
            if not hasattr(result, key):
                raise AuditError(f"Unknown result field: {key}")
            if value is not None:
                setattr(result, key, value)
        result.tested_on = result.tested_on or date.today().isoformat()

        # Default the remediation deadline from severity if the auditor didn't set one.
        if result.is_finding() and not result.due_date:
            sla = self.sla_days(self.finding_severity(check_id))
            result.due_date = (date.today() + timedelta(days=sla)).isoformat()
        return result

    # ---------- scoring ----------

    def section_stats(self, section: dict) -> dict:
        counts = {k: 0 for k in STATUSES}
        risk = 0
        for check in section["checks"]:
            result = self.results.get(check["id"], Result(check_id=check["id"]))
            counts[result.status] += 1
            if result.is_finding():
                risk += SEVERITY_WEIGHT.get(self.finding_severity(check["id"]), 3)

        assessed = counts["compliant"] + counts["partial"] + counts["non_compliant"]
        score = None
        if assessed:
            score = round((counts["compliant"] + 0.5 * counts["partial"]) / assessed * 100, 1)
        return {
            "id": section["id"],
            "title": section["title"],
            "objective": section.get("objective", ""),
            "counts": counts,
            "assessed": assessed,
            "total": len(section["checks"]),
            "score": score,
            "risk": round(risk, 1),
            "rating": rating_for(score),
        }

    def overall(self) -> dict:
        counts = {k: 0 for k in STATUSES}
        risk = 0.0
        severity_breakdown = {s: 0 for s in SEVERITY_WEIGHT}
        for check in self.all_checks():
            result = self.results.get(check["id"], Result(check_id=check["id"]))
            counts[result.status] += 1
            if result.is_finding():
                severity = self.finding_severity(check["id"])
                risk += SEVERITY_WEIGHT.get(severity, 3)
                severity_breakdown[severity] += 1

        assessed = counts["compliant"] + counts["partial"] + counts["non_compliant"]
        score = round((counts["compliant"] + 0.5 * counts["partial"]) / assessed * 100, 1) if assessed else None
        total = sum(counts.values())
        return {
            "counts": counts,
            "assessed": assessed,
            "total": total,
            "tested": total - counts["not_tested"],
            "score": score,
            "risk": round(risk, 1),
            "rating": rating_for(score),
            "opinion": opinion_for(score, severity_breakdown),
            "findings_by_severity": severity_breakdown,
        }

    def findings(self) -> list[dict]:
        """Every failed or partially met control, worst first."""
        rows = []
        for section in self.framework["sections"]:
            for check in section["checks"]:
                result = self.results.get(check["id"])
                if result and result.is_finding():
                    rows.append({"check": check, "result": result, "section": section,
                                 "severity": self.finding_severity(check["id"])})
        rows.sort(key=lambda r: (
            SEVERITY_ORDER.get(r["severity"], 2),
            0 if r["result"].status == "non_compliant" else 1,
            r["check"]["id"],
        ))
        return rows

    def overdue_actions(self, as_of: date | None = None) -> list[dict]:
        as_of = as_of or date.today()
        out = []
        for row in self.findings():
            due = row["result"].due_date
            if due:
                try:
                    if date.fromisoformat(due) < as_of:
                        out.append(row)
                except ValueError:
                    pass
        return out


def rating_for(score: float | None) -> str:
    """Map a compliance percentage to an assurance rating."""
    if score is None:
        return "Not assessed"
    if score >= 95:
        return "Substantial"
    if score >= 80:
        return "Reasonable"
    if score >= 60:
        return "Limited"
    return "No assurance"


def opinion_for(score: float | None, severity_breakdown: dict) -> str:
    """Overall audit opinion, floored by the presence of critical failures."""
    if score is None:
        return "Fieldwork incomplete - no opinion issued."
    critical = severity_breakdown.get("critical", 0)
    high = severity_breakdown.get("high", 0)
    if critical:
        return (
            f"Limited assurance at best. {critical} finding(s) were rated critical; these "
            "expose patient data or clinical service continuity to material risk and require "
            "remediation ahead of the wider action plan."
        )
    if score >= 95 and not high:
        return "Substantial assurance. The control environment is designed and operating effectively."
    if score >= 80:
        return (
            "Reasonable assurance. The control framework is broadly sound, with weaknesses "
            "that should be addressed within the agreed timescales."
        )
    if score >= 60:
        return (
            "Limited assurance. Control weaknesses are sufficiently widespread that reliance "
            "cannot be placed on the environment without remediation."
        )
    return (
        "No assurance. Fundamental control failures were identified across multiple domains; "
        "immediate management attention and a remediation programme are required."
    )
