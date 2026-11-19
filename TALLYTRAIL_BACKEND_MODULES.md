# TallyTrail Backend Modules

Source: TallyTrail Product Requirements Document v1.0.

The backend stack is FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, Pydantic, Redis, Celery, and S3-compatible object storage. This plan covers backend responsibilities only. The Next.js interface, offline browser queue, document viewer UI, and optional OCR model are outside this repository.

## Delivery progress

### Batch 1 - Platform, access, and organisation

- [x] Module 1 - Platform foundation
- [x] Module 2 - Identity, MFA, and geographically scoped RBAC
- [x] Module 3 - Party workspaces and electoral geography

### Batch 2 - Election configuration and result intake

- [x] Module 4 - Elections, contests, candidates, and monitored parties
- [x] Module 5 - Document storage, integrity, and versioning
- [x] Module 6 - Result submissions, figures, validation, and idempotency

### Batch 3 - Reconciliation and operations

- [ ] Module 7 - Deterministic collation reconciliation engine
- [ ] Module 8 - Discrepancy records and investigations
- [ ] Module 9 - Monitoring dashboard, progress, and operational metrics

### Batch 4 - Evidence, external ingestion, and reporting

- [ ] Module 10 - Immutable audit trail and evidence integrity
- [ ] Module 11 - Best-effort public IReV ingestion
- [ ] Module 12 - Reconciliation reports and evidence exports

## Module 1 - Platform foundation

Build the shared backend runtime:

- FastAPI application factory and versioned `/api/v1` routing.
- Typed environment configuration with production validation.
- PostgreSQL connection management through SQLAlchemy 2.x.
- Alembic migration chain.
- Redis and Celery configuration for LGA/state rollups, exports, and IReV ingestion.
- Standard error envelope and request IDs.
- Structured JSON logs and UTC timestamps.
- CORS and trusted-host configuration.
- Liveness and dependency readiness endpoints.
- Docker Compose services for PostgreSQL, Redis, and local S3-compatible storage.
- Automated test, lint, and formatting configuration.
- OpenAPI documentation and consistent pagination conventions.

## Module 2 - Identity, MFA, and geographically scoped RBAC

Implement secure personnel access:

- Local email/password authentication with Argon2 hashing.
- Short-lived access tokens and rotating, revocable refresh sessions.
- TOTP MFA enrollment, confirmation, challenge, recovery codes, and disable flow.
- Mandatory MFA enforcement for party administrators and operations users.
- Immediate account/session revocation.
- User invitation and activation workflow.
- Roles: `party_admin`, `pu_agent`, `ward_agent`, `collation_officer`, `operations`, and `legal_compliance`.
- Workspace membership separated from global identity.
- Geographical assignments restricting users to state, LGA, ward, or polling unit scope.
- Explicit server-side authorization dependencies for every protected operation.
- Device/session metadata and last-used timestamps.
- One-time initial administrator bootstrap command.

## Module 3 - Party workspaces and electoral geography

Create isolated organisational boundaries:

- Multi-tenant party workspaces with strict row-level workspace scoping.
- Workspace lifecycle: draft, active, suspended, archived.
- Party name, code, branding metadata, timezone, and contact settings.
- State, LGA, ward/registration area, and polling-unit hierarchy.
- Import polling-unit codes and hierarchy from validated CSV.
- Duplicate-code, parent-child, and hierarchy validation.
- Workspace-specific monitored coverage without rewriting the canonical geography.
- Personnel assignments to permitted geography nodes.
- Block submissions outside a user's active assignment unless an explicit override is recorded.
- Workspace activation checks requiring an election hierarchy and administrator.
- Coverage and assignment summary endpoints.

## Module 4 - Elections, contests, candidates, and monitored parties

Configure what is being monitored:

- Elections within a workspace, including type, date, jurisdiction, and status.
- Contests for presidential, governorship, senatorial, representative, or state assembly races.
- Candidates and political parties with ballot codes.
- Workspace selection of monitored candidates/parties.
- Election-specific geographic coverage.
- Form-level configuration mapping EC8A, EC8B, EC8C, and EC8D to hierarchy tiers.
- Activation validation so result intake cannot begin with incomplete contest configuration.
- Immutable configuration snapshot attached to every submitted result version.

## Module 5 - Document storage, integrity, and versioning

Preserve source evidence:

- S3-compatible storage adapter with private buckets.
- Presigned, short-lived upload and download URLs.
- Server-side file finalization and metadata verification.
- Supported image/PDF types and configurable size limits.
- SHA-256 hashing at ingestion.
- Stored object size, media type, page count where available, original filename, and storage key.
- Strict provenance: `party_submitted` or `public_irev`.
- Immutable original objects; corrections create new document versions.
- Parent/superseded version relationships.
- Duplicate binary detection without silently treating two submissions as equivalent.
- Integrity re-check endpoint comparing current bytes with the stored digest.
- Quarantine state for unsafe, corrupt, or mismatched uploads.
- Clear disclaimer that a matching hash proves stored-file integrity, not physical authenticity.

## Module 6 - Result submissions, figures, validation, and idempotency

Collect structured EC8A-EC8D results:

- Submission records tied to workspace, election, contest, geography, form type, document, submitter, and source.
- Statuses for draft, submitted, verified, invalidated, superseded, and cancelled.
- Candidate vote figures plus valid votes, rejected ballots, total votes cast, accredited voters, and registered voters where applicable.
- Non-negative integer and arithmetic validation.
- Dual-entry confirmation for key totals.
- Idempotency keys for weak-network retries.
- Duplicate active form detection at the same election/contest/geography/tier.
- Explicit zero-vote, cancelled unit, invalidated unit, supplementary poll, and superseded-version flags.
- Non-destructive corrections creating new versions.
- Submitter confirmation and verifier workflow.
- Submission timestamps, close-of-poll timestamps, and turnaround metrics.
- Source-document linkage for side-by-side display.

