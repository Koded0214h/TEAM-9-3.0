# Repelect Backend Feature Outline

Source: Repelect Product Requirements Document, version 1.0 (19 November 2026).

This document isolates the backend work for the hackathon MVP. The intended stack is FastAPI, PostgreSQL with PostGIS, SQLAlchemy 2.x, Alembic, Pydantic, and a background-job mechanism. Voter-allocation optimization and queue simulation algorithms belong to another workstream; this backend will expose stable contracts and placeholders for them.

## Implementation progress

- [x] Module 1 - Platform foundation
  - [x] FastAPI application factory and versioned `/api/v1` router
  - [x] Environment-based typed settings and `.env.example`
  - [x] PostgreSQL/PostGIS SQLAlchemy setup
  - [x] Alembic configuration and initial PostGIS migration
  - [x] Consistent API error envelope
  - [x] Request IDs, structured JSON logging, and configurable CORS
  - [x] Liveness and database readiness endpoints
  - [x] Local PostGIS Docker Compose service
  - [x] Automated tests and lint configuration
- [x] Module 2 - Identity and access control
  - [x] Local login, access tokens, refresh-token rotation, and logout/revocation
  - [x] Secure Argon2 password hashing and inactive-user enforcement
  - [x] User administration and four seeded platform roles
  - [x] Reusable server-side role dependencies
  - [x] Safe one-time system-administrator bootstrap command
- [x] Module 3 - Geography, polling units, dataset ingestion, and provenance
  - [x] Versioned, classified datasets with activation and provenance metadata
  - [x] CSV and GeoJSON validation with row-level errors and dry runs
  - [x] State, LGA, ward, and registration-area hierarchy with PostGIS boundaries
  - [x] Polling-unit storage, filtering, search, detail, GeoJSON, and proximity APIs
  - [x] Coordinate-to-boundary resolution and spatial indexes
- [x] Module 4 - Scenario management and proposed polling-unit changes
  - [x] Immutable baseline snapshots and effective scenario state
  - [x] Scenario lifecycle, duplication, archive status, and soft deletion
  - [x] Revision history and optimistic-concurrency conflict detection
  - [x] Proposed new, relocated, and deactivated polling-unit overlays
  - [x] Planning-boundary enforcement and reversible scenario changes
- [x] Module 5 - Capacity and voter-load analysis
  - [x] Versioned global or ward-specific target and maximum-capacity rules
  - [x] Configurable underutilization threshold and transparent classification
  - [x] Effective-scenario load ratios and per-unit classifications
  - [x] Overloaded, underutilized, and within-capacity summary counts
- [x] Module 6 - Voter-allocation engine contract and placeholder
  - [x] Versioned input/output contracts and immutable scenario snapshots
  - [x] Replaceable `AllocationEngine` interface
  - [x] Explicit deterministic stub with no fabricated recommendation
  - [x] Persisted run lifecycle, retrieval, cancellation, and result selection guard
- [x] Module 7 - Equipment planning
  - [x] Equipment catalogue and versioned ward inventory snapshots
  - [x] Configurable, versioned demand rules with transparent formulas
  - [x] Finite-stock allocation, shortage, surplus, and coverage data
  - [x] Scenario-pinned equipment plans and input snapshots
  - [x] Reason-required manual overrides preserving calculated values
- [x] Module 8 - Queue/capacity simulation contract and placeholder
  - [x] Versioned ward/global simulation assumptions
  - [x] Immutable scenario, equipment, and assumption input snapshots
  - [x] Replaceable `SimulationEngine` interface
  - [x] Explicit stub that produces no fabricated queue estimates
  - [x] Persisted simulation run lifecycle, retrieval, and cancellation
- [x] Module 9 - Comparisons, metrics, and explanations
  - [x] Baseline-versus-scenario polling-unit change table
  - [x] Added, relocated, deactivated, and unchanged summaries
  - [x] Capacity and equipment metrics with rule/version explanations
  - [x] Algorithm-owned metrics returned only from successful runs
  - [x] Explicit `unavailable` values instead of fabricated estimates
