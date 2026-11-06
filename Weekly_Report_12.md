# WEEKLY REPORT 12

**Project Title:** AI-Powered Business Intelligence Platform  
**Student IDs:** 23DCS110, 23DCS106  
**Semester:** 7th

**From Date:** 29/09/2026  
**To Date:** 05/10/2026

## Work done from 29/09/2026 to 05/10/2026

- Implemented the public, read-only shared-dashboard response with the dataset title, KPI values, saved insights, and aggregate chart data.
- Added expiring share-token access and limited public chart responses to approved aggregate chart types.
- Required authentication in production-like environments and attached bearer tokens to protected frontend API requests.
- Checked production-mode account access: unauthenticated requests were rejected, while sign-up, sign-in, profile access, and authenticated session access worked.
- Improved handling of empty AI-generated SQL responses by retrying and returning a clear error when no query was produced; retained the read-only `SELECT` validation.
- Recorded 65 passing backend tests. Frontend type validation and the Vercel-targeted production build were also recorded as successful.

## Plans for next week: 06/10/2026 to 12/10/2026

- Add session-ownership checks to protected data routes and associate each new upload session with its signed-in owner.
- Filter session history and session-level access according to ownership.
- Add KPI confidence context and a percentage-based what-if calculation endpoint.
- Add focused test coverage for session ownership, empty AI responses, KPI confidence, and scenario calculations.
- Preserve the read-only `SELECT` validation in the AI query flow while making these changes.

## References

- FastAPI Documentation — https://fastapi.tiangolo.com/
- PostgreSQL Documentation — https://www.postgresql.org/docs/
- React Documentation — https://react.dev/
- Vite Documentation — https://vite.dev/guide/
- SQLAlchemy Documentation — https://docs.sqlalchemy.org/
- Plotly JavaScript Documentation — https://plotly.com/javascript/

**Signature of Student:** ____________________  
**Signature of Mentor:** ____________________