## Module 7 - Deterministic collation reconciliation engine

Implement reproducible arithmetic only:

- EC8A to expected EC8B ward totals.
- EC8B to expected EC8C LGA totals.
- EC8C to expected EC8D state totals.
- Expected total equals the sum of active, eligible lower-level results.
- Variance equals announced total minus expected total.
- Candidate and vote-field comparisons.
- Reconciliation statuses: matched, discrepancy detected, incomplete, pending review, and unverifiable.
- Missing-form count and exact missing geography IDs.
- A partial sum can never be marked matched.
- Explicit treatment of zero, cancelled, invalidated, supplementary, and superseded forms.
- Immutable input snapshot, engine version, execution duration, and output record.
- Synchronous ward execution target below two seconds.
- Celery-backed LGA/state execution with progress updates and safe retries.
- Deterministic reruns producing the same result for the same input snapshot.

## Module 8 - Discrepancy records and investigations

Manage human review without erasing evidence:

- Generate one discrepancy record per affected candidate or vote field.
- Record expected value, announced value, signed variance, tier, geography, and reconciliation run.
- Link every discrepancy to lower-level forms and announced source document.
- Statuses: open, assigned, awaiting clarification, resolved, unresolved, and further review.
- Investigator assignment and due dates.
- Agent clarification requests and responses.
- Supplementary evidence attachments.
- Append-only comments and status history.
- Resolution category and neutral outcome language.
- Preserve the original discrepancy even after resolution or corrected submissions.
- Prevent terminology that declares fraud or criminal conduct.

## Module 9 - Monitoring dashboard, progress, and operational metrics

Supply the command-centre read models:

- Metrics filterable by state, LGA, ward, and polling unit.
- Expected versus submitted EC8A counts.
- Missing polling units.
- EC8B, EC8C, and EC8D submission counts.
- Reconciliation completion rate and status counts.
- Open, assigned, resolved, and unresolved investigation counts.
- Submission turnaround time and reconciliation latency.
- Discrepancy traceability coverage.
- Progressive polling endpoints or server-sent updates for live operations.
- Query-efficient materialized summaries or cached read models.
- Clear source/provenance badges in response payloads.

## Module 10 - Immutable audit trail and evidence integrity

Provide legal/compliance traceability:

- Append-only audit records for authentication, invitations, assignments, uploads, submissions, corrections, verification, reconciliation, investigations, exports, and administrative changes.
- User ID, effective role, workspace, IP, user-agent/device metadata, request ID, and UTC timestamp.
- Safe before/after metadata without secrets or document bytes.
- Hash-chain audit records or equivalent tamper-evident integrity mechanism.
- Restricted read-only audit search for administrators and legal/compliance users.
- Evidence-integrity verification history.
- Retention controls and legal-hold markers.
- Security headers, rate limits, upload validation, and safe error handling.
- TLS/AES deployment requirements documented and enforced where application-controlled.

## Module 11 - Best-effort public IReV ingestion

Keep external evidence optional and isolated:

- Provider adapter for publicly accessible IReV records where technically permitted.
- Celery tasks with bounded retries, timeouts, and progress.
- Strict `public_irev` provenance and retrieval timestamp.
- External source URL/reference and response metadata.
- Do not treat retrieved material as party-submitted or automatically authoritative.
- Do not block party reconciliation when IReV is unavailable.
- Manual import fallback for publicly downloaded files.
- Duplicate hash and geography/form matching.
- Provider terms, rate limits, and feature flag configuration.
- No unverified scraping in the MVP.

## Module 12 - Reconciliation reports and evidence exports

Produce reviewable evidence packages:

- CSV reconciliation tables.
- PDF ward reconciliation report.
- ZIP evidence dossier containing report, source documents, hashes, version history, discrepancies, and audit manifest.
- Workspace/election/geography filters.
- Dataset, engine, form-version, provenance, and generation metadata.
- Neutral legal language and explicit limitations.
- Celery-backed export jobs with live status.
- Private object storage and expiring signed download URLs.
- Export manifest hash and file checksums.
- Target complete evidence bundle generation below 60 seconds for pilot scope.

## Backend MVP acceptance path

The Phase 1 MVP is complete when:

- one party workspace can configure one ward with three to five polling units;
- users are assigned to the exact polling units or ward they may operate in;
- three PU agents can submit versioned EC8A images and structured figures idempotently;
- a ward agent can submit EC8B figures and its source document;
- each stored document receives a SHA-256 digest and immutable version record;
- reconciliation reports missing forms and cannot match an incomplete ward;
- a complete ward reconciliation detects and quantifies the documented +150 variance;
- every variance links to all supporting EC8A records and the EC8B record;
- operations users can investigate without deleting the original discrepancy;
- legal/compliance users can inspect document hashes and audit events;
- a CSV/PDF evidence report can be generated with neutral terminology and provenance.

## Keys and external configuration matrix

- Module 1: PostgreSQL URL and Redis URL; local Docker defaults need no external keys.
- Module 2: application auth secret; TOTP does not require a provider key. Email invitations require an email provider key if enabled.
- Module 5: S3 endpoint, bucket, access key, and secret key; local MinIO defaults can be used for development.
- Module 11: no key is assumed until an approved IReV integration method is confirmed.
- Module 12: reuses object-storage credentials; no separate export key is required.
- Optional OCR: provider credentials only if a hosted OCR service is chosen; local OpenCV/Tesseract requires none.

No secret value belongs in Git. Development values must live in ignored `.env` files; production values belong in the deployment secret manager.