- [x] Module 10 - Exports
  - [x] Authorized JSON scenario-review package
  - [x] CSV before/after polling-unit allocation table
  - [x] Dataset provenance, versions, assumptions, warnings, and generation metadata
  - [x] Persisted export jobs with expiring authenticated downloads
- [ ] Module 11 - Auditability, reliability, privacy, and security hardening

## 1. Backend scope and boundaries

The backend must:

- serve polling units, administrative geography, voter-count aggregates, equipment data, configuration, and scenario data;
- preserve an immutable official/baseline dataset while allowing scenario-specific proposals and overrides;
- support geographic filtering, point/boundary validation, proximity lookup, and distance values;
- manage optimization and simulation runs without implementing their mathematical logic yet;
- compare baseline and scenario state;
- authenticate users, enforce roles, and keep a complete audit history;
- import clearly labelled sample data and export scenario results;
- expose assumptions, data provenance, limitations, and run explanations.

The backend must not:

- store or expose individual voter identities;
- alter official voter assignments or official polling-unit status;
- implement electronic voting, voter registration, result collation, or public election monitoring;
- implement production INEC integrations, nationwide scaling, procurement, or live equipment tracking in the MVP;
- decide voter allocations or implement queue-simulation mathematics in this workstream.

## 2. Platform foundation

### 2.1 Application structure

- Versioned REST API under `/api/v1`.
- FastAPI dependency injection for database sessions, current user, permissions, and settings.
- SQLAlchemy models/repositories and Alembic migrations.
- PostgreSQL with PostGIS for points, polygons/multipolygons, containment, proximity, and spatial indexes.
- Pydantic request/response schemas with consistent validation and serialization.
- Environment-based configuration and secret handling.
- OpenAPI documentation with example requests and responses.
- Standard error envelope containing a machine code, human-readable message, field details, and request ID.
- Health endpoints for liveness and readiness.
- Structured logs and request correlation IDs.

### 2.2 Background work

Long-running imports, exports, optimization calls, and simulation calls must not block HTTP requests.

- Create a job/run record before dispatch.
- Track `queued`, `running`, `succeeded`, `failed`, and `cancelled` states.
- Store progress percentage or a user-readable stage where available.
- Preserve input snapshots and errors for diagnosis.
- Make retries idempotent and prevent a failed run from changing the baseline or last successful result.
- MVP implementation may use FastAPI background tasks; a worker queue such as Celery, Dramatiq, or RQ is the preferred upgrade path.

## 3. Identity and access control

### 3.1 Authentication

- User login and token refresh/logout.
- Secure password hashing if accounts are local.
- Access-token validation and disabled-user checks.
- Current-user/profile endpoint.
- Bootstrap mechanism for the first system administrator.

### 3.2 Roles

Use role-based access control with these initial roles:

- `planning_admin`: inspect data, create and edit scenarios, run engines, review recommendations, and export.
- `operations_officer`: inspect scenarios, manage equipment inputs/overrides, run equipment calculations and simulations, and export.
- `system_admin`: manage users, datasets, configurations, inventory, and audit records.
- `reviewer`: read-only access to maps, scenarios, comparisons, explanations, and exports.

Every mutating endpoint must enforce its permission server-side. Dataset management, configuration publication, user management, and access to full audit history are system-admin operations.

## 4. Geography and polling-unit data

### 4.1 Administrative geography

- Store states, LGAs, wards, and optional registration areas as a hierarchy.
- Store authoritative or sample boundary geometry and its source/version.
- List and retrieve each geography level.
- Filter children by parent geography.
- Return lightweight GeoJSON suitable for a limited MVP map.
- Resolve a coordinate to its containing state/LGA/ward/registration area.
- Validate hierarchy consistency and invalid/self-intersecting geometry during import.

### 4.2 Polling units

- Store code, name, address, coordinates, ward, LGA, state, status, source, and dataset version.
- Store aggregated registered-voter count, never voter identity records.
- Store official current equipment allocation when available.
- List units by state, LGA, ward, registration area, status, and scenario.
- Search by unit code/name and address.
- Retrieve a detailed polling-unit record.
- Return map-friendly GeoJSON plus summary attributes.
- Find nearby polling units within a radius or nearest-N limit.
- Compute simple straight-line/geodesic distance for the MVP and label it as an estimate.
- Return overload/utilization status using the effective configured capacity threshold.
- Support pagination, stable sorting, and compact field selection for map performance.

