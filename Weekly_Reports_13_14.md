# Weekly Reports 13–14

## WEEKLY REPORT 13

**Project Title:** AI-Powered Business Intelligence Platform  
**Student IDs:** 23DCS110, 23DCS106  
**Semester:** 7th

**From Date:** 06/10/2026  
**To Date:** 12/10/2026

**Work done from 06/10/2026 to 12/10/2026**

- Added ownership checks to protected session routes and associated new uploads with the signed-in user.
- Filtered dataset-history results and session access according to account ownership.
- Added a KPI confidence heuristic and a backend what-if endpoint for percentage-based KPI projections.
- Added targeted test coverage for session ownership, empty AI responses, KPI confidence, and scenario calculations; no pass count is claimed for these newly added cases.
- Retained the AI query guard that accepts only a validated, read-only `SELECT` statement.

**Plans for next week: 13/10/2026 to 19/10/2026**

- Define the purpose and scope of a more project-specific feature, using traceable KPI and dataset evidence.
- Review the upload, schema inspection, dashboard, AI chat, PDF, authentication, and sharing workflows.
- Recheck invalid/expired share-link behavior and the consistency of saved data-quality summaries.
- Select sanitized screenshots and continue preparing the final project report.

**References**

- FastAPI Documentation — https://fastapi.tiangolo.com/
- PostgreSQL Documentation — https://www.postgresql.org/docs/
- React Documentation — https://react.dev/
- SQLAlchemy Documentation — https://docs.sqlalchemy.org/
- Plotly JavaScript Documentation — https://plotly.com/javascript/

**Signature of Student:** ____________________  
**Signature of Mentor:** ____________________

---

## WEEKLY REPORT 14

**Project Title:** AI-Powered Business Intelligence Platform  
**Student IDs:** 23DCS110, 23DCS106  
**Semester:** 7th

**From Date:** 13/10/2026  
**To Date:** 19/10/2026

**Work done from 13/10/2026 to 19/10/2026**

- Reviewed possible enhancements to the AI-Powered Business Intelligence Platform and selected two focused features for the next development phase.
- Defined the scope of a What-If KPI panel that will use the existing scenario calculation support to show baseline and projected KPI values after a percentage adjustment. Projected values will be identified as estimates.
- Defined the scope of a per-session Data Quality Alerts panel that will present existing upload notifications and flagged outlier alerts for the selected dataset.

**Plans for next week: 20/10/2026 to 26/10/2026**

- Implement the What-If KPI panel using the existing scenario calculation support, with percentage adjustments, baseline-versus-projected KPI values, and a clear estimate label.
- Implement a per-session Data Quality Alerts panel using existing upload notifications and flagged outlier alerts.
- Resume regression checks for upload, dashboard, AI chat, PDF reporting, authentication, and sharing.
- Compare data-quality values across profiling, stored metadata, Data X-Ray, and PDF output.
- Finalize report screenshots and request an Internal Guide review of the report content.

**References**

- FastAPI Documentation — https://fastapi.tiangolo.com/
- PostgreSQL Documentation — https://www.postgresql.org/docs/
- React Documentation — https://react.dev/
- SQLAlchemy Documentation — https://docs.sqlalchemy.org/
- Plotly JavaScript Documentation — https://plotly.com/javascript/

**Signature of Student:** ____________________  
**Signature of Mentor:** ____________________

