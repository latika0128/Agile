# PhonePe-style Mobile Payments App — Project Seed

This repository contains the seed README and project specification for implementing a PhonePe-style mobile payments application (backend + frontend + infra + CI/CD + Jira integration).

Use this document as the single source-of-truth to hand off to a development team, contractor, or automated agent.

---

## Project Summary

Create a secure, performant, and user-friendly mobile payments application (PhonePe-like) enabling users to register, authenticate, link bank accounts, transfer money via UPI, recharge mobile & pay bills, track history, receive notifications, and access customer support. Deliver a production-ready backend, a mobile/web frontend, automated tests, CI/CD, and Jira project tracking.

Primary goals:
- Simplicity and security for payments (UPI flow)
- Minimal friction onboarding (OTP + biometric)
- Reliable transaction tracking & reconciliation
- Clear analytics & exportable statements
- Operational readiness (monitoring, alerts, helpdesk)

---

## High-level Deliverables

- Backend API (REST) with authentication, UPI payment orchestration, biller integrations, transactions DB.
- Frontend (mobile-friendly React or React Native) for onboarding, payments, recharges, history, and profile.
- GitHub repository with branch-per-story workflow and this README as seed.
- Jira project with Epics, Stories, Subtasks, 2+ sprints, configured workflow.
- CI/CD (GitHub Actions) building, testing, and deploying to staging/prod.
- Automated tests (unit, integration, e2e).
- Documentation (API spec, deployment guide, runbook, demo script).

---

## Epics (Top-level)

- EPIC-Auth: User Authentication & Onboarding
- EPIC-UPI: Money Transfer & UPI Payments
- EPIC-RechargeBill: Recharge & Bill Payments
- EPIC-History: Transaction History, Statements & Analytics
- EPIC-Security: Security, PIN/Biometric & Notifications
- EPIC-Support: Customer Support & Dispute Management
- EPIC-DevOps: GitHub Integration, CI/CD & Monitoring

---

## User Stories (Summary)

See the full project spec for story-level detail. Key stories include:
- US1 Sign up with mobile number & OTP (3 SP)
- US2 Login via OTP + biometric (2 SP)
- US3 Link bank account (3 SP)
- US4 Send money using UPI (5 SP)
- US7 Mobile recharge (3 SP)
- US10 Transaction history & export (3 SP)
- US11 Download monthly statement (2 SP)
- US13 Push & SMS notifications (2 SP)
- US16 In-app support chat (3 SP)
- US19 CI/CD build/test/deploy (5 SP)

---

## Sprint Plan (Example)

- Sprint 0: Project setup (1 week) — repo structure, Jira, CI skeleton.
- Sprint 1: Onboarding & UPI basics (2 weeks) — US1-US4 core flows.
- Sprint 2: Recharge/Bill & History (2 weeks) — US7-US10.
- Sprint 3: Security & Notifications (2 weeks).
- Sprint 4: Analytics, Support & Stabilize (2 weeks).

Compressed demo option: Use 2 sprints to deliver a minimal E2E flow.

---

## API Surface (minimal)

- POST /auth/signup — { phone } → sends OTP
- POST /auth/verify — { phone, otp } → returns JWT
- POST /banks/link — { vpa | account+ifsc } → starts verification
- POST /transactions/send — { to, amount, txn_ref } → returns txn_id
- GET /transactions/{id} — transaction status
- GET /transactions — history & filters
- POST /recharge — { mobile, operator, amount }
- POST /bills/pay — { biller_id, amount }
- GET /statements/monthly?month=YYYY-MM — PDF link

All endpoints require HTTPS and JWT authentication.

---

## Data Model (summary)

- Users: id (UUID), phone_number, name, kyc_status, created_at
- LinkedAccounts: id, user_id, bank_name, vpa/masked_account, verified_at
- Transactions: id, user_id, type, amount, status, external_txn_id, metadata, timestamps
- Statements: id, user_id, period_start, period_end, file_url

---

## Security & Compliance Notes

- TLS 1.2+, JWT short expiry + refresh tokens
- Never store raw payment credentials; mask sensitive data
- Encrypt PINs with KDF + per-device salt
- OTP & payment endpoint rate-limiting
- Audit logs for 6+ months

---

## CI/CD & Repo Guidelines

- Branch-per-story naming: `feature/SCRUM-<issue>-short-desc`
- PRs require 1 dev + 1 QA reviewer, passing CI
- GitHub Actions: run tests on PR; push to main triggers build+deploy to staging
- Use GitHub Secrets / Vault for credentials

---

## Next Actions (short)

1. Commit this README to `main` (done by creating this file here).
2. Create a Jira project and import Epics/Stories/Subtasks (I can generate CSV or an import script).
3. Add `backend/`, `frontend/`, `infra/` folders and initial skeletons.
4. Add `requirements.txt` / `package.json` and CI workflow files under `.github/workflows/`.
5. Connect GitHub ↔ Jira via GitHub for Jira app and enable the development panel.

---

If you want, I can next:
- Generate a Jira import CSV for all Epics/Stories/Subtasks.
- Add a GitHub Actions CI skeleton and a `requirements.txt`.
- Create initial backend skeleton (FastAPI + SQLAlchemy) and frontend skeleton (React) with example endpoints.

Pick one of the next steps and I will implement it.