### 4.3 Geospatial context

- Store or reference optional roads, settlements, landmarks, and other context layers.
- List available layers and their provenance.
- Serve layer metadata and bounded GeoJSON for the demonstration area.
- Keep 2D/3D rendering in the frontend; the backend supplies coordinates, elevation/context data if available, and map-layer metadata.

### 4.4 Location/address lookup

- Provide a backend geocoding adapter used by map address search.
- Normalize provider results to address, latitude, longitude, confidence, and provider attribution.
- Cache safe lookup results and handle provider timeout/rate-limit errors.
- Permit a sample/local gazetteer for an offline hackathon demo.

## 5. Dataset ingestion and provenance

- Import polling units, voter counts, administrative boundaries, geospatial context, equipment inventory, and operational assumptions from CSV/GeoJSON as appropriate.
- Validate required fields, coordinates, duplicate codes, numeric ranges, parent geography, and boundary containment.
- Support a validation-only/dry-run mode.
- Produce row-level validation errors that can be downloaded.
- Record dataset type, name, version, source, checksum, uploader, import time, row counts, status, and whether data is `official`, `sample`, or `synthetic`.
- Prevent partially failed imports from becoming active.
- Allow a system administrator to activate one dataset version for the baseline.
- Retain prior versions for reproducibility and existing scenario snapshots.
- Ensure every relevant API response or run result can identify illustrative/sample data.

## 6. Scenario management

### 6.1 Scenario lifecycle

- Create a scenario from the active baseline with a name, description, planning area, and assumption/configuration version.
- List, retrieve, update metadata, duplicate, archive, and optionally soft-delete scenarios.
- Initial statuses: `draft`, `ready_for_review`, `reviewed`, and `archived`.
- Enforce optimistic concurrency with a revision number or update timestamp.
- Keep the baseline immutable; scenario changes are overlays or versioned snapshots.
- Record creator, collaborators if enabled, timestamps, and latest successful engine runs.

### 6.2 Proposed polling-unit changes

- Add a proposed unit from an address or selected coordinate.
- Edit its name/address/coordinates and other scenario-only attributes.
- Move a proposed location.
- Deactivate/reactivate a proposed location.
- Remove a scenario-only proposal.
- Represent proposed new, relocated, or deactivated units without editing the official record.
- Validate that a proposed point falls inside the scenario's permitted administrative boundary.
- Return nearby units and effective ward/LGA context during validation.
- Record the reason for material edits where required.

### 6.3 Scenario effective state

- Resolve baseline records plus scenario overlays into one effective read model.
- Return official/proposed/scenario-only status explicitly.
- Return before/after values for unit location, voter load, status, and equipment allocation.
- Snapshot inputs used by every engine run so later scenario edits do not rewrite old results.

## 7. Capacity and voter-load analysis

This is ordinary backend rule evaluation, not the allocation algorithm.

- Configure target and maximum voter capacity globally or by planning area.
- Define overload and underutilization thresholds.
- Calculate load ratio and classification for each effective polling unit.
- Return counts and lists of overloaded, underutilized, and within-capacity units.
- Provide baseline-versus-scenario summaries.
- Keep the rule version and effective dates with every result.

## 8. Voter-allocation engine integration - placeholder only

The backend owns orchestration, persistence, validation, and API contracts. Another workstream supplies the deterministic optimization implementation.

### 8.1 Input contract

Build a versioned engine payload containing:

- run ID, scenario ID, planning-area boundary, and input snapshot version;
- aggregated voter origins/counts;
- existing and proposed eligible polling units;
- current assignments at aggregate level;
- target/maximum capacities;
- permitted administrative boundaries;
- distance/travel-cost matrix or coordinates;
- accessibility/eligibility constraints;
- configurable objective weights.

### 8.2 Output contract

Accept and validate:

