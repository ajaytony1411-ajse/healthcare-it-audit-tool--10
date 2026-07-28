"""A fully worked example engagement, used by `python audit.py demo`.

Fictional auditee. The findings are written the way a real IT audit file reads:
observation, root cause, risk, recommendation, owner, date.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from engine import Audit

TODAY = date.today()


def d(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


# Controls where testing identified an exception.
# check_id: (status, observation, root_cause, risk, recommendation, owner, due, sample)
FINDINGS = {
    "IAM-01": (
        "non_compliant",
        "20 leavers were sampled against HR termination records. 7 accounts (35%) remained "
        "enabled after the leave date, the longest for 94 days. Two of these accounts were "
        "used to authenticate to the EHR after the individual had left the organisation.",
        "Leaver notification is a manual email from HR to the service desk with no ticket "
        "raised, no SLA and no reconciliation between HR records and Active Directory.",
        "Active credentials held by former staff allow unauthorised access to special category "
        "health data. Post-termination logons already evidenced constitute a reportable "
        "personal data breach exposure under UK GDPR Art. 33.",
        "Automate leaver de-provisioning from the HR system to Active Directory. As an interim "
        "control, implement a monthly reconciliation of the HR leaver report against enabled "
        "accounts, with exceptions reported to the IG committee. Investigate the two "
        "post-termination logons as potential incidents.",
        "Head of IT Operations / HR Director",
        d(7),
        "20 of 143 leavers",
    ),
    "IAM-02": (
        "partial",
        "31 accounts hold Domain Admin or equivalent privilege. 9 are shared or service "
        "accounts without a named owner, and 4 have not been used in over 180 days. Quarterly "
        "privileged access reviews were evidenced for Q1 and Q2 only; Q3 and Q4 were not "
        "performed.",
        "No privileged access management tooling; reviews depend on the availability of a "
        "single infrastructure engineer with no deputy.",
        "Excessive and unattributable administrative access increases the blast radius of a "
        "compromised credential and prevents attribution during investigation.",
        "Reduce privileged accounts to named individuals with a documented justification, "
        "disable dormant accounts, and place remaining service accounts under managed vault "
        "credentials. Reinstate quarterly review with a named deputy reviewer.",
        "Infrastructure Manager",
        d(30),
        "31 privileged accounts (full population)",
    ),
    "VUL-02": (
        "non_compliant",
        "Of 20 critical and high vulnerabilities sampled, 13 exceeded the 14-day remediation "
        "SLA. Mean time to remediate for critical vulnerabilities was 47 days. Three "
        "internet-facing systems carried unpatched vulnerabilities with known public exploits "
        "at the time of testing.",
        "Patching windows for clinical systems require clinical sign-off that is only sought "
        "monthly, and there is no emergency patching route for actively exploited "
        "vulnerabilities.",
        "Exploitation of known vulnerabilities on internet-facing infrastructure is the most "
        "common initial access vector in healthcare ransomware incidents. Failure also breaches "
        "Cyber Essentials certification conditions.",
        "Define and approve an emergency patching procedure for actively exploited "
        "vulnerabilities with a 72-hour target. Remediate the three internet-facing systems "
        "immediately. Report SLA compliance monthly to the IG committee.",
        "Head of IT Operations",
        d(7),
        "20 of 486 critical/high findings",
    ),
    "VUL-03": (
        "non_compliant",
        "14 Windows Server 2012 R2 hosts and 2 Windows 10 21H2 endpoints remain in service, "
        "including the radiology PACS gateway. No extended security updates are purchased and "
        "no risk acceptance has been formally approved.",
        "Replacement of the PACS gateway is dependent on a supplier upgrade that has been "
        "deferred twice; no compensating controls were implemented while the deferral ran.",
        "Unsupported platforms receive no security updates and cannot be brought into a "
        "defensible position. Compromise of the PACS gateway would disrupt diagnostic imaging "
        "and expose patient images.",
        "Produce a dated decommissioning plan for all end-of-life hosts. Where migration cannot "
        "complete within 90 days, isolate the hosts to a restricted VLAN with explicit allow "
        "rules and obtain formal risk acceptance from the SIRO.",
        "IT Director",
        d(30),
        "Full asset register (612 hosts)",
    ),
    "BCP-02": (
        "non_compliant",
        "No full restore test of the EHR has been performed since the platform migration 19 "
        "months ago. Testing is limited to individual file-level restores. The documented RTO "
        "of 4 hours has therefore never been validated.",
        "Restore testing requires an isolated recovery environment that has not been funded.",
        "In a ransomware scenario the organisation cannot demonstrate that clinical systems can "
        "be recovered within the stated RTO. Unvalidated backups are a recurring cause of "
        "extended clinical downtime.",
        "Perform a full restore test of the EHR and PACS to an isolated environment within 60 "
        "days, measure actual recovery time against RTO, and repeat at least annually. Report "
        "the result to the board.",
        "Infrastructure Manager",
        d(7),
        "Backup test records, 19 months",
    ),
    "NET-02": (
        "partial",
        "Medical device and corporate VLANs are separated, but ACL testing from the corporate "
        "segment reached 4 of 8 medical devices tested on management ports (SSH/HTTP). Guest "
        "Wi-Fi was correctly isolated. The network diagram was last updated 14 months ago and "
        "did not reflect two new VLANs.",
        "Segmentation was implemented at project level without an enforced inter-VLAN policy "
        "baseline, and no periodic validation testing takes place.",
        "Lateral movement from a compromised corporate endpoint to connected medical devices "
        "could affect device availability and, in some device classes, patient safety.",
        "Apply default-deny inter-VLAN policy with explicit allow rules for clinically required "
        "flows. Re-test segmentation after change and at least annually. Refresh the network "
        "diagram and place it under change control.",
        "Network Manager",
        d(30),
        "8 devices tested across 5 VLANs",
    ),
    "LOG-02": (
        "non_compliant",
        "The EHR records record-level access, but no proactive audit of inappropriate access "
        "has been performed in the audit period. No alerting exists for self-lookup, "
        "same-surname or VIP record access. A sample query run during fieldwork identified 3 "
        "instances of staff accessing their own record.",
        "Ownership of clinical record access auditing is not assigned; IG assumes IT performs "
        "it, IT assumes IG performs it.",
        "Inappropriate access to patient records goes undetected. This is a recurring theme in "
        "ICO enforcement against healthcare providers and undermines the confidentiality "
        "obligation under UK GDPR Art. 5(1)(f).",
        "Assign ownership of clinical audit review to the IG team. Implement monthly proactive "
        "audit covering self, same-surname and VIP access, with exceptions investigated under "
        "the disciplinary process. Review the 3 instances identified during fieldwork.",
        "Head of Information Governance",
        d(30),
        "12 months of EHR audit data",
    ),
    "TPR-03": (
        "partial",
        "21 third-party support accounts were identified. 6 lack MFA, 11 have no expiry date "
        "set, and per-session approval is not required for 4 suppliers who hold standing "
        "access. Session logging is in place for all accounts.",
        "Supplier access is provisioned ad hoc at contract start with no standard control "
        "baseline and no periodic review.",
        "Standing, unattributed supplier access is a well-documented initial access route in "
        "healthcare supply chain incidents and limits the ability to attribute activity.",
        "Apply a supplier access standard: MFA mandatory, accounts disabled by default and "
        "enabled per approved session, maximum 12-month expiry, quarterly review by the "
        "contract owner.",
        "Head of IT Operations",
        d(30),
        "21 third-party accounts (full population)",
    ),
    "AWR-01": (
        "partial",
        "Annual data security training completion was 87% against the 95% DSPT threshold. "
        "Completion among medical staff was 71% and among board members 60%. Non-completion is "
        "not escalated to line managers.",
        "Training is assigned via the LMS but completion is not linked to appraisal or to "
        "system access, and no escalation route exists.",
        "The organisation does not meet the DSPT training standard, which affects the toolkit "
        "submission. Untrained staff are materially more likely to fall to phishing.",
        "Escalate non-completion to line managers at 30 days and to executive leads at 60 days. "
        "Link completion to the appraisal process. Report completion rates by staff group "
        "monthly to the IG committee.",
        "Head of Information Governance / L&D",
        d(60),
        "LMS report, 1,240 staff",
    ),
    "RSK-02": (
        "partial",
        "Four new systems processing patient data were deployed in the period. DPIAs exist for "
        "three; the patient messaging platform went live without one and the DPIA was completed "
        "retrospectively 5 months after go-live. Two DPIAs lack evidence of DPO review.",
        "The DPIA trigger sits in the IG process but is not a mandatory gate in the project or "
        "procurement lifecycle, so it can be bypassed.",
        "Deploying high-risk processing without a prior DPIA is a direct breach of UK GDPR Art. "
        "35 and removes the opportunity to design in mitigations before go-live.",
        "Make DPIA completion and DPO sign-off a mandatory stage gate in the project and "
        "procurement lifecycle, with the CAB unable to approve go-live without it.",
        "Data Protection Officer",
        d(60),
        "4 systems deployed in period",
    ),
    "CHG-03": (
        "non_compliant",
        "The UAT instance of the EHR contains a full copy of live patient data refreshed "
        "monthly, including names, NHS numbers and clinical notes. 34 users have access to UAT, "
        "of whom 9 have no clinical role. No masking process exists and no approval for the use "
        "of live data was found.",
        "The test refresh process was inherited from the previous supplier's implementation and "
        "has never been reviewed against data protection requirements.",
        "Patient data is processed in an environment with weaker access control and no clinical "
        "justification, contrary to the purpose limitation and security principles. A "
        "compromise of UAT would be a reportable breach of the full patient record.",
        "Implement pseudonymisation on refresh to non-production, or restrict UAT access to the "
        "same population as production pending that capability. Document and approve the "
        "process through the DPO.",
        "EHR System Owner / DPO",
        d(7),
        "UAT database sampling, 34 users",
    ),
    "PHY-01": (
        "partial",
        "The comms room access list holds 23 people, of whom 5 have left the organisation or "
        "changed role. The last documented access review was 16 months ago. Access logs are "
        "retained but not reviewed.",
        "The access list is owned by Facilities and is not linked to the leaver process or the "
        "IT access review cycle.",
        "Unauthorised physical access to network infrastructure bypasses logical controls "
        "entirely and would not be detected.",
        "Remove the 5 invalid holders immediately. Bring comms room access into the six-monthly "
        "access review cycle and the leaver checklist.",
        "Facilities Manager / Infrastructure Manager",
        d(30),
        "23 badge holders (full population)",
    ),
    "END-04": (
        "partial",
        "The medical device inventory holds 218 networked devices but is not reconciled to "
        "network discovery, which identified 27 further devices. Of 8 devices sampled, 3 ran "
        "unsupported operating systems and 2 retained default administrative credentials.",
        "Medical devices are procured by clinical departments without IT involvement, so they "
        "do not enter the IT asset or vulnerability management processes.",
        "Unmanaged connected devices with default credentials provide a persistent foothold on "
        "the clinical network and, for some device classes, present a patient safety risk.",
        "Include IT security sign-off as a mandatory step in medical device procurement. "
        "Reconcile the inventory to discovery quarterly. Change default credentials on the "
        "devices identified and obtain manufacturer patch positions for unsupported devices.",
        "Head of Medical Physics / IT Security Manager",
        d(60),
        "8 of 218 registered devices",
    ),
    "DPR-03": (
        "partial",
        "Of 10 subject access requests sampled, 8 were completed within one calendar month, 1 "
        "took 47 days with no extension notified, and 1 remained open at 62 days. Identity "
        "verification was evidenced in all cases.",
        "SAR handling rests with a single IG officer with no cover during absence, and no "
        "escalation triggers when a request approaches 21 days.",
        "Late responses without a notified extension breach UK GDPR Art. 12(3) and are a common "
        "trigger for ICO complaints.",
        "Introduce automated escalation at day 21, cross-train a second officer, and report "
        "open SAR aging to the IG committee monthly.",
        "Head of Information Governance",
        d(60),
        "10 of 63 SARs",
    ),
    "IRM-01": (
        "partial",
        "An incident response plan exists and was updated in the period. The last tabletop "
        "exercise was 22 months ago and did not cover a ransomware scenario. Four of six "
        "lessons learned from that exercise remain open.",
        "Exercising is not scheduled in the assurance calendar and competes with operational "
        "priorities.",
        "An untested plan and unclosed lessons reduce the effectiveness of response at the point "
        "of a real incident, extending clinical downtime.",
        "Run a ransomware tabletop covering clinical downtime and board communications within 90 "
        "days, involving clinical leadership. Close the four outstanding actions and schedule "
        "exercising annually in the assurance calendar.",
        "IT Security Manager",
        d(60),
        "IR plan and exercise records",
    ),
    "ISG-04": (
        "partial",
        "The asset register records 612 hosts against 671 identified by network discovery, a "
        "variance of 8.8%. 43 entries have no named owner and criticality ratings are absent "
        "for all non-server assets.",
        "The register is maintained manually in a spreadsheet and updated only at procurement, "
        "not at decommission or discovery.",
        "Assets outside the register are outside patching, monitoring and backup scope, and "
        "cannot be protected or recovered.",
        "Move the register to the endpoint management platform as the source of truth, with "
        "monthly automated reconciliation against discovery and exception reporting.",
        "IT Asset Manager",
        d(60),
        "Full register vs discovery scan",
    ),
    "LOG-04": (
        "partial",
        "Of 8 systems sampled, 2 network appliances synchronise to an external NTP source rather "
        "than the internal authoritative source, with observed drift of up to 4 minutes.",
        "Appliance builds were not covered by the standard NTP configuration baseline.",
        "Inconsistent timestamps complicate correlation of events across systems during "
        "investigation and can undermine evidential reliability.",
        "Add NTP source to the network device build standard and correct the two appliances.",
        "Network Manager",
        d(90),
        "8 systems sampled",
    ),
    # Carried forward from the prior year's audit and still open - demonstrates
    # overdue tracking in the report.
    "TPR-01": (
        "partial",
        "Of 10 suppliers processing patient data, 8 hold Art. 28 compliant contracts. 2 operate "
        "under purchase-order terms only with no data processing clauses, one of which hosts "
        "patient-facing appointment data. This finding was raised in the prior year audit and "
        "remains open.",
        "Contract remediation was assigned to procurement but no completion date was tracked "
        "after the original owner left the organisation.",
        "Without Art. 28 terms the organisation cannot demonstrate that processors are bound to "
        "appropriate security, sub-processor and breach notification obligations, and remains "
        "liable as controller.",
        "Execute data processing agreements with both suppliers or cease the processing. "
        "Reassign ownership of the prior-year action and report closure to the audit committee.",
        "Head of Procurement / DPO",
        (TODAY - timedelta(days=41)).isoformat(),
        "10 of 84 suppliers",
    ),
}

NOT_APPLICABLE = {
    "RSK-04": "The organisation is an independent provider and is not required to submit the "
              "DSPT; the equivalent assurance is provided through ISO 27001 certification, "
              "which was verified as current. Cyber Essentials Plus and ICO registration were "
              "confirmed in date.",
}

# Scope limitation - agreed with management, reported as untested.
NOT_TESTED = {"IRM-04"}


def build_demo(checklist_path: Path) -> Audit:
    audit = Audit.from_checklist(
        checklist_path,
        entity="Northgate Health Group",
        site="Head office, 3 clinical sites and hosted data centre",
        lead_auditor="A. Tony, Lead IT Auditor",
        period_start=(TODAY.replace(day=1) - timedelta(days=365)).isoformat(),
        period_end=TODAY.isoformat(),
        scope_notes=(
            "Fieldwork covered central IT infrastructure, the electronic health record, PACS, "
            "the practice management system and supporting cloud services. Clinical practice, "
            "medical device efficacy and financial controls were outside scope. Forensic "
            "readiness testing (IRM-04) was deferred at management request and will be covered "
            "in the next cycle; this constitutes a scope limitation."
        ),
    )
    audit.report_date = TODAY.isoformat()
    audit.watermark = "WORKED EXAMPLE · AJAY TONY"
    audit.notice = (
        "WORKED EXAMPLE — NOT A REAL AUDIT. Northgate Health Group is a fictional "
        "organisation and every finding below is illustrative. This report was generated by "
        "the open-source healthcare IT audit tool at "
        "github.com/ajaytony1411-ajse/healthcare-it-audit-tool--10 to demonstrate its output. "
        "It contains no real patient data and describes no real organisation's security posture."
    )

    for check in audit.all_checks():
        cid = check["id"]
        if cid in NOT_TESTED:
            continue
        if cid in NOT_APPLICABLE:
            audit.record(cid, "not_applicable", observation=NOT_APPLICABLE[cid],
                         evidence_ref=f"WP-{cid}")
            continue
        if cid in FINDINGS:
            status, obs, cause, risk, action, owner, due, sample = FINDINGS[cid]
            audit.record(
                cid, status, observation=obs, root_cause=cause, risk_statement=risk,
                corrective_action=action, action_owner=owner, due_date=due,
                sample_size=sample, evidence_ref=f"WP-{cid}",
                management_response="Accepted." if status == "non_compliant" else
                                    "Accepted, timescale agreed with management.",
            )
            continue
        audit.record(cid, "compliant",
                     observation="Control tested and found to be operating effectively; no "
                                 "exceptions identified in the sample.",
                     evidence_ref=f"WP-{cid}")
    return audit
