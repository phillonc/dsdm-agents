# Change Log — Customer Feedback Portal

_Maintained by the `change-control` agent · `/run-change-request`_

Every entry records a trade-off, never a bare addition — see
`.github/agents/change-control.agent.md`.

---

## CR-001 — Combined CSV+PDF export

**Raised by:** VP Customer Success (exec ask, mid-Timebox 3)
**Requested priority:** Must Have
**Current state:** "Export to CSV" is a Should-Have (#8 in `PRODUCT_REQUIREMENTS.md`)

### Classification
Re-scope of an existing Should-Have item (CSV export → CSV **and** PDF
export), requested at a higher priority than it currently holds.

### Trade-off proposed
Add "Combined CSV+PDF export" at **Should Have** (not Must — Timebox 3 is
already at capacity and no existing Must-Have has spare room to trade
against) **by deferring** "Public roadmap board" (Could-Have #11) to a
future release. PDF generation reuses the existing CSV query path plus a
templating library (`pdfkit`), so it is scoped as an extension of #8 rather
than a net-new Must-Have.

### Escalation
Elevating this to a **Must Have**, as requested, would require displacing
an existing Must-Have (none of the 6 have spare capacity this close to
MVP). Per the change-control agent's stop condition, this was flagged back
to the Product Owner rather than resolved unilaterally.

**Decision:** Product Owner accepted the Should-Have trade (PDF export
ships with CSV export in Phase 1; roadmap board moves to "Future"). Logged
2026-07-24.

### Updated MoSCoW counts
Must: 6 (unchanged) · Should: 3 (CSV export → CSV+PDF export) · Could: 1
(-1, roadmap board moved to Future) · Won't: 2 (unchanged)

### Risk log impact
None — no new risk introduced; `pdfkit` is a well-established, actively
maintained library.

### Sync
`jira_update_issue` on the CSV-export story (scope note added);
`jira_add_comment` linking this change-log entry; Confluence status log
updated via `sync_work_item_status`.

---

_To raise a new request, run `/run-change-request` with the project slug,
change description, requested priority, and source._