- run status and engine version;
- recommended aggregate voter allocation per polling unit;
- before/after voter counts;
- overloaded and underutilized units;
- proposed unit actions, when emitted;
- estimated distance/travel impact;
- objective/component values;
- satisfied, binding, and unsatisfied constraints;
- human-readable explanation/warnings.

### 8.3 Placeholder behavior

- `POST /scenarios/{id}/allocation-runs` creates a run and dispatches an `AllocationEngine` interface.
- Initially bind that interface to a `StubAllocationEngine`.
- The stub must return deterministic fixture data or a clearly labelled `not_implemented` result; it must never pretend to be an actual recommendation.
- Store run inputs/results separately from scenario edits.
- Allow retrieval, listing, cancellation where possible, and selection of a successful run as the scenario's active recommendation.
- Reject results that cross prohibited boundaries or exceed schema/range constraints before persisting them.
- Do not allow a recommendation to mutate official assignments.

## 9. Equipment planning

### 9.1 Equipment catalogue and inventory

- Manage configurable equipment types such as BVAS devices, ballot boxes, voting cubicles, forms, and registers.
- Store unit of measure, active status, description, and optional capacity metadata.
- Store available stock by planning area/location and dataset version.
- Store current/baseline polling-unit allocations.
- Validate non-negative quantities and prevent double counting within an inventory snapshot.

### 9.2 Configurable demand rules

- Create versioned rules by equipment type, planning area, and effective period.
- Support simple transparent MVP rules such as fixed minimum plus `ceil(voter_count / voters_per_item)`.
- Store minimum/maximum quantities, rounding method, priority, capacity values, and explanatory text.
- Preview a rule against a voter count before publishing it.
- Keep historical rule versions so results remain reproducible.

### 9.3 Demand and allocation results

- Calculate equipment demand for each effective polling unit using its voter load and active rule version.
- Compare demand with current allocation and available stock.
- Return recommended quantity, allocated quantity, shortage/surplus, coverage percentage, and warnings.
- Allocate finite stock using a simple documented priority policy for the MVP; keep the allocation strategy behind an interface if it becomes algorithm-owned.
- Compare baseline and scenario equipment distribution.
- Summarize shortages and locations needing additional resources.

### 9.4 Manual overrides

- Permit authorized users to override a recommended quantity.
- Require a non-empty reason.
- Preserve calculated value, overridden value, author, timestamp, and revision.
- Include overrides in comparisons, exports, and the audit log.

## 10. Queue/capacity simulation integration - placeholder only

The simulation mathematics is outside this backend workstream. The backend supplies configuration, orchestration, storage, and comparison.

### 10.1 Assumptions and input contract

- Voting-period start/end and time-step where applicable.
- Arrival-pattern identifier and parameters.
- Service-time/service-rate assumptions.
- Staffing and active-device counts.
- Equipment uptime/capacity assumptions.
- Scenario voter loads and equipment allocations.
- Assumption version, sample-data marker, and warnings.

### 10.2 Output contract

- Estimated queue length and waiting-time series/summary.
- Peak queue, average/max wait, throughput, utilization, and unserved/remaining voters where supported.
- Capacity/bottleneck flags per polling unit.
- Baseline-versus-scenario deltas.
- Engine version, explanation, limitations, and warnings.

### 10.3 Placeholder behavior

- `POST /scenarios/{id}/simulation-runs` dispatches a `SimulationEngine` interface.
- Initially use `StubSimulationEngine` with deterministic fixtures or an explicit `not_implemented` result.
- Persist input/output snapshots and expose run status/progress/errors.
- Mark every simulation output as an estimate and expose all assumptions used.

## 11. Comparison, metrics, and explanations

- Compare the baseline with one scenario or compare two compatible scenarios.
- Return added, moved, deactivated, and unchanged polling units.
- Return before/after voter loads and overload classifications.
- Return before/after equipment demand, allocation, shortage, and utilization.
- Return algorithm-supplied distance and simulation metrics when successful runs exist; otherwise return `unavailable`, not fabricated values.
- Calculate backend-owned summary metrics: over-capacity unit count, equipment coverage, change counts, and configuration/data versions.
- Present algorithm explanations, constraints, objective values, warnings, and limitations without silently rewriting them.
- Flag comparisons that use incompatible dataset or configuration versions.

## 12. Exports

- Export scenario summary as JSON and CSV for the MVP; PDF can be added if required by the demo.
- Export polling-unit before/after table.
- Export voter-allocation result table supplied by the engine placeholder/implementation.
- Export equipment demand/allocation/override table.
- Export simulation summary supplied by the simulation placeholder/implementation.
- Include scenario metadata, planning area, dataset versions, configuration versions, assumptions, sample/synthetic labels, generation time, and author.
- Generate larger exports as background jobs with expiring authorized download links.

## 13. Auditability and reliability

- Append audit events for login/security changes, dataset imports/activation, configuration changes, scenario lifecycle changes, polling-unit proposals, engine runs, selected results, equipment overrides, and exports.
- Each event stores actor, action, entity type/ID, timestamp, request ID, reason where applicable, and safe before/after data.
- Redact passwords, tokens, and secrets from logs/audit payloads.
- Provide filtered audit-history endpoints to authorized users.
- Wrap related mutations in database transactions.
- Use idempotency keys for run creation/import/export requests that may be retried.
- Use soft deletion or archival for reviewed/referenced records.
- Back up the database in deployed environments and test restoration before production use.

## 14. Privacy and security

- Accept aggregated voter counts only; reject or quarantine uploads containing unsupported personal voter fields.
- Validate file type, size, schema, and geometry before import.
- Apply least-privilege database credentials and role checks.
- Restrict CORS to configured frontend origins.
- Add rate limits to authentication, geocoding, imports, run creation, and exports.
- Use HTTPS in deployed environments and secure token/cookie settings.
- Avoid leaking internal stack traces or provider credentials.
- Record data retention and deletion rules for imports, job artifacts, exports, and audit records.

## 15. Suggested core data model

The exact schema can evolve, but the initial model should cover:

- `users`, `roles`, `user_roles`, `refresh_tokens` or sessions;
- `dataset_versions`, `import_jobs`, `import_errors`;
- `states`, `lgas`, `wards`, `registration_areas`;
- `polling_units`, `polling_unit_voter_counts`;
- `geospatial_layers`, `geospatial_features` where local context data is stored;
- `equipment_types`, `inventory_snapshots`, `inventory_items`, `baseline_equipment_allocations`;
- `capacity_rule_versions`, `equipment_rule_versions`, `simulation_assumption_versions`;
- `scenarios`, `scenario_revisions`, `scenario_polling_unit_changes`;
- `allocation_runs`, `allocation_run_inputs`, `allocation_results`;
- `equipment_plan_runs`, `equipment_plan_items`, `equipment_overrides`;
- `simulation_runs`, `simulation_run_inputs`, `simulation_results`;
- `export_jobs`, `audit_events`.

Important database constraints/indexes:

- unique polling-unit code within a dataset version;
- unique geography code within its level/version;
- foreign-key enforcement for geography hierarchy;
- non-negative voter/equipment counts;
- valid run/status transitions at the service layer;
- GiST indexes on boundary and coordinate geometry;
- B-tree indexes on dataset version, geography IDs, scenario ID, status, and creation time;
- partial/unique constraints ensuring one active baseline/configuration version per intended scope.

## 16. Proposed API surface

This is an outline, not a frozen URL design.

### Authentication and administration

- `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`
- `GET/POST /users`, `GET/PATCH /users/{id}`
- `GET /audit-events`
- `GET /health/live`, `GET /health/ready`

### Geography and baseline data

- `GET /geographies/states`
- `GET /geographies/lgas?state_id=`
- `GET /geographies/wards?lga_id=`
- `GET /geographies/registration-areas?ward_id=`
- `POST /geographies/resolve-point`
- `GET /polling-units`
- `GET /polling-units/{id}`
- `GET /polling-units/{id}/nearby`
- `GET /map/layers`, `GET /map/layers/{id}/features?bbox=`
- `GET /locations/search?q=`

### Datasets and configuration

- `GET/POST /datasets`, `GET /datasets/{id}`
- `POST /datasets/{id}/validate`, `POST /datasets/{id}/activate`
- `GET /imports/{id}`, `GET /imports/{id}/errors`
- CRUD/version endpoints for capacity rules, equipment rules, and simulation assumptions

### Scenarios

- `GET/POST /scenarios`
- `GET/PATCH/DELETE /scenarios/{id}`
- `POST /scenarios/{id}/duplicate`
- `GET /scenarios/{id}/effective-polling-units`
- `POST /scenarios/{id}/polling-unit-changes`
- `PATCH/DELETE /scenarios/{id}/polling-unit-changes/{change_id}`
- `GET /scenarios/{id}/load-analysis`

### Runs, equipment, comparison, and export

- `GET/POST /scenarios/{id}/allocation-runs`
- `GET /allocation-runs/{run_id}`, `POST /allocation-runs/{run_id}/cancel`
- `POST /scenarios/{id}/equipment-plans`, `GET /equipment-plans/{run_id}`
- `POST /equipment-plans/{run_id}/items/{item_id}/override`
- `GET/POST /scenarios/{id}/simulation-runs`
- `GET /simulation-runs/{run_id}`, `POST /simulation-runs/{run_id}/cancel`
- `GET /comparisons?baseline_id=&scenario_id=` or `GET /scenarios/{id}/comparison`
- `POST /scenarios/{id}/exports`, `GET /exports/{export_id}`

## 17. MVP delivery order

### Phase 1 - foundation and sample data

- FastAPI project setup, PostgreSQL/PostGIS, migrations, settings, health checks, error format, and tests.
- Authentication/RBAC and initial admin bootstrap.
- Geography/polling-unit schema and sample-data import with provenance labels.
- Polling-unit list/detail/search/filter/nearby/map endpoints.

### Phase 2 - scenarios and rule-based analysis

- Immutable baseline plus scenario CRUD and revisions.
- Proposed polling-unit add/move/deactivate/remove with boundary validation.
- Capacity configuration and overloaded/underutilized analysis.
- Audit events for all mutations.

### Phase 3 - engine contracts and equipment

- Allocation engine interface, run lifecycle, input/output persistence, and explicit stub.
- Equipment catalogue, inventory, configurable demand rules, recommendations, shortages, and overrides.
- Simulation engine interface, assumptions, run lifecycle, and explicit stub.

### Phase 4 - comparison and delivery

- Baseline/scenario comparison and summary metrics.
- CSV/JSON exports and export jobs.
- Reliability, security, performance, and acceptance tests.
- OpenAPI cleanup and demo seed/reset workflow.

## 18. Backend MVP acceptance checklist

- Polling units for one labelled demonstration area can be imported and queried by geography.
- Map clients can fetch coordinates, basic attributes, effective voter counts, and overload status.
- Address/coordinate proposals can be validated against permitted boundaries.
- A proposed unit can be added, moved, deactivated, and removed without altering the baseline.
- Capacity thresholds and equipment rules are configurable and versioned.
- Equipment demand, stock coverage, shortages, and manual overrides are persisted and auditable.
- Allocation and simulation endpoints have stable, documented contracts and honest placeholder behavior.
- No placeholder result is represented as a real optimization or simulation result.
- Baseline/scenario differences can be retrieved and exported.
- Sample/synthetic data and simulation assumptions are clearly labelled in responses and exports.
- Reviewers cannot mutate data; privileged actions are role-protected.
- Scenario changes, overrides, imports, runs, and exports identify who did what and when.
- Failed imports or engine jobs cannot corrupt the baseline or erase the last successful result.
- Automated tests cover permissions, boundary enforcement, baseline immutability, rules, run-state transitions, comparisons, and exports.

## 19. Deferred beyond the backend MVP

- Nationwide authoritative datasets and national-scale tuning.
- Direct INEC internal-system integration.
- Formal legal approval workflows for creating/abolishing polling units.
- Individual voter records or production voter reassignment.
- Complex forecasting across election cycles.
- Road-network routing if a reliable source is unavailable for the demo.
- Live equipment tracking, procurement, and warehouse operations.
- A calibrated election-day digital twin.
- Enterprise multi-agency tenancy and permission hierarchies.
- Production implementation of the voter-allocation and queue-simulation algorithms owned by the other workstream.
