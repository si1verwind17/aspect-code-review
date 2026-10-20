# Code Review Ledger

Method: aspect-scored review — severity sets the band, count refines within
it; scores derive from open findings by fixed arithmetic. This document is
the persistent ledger: scope, assumptions, overrides, open findings, archive,
history. Finding IDs are stable and never reused. Keep the section names and
order of this template — incremental reviews and future maintainers navigate
by them.

## Summary — 2026-10-17 @ 862df06 (incremental review, 11 aspects, scope: diff since 4bdacf6)

**Worst aspect: Requirements alignment (REQ) at 0/10.** Open criticals:
- REQ-001 C: a provider can cancel without the reason R7 requires.
- REQ-002 C: no metric or alert exists for undispatched events (NF11).
- REQ-003 C: BookingCompleted does not say whether the system or the provider completed it (UC12).
- REQ-004 C: there is no erasure, export or retention (NF5).

This review covered one fix commit. Availability edits now lock the resource row FOR UPDATE, and create and reschedule hold it FOR SHARE before they check availability. One finding was resolved: CON-001 C. The concurrency reviewer checked both race orders under READ COMMITTED and every lock site, and found no new deadlock edge. Concurrency safety moves from 3 to 4, with no critical left. Only create against a BLOCK is pinned by a test. Deleting the reschedule lock or the end-rule lock leaves the suite green, so both are filed as TSQ-016 M; each mutation was run. Three minors were found: TSQ-017, RDB-009 and REQ-019. Two clean-context reviewers covered the diff.

| Aspect | Score | Worst open | Open findings |
|---|---|---|---|
| Logic correctness (LOG) | **4** | major | LOG-006 M, LOG-007 M, LOG-008 M, LOG-009 M, LOG-010 M, LOG-011 M, LOG-012 m, LOG-013 m |
| Error handling (ERR) | **4** | major | ERR-002 M (w), ERR-003 M, ERR-004 m, ERR-005 m, ERR-006 m, ERR-007 m (w), ERR-008 m |
| Security (SEC) | **4** | major | SEC-003 M (w), SEC-004 M (w), SEC-005 M, SEC-006 m, SEC-007 m, SEC-008 m, SEC-009 m |
| Code pattern (PAT) | **6** | major | PAT-001 M, PAT-002 m, PAT-004 m, PAT-005 m (w), PAT-006 m |
| Concurrency safety (CON) | **4** | major | CON-002 M, CON-003 M, CON-004 M, CON-005 M (w), CON-006 M, CON-007 m |
| Contract & compatibility (CMP) | **5** | major | CMP-001 M, CMP-002 M, CMP-003 m (w), CMP-004 m |
| Logging (LGG) | **9** | minor | LGG-001 m, LGG-002 m (w), LGG-003 m, LGG-004 m, LGG-005 m, LGG-006 m |
| Test quality (TSQ) | **4** | major | TSQ-001 M, TSQ-003 M, TSQ-004 M, TSQ-005 M, TSQ-006 M, TSQ-007 M, TSQ-008 M, TSQ-009 M, TSQ-010 m, TSQ-011 m, TSQ-012 m, TSQ-013 m, TSQ-014 m, TSQ-015 m, TSQ-016 M, TSQ-017 m |
| Type & null safety (TYP) | **9** | minor | TYP-001 m, TYP-002 m (w) |
| Readability & maintainability (RDB) | **9** | minor | RDB-001 m, RDB-002 m, RDB-003 m, RDB-004 m, RDB-005 m, RDB-006 m, RDB-007 m, RDB-008 m, RDB-009 m |
| Requirements alignment (REQ) | **0** | critical | REQ-001 C, REQ-002 C (w), REQ-003 C, REQ-004 C, REQ-005 M, REQ-006 M, REQ-007 M, REQ-008 M, REQ-009 M, REQ-010 M, REQ-011 M, REQ-012 m (w), REQ-013 m, REQ-014 m, REQ-015 m, REQ-016 m, REQ-017 m, REQ-018 m, REQ-019 m |

Rows stay in catalog order (the History table's column order), never sorted
by score — so any two reviews line up row-for-row. The worst aspects are
named in the prose above, not by reordering the table.

Average (trend only, never the headline): **5.3**.

## Review scope

Incremental review at 862df06 (clean tree): the diff since 4bdacf6 for all 11 aspects. Four files were touched: `ddl/03-functions.sql` (`fn_create_booking`, `fn_reschedule_booking`), `sql/management/insert_availability_exception.sql`, `sql/management/end_availability_rule.sql` and `repo/AvailabilityManagementIT.kt`. The first review's hash, 4781c64, is the service's own repository; its tree is the one this repository holds at c51e603. Later hashes are commits in this repository. Findings outside the diff are carried forward from the full review at 4781c64, which covered:
- `src/main/kotlin/`
- `src/main/resources/` (33 SQL statements and `application.yaml`)
- `docs/backend-design/ddl/*.sql`, which is the Flyway migration source and therefore code
- `src/test/`
- `build.gradle.kts`

Context: `docs/domain-context.md @4781c64, owner-confirmed 2026-09-04`.

## Declared assumptions (scout pass @ 4781c64, 2026-10-17)

Evidence-based detections; each states the weakest claim its evidence
supports. Override any of these in User overrides — overrides persist and
bind future reviews.

- **Language(s)**: Kotlin 2.3 (about 3.2k lines in main, 1.5k in test) and PostgreSQL SQL/plpgsql (ddl about 1.2k lines, plus 33 statement files). One Gradle module.
- **House pattern standard**: Kotlin, repo-declared (README "Layout", data-design.md §4). It has these parts:
  - `core/` holds domain types, pure rules and ports, with no framework imports (verified).
  - `repo/` holds JdbcClient adapters that load SQL from resources.
  - `api/` holds controllers that delegate to core.
  - `sys/` holds wiring; `worker/` holds Kafka and the schedules.
  - Every multi-statement write is one plpgsql call.
  - There is no ORM, and tests use hand-written fakes.
  - No linter or formatter is configured.
- **Auth model** (amended @66308b9): in-code. A JWT resource server with a required issuer; every path except `/actuator/**` needs a token. `/internal/**` also needs scope `booking.contacts.read`, and `POST /v1/providers` needs scope `booking.providers.create` (`sys/SecurityConfig.kt:36-39`). Every other authorization comes from `provider_admin` membership in the database. No network isolation is committed. Any holder of an issuer token is an untrusted caller (domain-context §5). Which tokens carry the two scopes is up to the IdP and is not recorded (SEC-009).
- **Deployment model**: assumed, never deployed. Basis: owner statement in domain-context §4; there are no manifests.
  - Designed topology: at least 2 `booking-api` and at least 2 `booking-worker` replicas from one image, chosen by profile. The relay and both sweeps run on every worker.
  - Design targets, never measured: about 500 providers, 2,000 resources, 10k bookings/day, 50 req/s search and 10 req/s writes.
  - Hikari pool of 10. The relay runs every 500 ms in batches of 100; the expiry sweep every 30 s; auto-complete hourly.
- **Consumed contract surfaces**: none have a consumer.
  - The HTTP `/v1/**` API is undeployed.
  - `booking-lifecycle-v1` is an unpublished draft (owner).
  - `booking-gate-resolution-v1` has no producer.
  - The schema reaches the database through Flyway at every pod startup, from migrations generated out of `ddl/` (`build.gradle.kts:64-80`).
- **Tests**: JUnit 5, in three tiers: pure unit tests, hand-faked orchestration tests, and `*IT` tests against real PostgreSQL (Testcontainers, or `BOOKING_TEST_JDBC_URL`).
  - The command `./gradlew test --offline` works here.
  - Baseline @4781c64: 72 tests, 5 failing. At 862df06 (amended): 86 tests, the same 5 failing. ApplicationContextIT fails 3 times (TSQ-009) and the BookingLifecycleIT relay pair fails twice (TSQ-001).
- **Exclusions**:
  - `build/`, `.idea/` and the Gradle wrapper
  - the documentation tooling: `docs/backend-design/build-review.mjs`, `package*.json` and `design-review.html` (owner: not a module)
  - the generated `data-dictionary.yaml`
- **Domain facts**: from domain-context §4 and §7, owner-confirmed.
  - No money anywhere. Durations are in minutes; horizon and grace in days. One booking takes one unit of capacity.
  - Instants are UTC; rules are wall-clock times in the provider's IANA zone. The session's values are authoritative over the current service row.
  - HELD and CONFIRMED hold capacity; the other five states are terminal.
  - Domain rejections are `BK001`–`BK009`; any other SQLSTATE is a defect.
  - Create is idempotent on (customer, key).
  - The outbox is at-least-once: the claim takes no lock and consumers dedupe on `eventId`.
  - The gate consumer dedupes on `inbox_message.message_id`. Events carry identifiers only.
- **Sweeps run** (src/main + ddl unless noted):
  - Raw identifier splices: SQL keyword next to `${`, `$x` or `"+`, or `EXECUTE`. 1 hit (`ddl/01:341`, a trigger `EXECUTE FUNCTION`); suppressed. All SQL is resource files with bound params.
  - Failure collapsed to a benign value: `catch (`, `runCatching`, `?: emptyList()`, `EXCEPTION WHEN`. 5 hits: `RuleViolations.kt:16` (translation), `OutboxRelay.kt:33` (row retained; feeds REQ-002 and LGG-001), `ListingService.kt:27` (correct for UC10), `ddl/03:348` and `:595` (re-raise as BK001). No collapse finding.
  - Init-only schema delivery: `initdb`, `init.sql`, `flyway`. 0 init-only hits; Flyway runs at startup. The delivery question leads to CMP-001.
  - Ungated tests touching real systems (src/test): `DataSource`, `JdbcClient`, `PostgreSQLContainer`. 5 files plus ApplicationContextIT, all gated by Testcontainers or an env var. The unguarded `clean()` is TSQ-010.
  - Silently-defaulting selectors: `X? = null`, `?:`, `orElse`, plpgsql `DEFAULT`. 25+ hits. Leads: `BookingDtos.kt:45` (LOG-005), `AvailabilityAdminController.kt:66` (LOG-004, LOG-009, PAT-003), `ddl/03:88` (CMP-002). The rest are suppressed (deliberate PD14 selection, membership-bound on-behalf, owner-confirmed contact fill).
  - Secrets adjacent to logging: 26 log calls. No credential or customer PII on a reachable path. `ApiExceptionHandler.kt:41` renders pgjdbc row detail (LGG-003).
  - Discarded external-mutation results: `send().get`, dropped `.update()`. 6 hits. `JdbcProviderSetupRepository.kt:77` leads to LOG-010; `:43` folds into ERR-003; the rest are guarded in SQL.
  - Numeric parse collapsed to zero: `toXOrNull`, `toInt()`, `parseInt`. 0 hits.
  - Retry budget against the caller's deadline:
    - Kafka `.get(10 s)` with `max.block.ms` left at 60 s, 100 events per pass, all on one shared scheduler thread. This is ERR-001.
    - Producer retries after the 10 s timeout cause duplicate publishes, which is credited (at-least-once).
    - The backoff is capped at 5 min with unlimited attempts.
  - Caller-supplied clock or identity: request `startsAt`, `resourceRef`, `onBehalfOfCustomerRef`, contact fields, `linkedSubject`. `startsAt` is checked against the server clock; `linkedSubject` leads to SEC-007 (latent); the rest are suppressed. No request field names "now".
- **Domain-context checklist**:
  - I1 (one occupied session per resource): held — `ddl/01-create-tables.sql:300-302`. The concurrency probe found 0 overlaps in 11.8k creates.
  - I2 (capacity per session): held — `ddl/03-functions.sql:342-345, 589-592`, CHECK at `ddl/01:296`.
  - I3 (one event per committed transition): held — `ddl/01:445`, `ddl/03:421, 510-511`.
  - I4 (no PII in events): held — `ddl/03:171-212` is the only outbox writer.
  - I5 (absent, not forbidden) (amended @66308b9): no longer reachable by an end-user token; the contacts route needs the service scope (`sys/SecurityConfig.kt:37`). A scope holder still reads any booking, as AQ3 intends.
  - I6 (transitions are rows): held — `ddl/03:437-445`.
  - Hazard, `POST /v1/providers` self-service: owner declined; filed as SEC-002, resolved @66308b9.
  - Hazard, gate consumer with no dead-letter: owner declined, filed as ERR-005 (latent).
  - Not exercised: the internal contacts endpoint has no legitimate caller (SEC-001, resolved @66308b9, rested its reach on an untrusted caller); `resource.idp_subject` is read by nothing (REQ-010, SEC-007); the reschedule resource-change plumbing is wired since eef5ebc (LOG-005 resolved); nothing crosses the Kafka edges (ERR-004/005/006, SEC-008, TYP-001 latent); `AWAITING_PAYMENT` is unreachable.
- **External-state journeys**: 11 operations enumerated.
  - Operations: create (including replay), cancel, approve, decline, attendance, reschedule, the expiry sweep, the auto-complete sweep, gate consume, relay publish/mark/record, provider setup writes, and availability rule and exception writes.
  - Empty or problematic cells:
    - create, ambiguous: concurrent same-key requests → CON-004.
    - create, replay with a different body → LOG-011.
    - sweeps, delayed: starved by the relay → ERR-001 (resolved @4bdacf6).
    - relay, partial order: → LOG-003 (resolved @dc188b7).
    - relay, rejected by the broker, persistently: no escalation → REQ-002.
    - gate consume, partial: claim before effect → ERR-004.
    - gate consume, malformed: → ERR-005.
    - gate consume, unknown booking: → ERR-006.
    - provider setup, partial: → ERR-003.
    - provider setup, already-linked: → LOG-010.
    - setup and availability writes, pre-flight CHECK: → ERR-002.
    - setup and availability writes, retries: → ERR-007.
    - availability edit vs create: → CON-001 (resolved @862df06).
  - Every other cell is decided or credited.
- **Scoring interpretation**: none → 10; minors only → 9 flat (listed and
  counted, never deducted); within the worst open C/M tier each *verified*
  finding counts one unit (widespread majors count two; doubling never
  applies to criticals); score = band start − step × (units − 1), clamped
  at the band floor (critical 3/−1/0, major 6/−1/4). The first unit is free
  — it sets the band: a single widespread major is 2 units → 6 − 1×1 = 5,
  never 4. Unverified C/M claims are listed as candidates and do not
  count.

## User overrides

_None yet._

## Open findings

Severity: C = critical, M = major, m = minor; (w) = widespread (counts
double). Findings open @ 862df06. A finding body stays pinned to its
discovery hash: 4781c64 unless its Status line says `found @<hash>`. Aspect sections stay in catalog order (same as the summary
table); a `---` rule before each aspect header keeps the section boundary
visible mid-scroll.

---

### Logic correctness (LOG) — 4/10 · 8 open

**LOG-006 · M · isolated — Availability search applies neither R4 lead time nor R5 horizon and offers past starts**
- `ddl/03-functions.sql:84-156` (comment `:156` "R4 and R5 are applied by the caller"); `core/availability/AvailabilityService.kt:22-27`; `sql/availability/search_availability.sql:1-2`
- Worksheet: reach any caller · residue request · signal none → major
- Intent: UC4. A search over a past date returns 29 slots; so does one beyond the 90-day horizon; creating any of them yields BK004/BK005.
- Cross-ref: REQ (UC4).

**LOG-007 · M · isolated — Slot grid anchored to the query's `from`, not the window start**
- `ddl/03-functions.sql:75-78`, `:128`, `:138`
- Worksheet: reach any search whose `from` falls inside a window (from=now, a paginated page 2) · residue request · signal none → major
- Intent: data-design OQ2. With `from=09:07` the offered starts are 09:07 and 09:22, and an existing 09:15 session with room never matches (exact `starts_at` join), so it vanishes from results.
- Cross-ref: REQ-016 (same code, `ddl/03-functions.sql:128`).

**LOG-008 · M · isolated — A customer cannot withdraw a HELD request inside the cancellation window**
- `ddl/03-functions.sql:473-480`
- Worksheet: reach customer at an approval-mode provider whose start is within 24 h · residue request (BK007; the hold persists) · signal caller → major
- Intent: UC6, and requirements §4.1, where HELD→CANCELLED needs only "Before start time" (R6 sits on the CONFIRMED row).
- Cross-ref: REQ; TSQ-005 (same code, `ddl/03-functions.sql:473`); RDB-001 (same code, `ddl/03-functions.sql:473`); RDB-005 (same code, `ddl/03-functions.sql:473`); REQ-001 (same code, `ddl/03-functions.sql:473`).
- Still open @eef5ebc: `:473-480` still applies the window to HELD cancels. The new reschedule comment (`ddl/03:571-574`) says a HELD request has no window, so the two paths now disagree.

**LOG-009 · M · isolated — A rule with a future effective_from cannot be ended; the attempt returns 500**
- `api/AvailabilityAdminController.kt:66`; `sql/management/end_availability_rule.sql:3-9`; CHECK `availability_rule_dates_forward` at `ddl/01-create-tables.sql:239`
- Worksheet: reach provider withdrawing a pre-published rule · residue request · signal caller (500) → major
- Evidence: the default "today" is before effective_from, giving 23514 → 500. Even an explicit date leaves at least one day published.
- Still open @dc188b7: the no-body default is now the provider's local today (`end_availability_rule.sql:5-6`), but it still precedes a future effective_from, so the CHECK still answers 500.
- Cross-ref: LOG-013 (same code, `sql/management/end_availability_rule.sql:3`).

**LOG-010 · M · isolated — Re-linking an already-linked service and resource answers 404 "no such provider, service or resource"**
- `sql/management/link_service_resource.sql:10`; `repo/JdbcProviderSetupRepository.kt:77`; `core/management/ProviderSetup.kt:89-93`; `api/ProviderSetupController.kt:106-110`
- Worksheet: reach any admin retrying the link (e.g. after a lost 204) · residue request · signal caller (misleading) → major
- Evidence: two identical POSTs give 204 then 404, although the link exists.
- Cross-ref: LGG-002 (same code, `api/ProviderSetupController.kt:107`).

**LOG-011 · M · isolated — Idempotency replay ignores the request body**
- `ddl/03-functions.sql:315-325`; `api/BookingOutcomeResponder.kt:25-35`
- Worksheet: reach any client reusing a key · residue request · signal none → major
- Evidence: key K for slot T1, then `POST {startsAt:T2}` with K → 200 with booking A(T1). No booking exists at T2, and the body does not show the mismatch.
- Cross-ref: CMP; CON-004 (same code, `ddl/03-functions.sql:315`).

**LOG-012 · m · isolated — Approval, gate resolution or reschedule accepted after hold_deadline until the next sweep**
- `ddl/03-functions.sql:464-466` (checks starts_at only); sweep interval `application.yaml:54`. Since 4bdacf6 the expiry sweep has its own thread, so the window is the 30 s interval plus the sweep's run time (ERR-001 resolved).
- Second occurrence @eef5ebc: `fn_reschedule_booking` (`ddl/03-functions.sql:619-623`) moves a HELD booking whose deadline has already lapsed, and returns 200. The sweep expires it within 30 s.

**LOG-013 · m · isolated — Ending a rule with an explicit date can extend an already-ended rule**
- `sql/management/end_availability_rule.sql:3-9` has no guard; `{effectiveUntil: 2099-01-01}` revives a rule ended in the past.
- Cross-ref: LOG-009 (same code, `sql/management/end_availability_rule.sql:3`).

---

### Error handling (ERR) — 4/10 · 7 open

**ERR-002 · M · widespread — Caller mistakes become 500 "internal error" plus an ERROR "unhandled defect" stack trace**
- `api/ApiExceptionHandler.kt:39-45` (catch-all, which wins over Spring's defaults). It catches:
  - type mismatch on every UUID or Instant param
  - a missing `@RequestParam`, malformed JSON, or an unknown route
  - `Page` `require` (`core/listing/Listing.kt:36-39`)
  - DB CHECK or UNIQUE violations from caller input: timezone (`ddl/01:94`), blank names, dayOfWeek, `endsAt ≤ startsAt` (`ddl/01:263`), a duplicate `linkedSubject` (`ddl/01:139`)
- Worksheet: reach any token holder · residue request · signal caller (wrong class, rule "none") → major; widespread: every controller module.
- Evidence (probe): `/v1/providers/not-a-uuid/availability` → 500 `{"code":"INTERNAL","rule":"none"}`; `POST /v1/providers {"timezone":"Mars/Olympus"}` → 500 plus an ERROR log line. NF8 is lost.
- Cross-ref: CMP (error shape), LGG (noise at ERROR); LGG-003 (same code, `api/ApiExceptionHandler.kt:41`).

**ERR-003 · M · isolated — Provider creation is two autocommit statements**
- `core/management/ProviderSetup.kt:61-66`; `repo/JdbcProviderSetupRepository.kt:25-44` (dropped `.update()` at `:43`); there is no `@Transactional` or TransactionTemplate anywhere in src
- Worksheet: reach `POST /v1/providers` with a failure between the statements (connection drop, pod kill) · residue external (a provider with no admin, unmanageable; a retry creates a second provider) · signal caller (500) → major
- Breaks the house rule "every multi-statement write is one function, one transaction" (data-design.md:424).
- Cross-ref: PAT, SEC-002; CON-005 (same code, `core/management/ProviderSetup.kt:62`).

**ERR-004 · m · isolated — Gate consumer commits the inbox dedupe claim before the effect (latent)**
- `core/gate/GateResolutionService.kt:34-41, 80-83`; `repo/JdbcWorkerRepositories.kt:101-124`; contradicts the inbox_message comment at `ddl/01:~480` ("same transaction as the effect").
- A redelivery after a failure is answered DUPLICATE, so the resolution is lost.
- Latent: no producer exists (not exercised). If the edge becomes live, this is external + none → C.
- Cross-ref: PAT, CON; CON-005 (same code, `core/gate/GateResolutionService.kt:81`).

**ERR-005 · m · isolated — Malformed gate resolution is retried, then skipped, with no dead-letter (owner declined hazard, domain-context §7)**
- `worker/GateResolutionListener.kt:20-23` (the comment promises dead-lettering), `:46-68`; no CommonErrorHandler or DeadLetterPublishingRecoverer bean exists. Latent (no producer); external + none → C once live.

**ERR-006 · m · isolated — A resolution for an unknown booking is answered with silence (latent; owner unknown §8)**
- `core/gate/GateResolutionService.kt:44-45, 75`.

**ERR-007 · m · widespread — Setup and availability writes are not idempotent on retry**
- `ProviderSetup.kt:61-80`, `AvailabilityManagement.kt:76-104`, `JdbcBookingLifecycle.kt:69-87`
- A retry after a lost response creates duplicate providers, resources, services, rules or exceptions.
- A repeated reschedule emits a second BookingRescheduled.
- The rule commits before `conflictsFor`, so a failed read loses the R20 list.

**ERR-008 · m · isolated — Scope denials answer Spring's empty 403, not the service's ErrorResponse**
- Status: open, found @66308b9
- `sys/SecurityConfig.kt:37-38`; `api/ApiExceptionHandler.kt` never sees a filter-chain denial.
- A caller with a valid token but the wrong scope gets no `{code, rule, message}` body. `SecurityConfigTest` asserts the status only.
- Cross-ref: CMP-004; SEC-009 (same code, `sys/SecurityConfig.kt:37`); LGG-006 (same code, `sys/SecurityConfig.kt:37`); RDB-004 (same code, `sys/SecurityConfig.kt:37`).

---

### Security (SEC) — 4/10 · 7 open

**SEC-003 · M · widespread — Raw PostgreSQL error text, with PL/pgSQL frames and internal ids, returned to clients**
- `sys/BookingSqlExceptionTranslator.kt:40`; `repo/RuleViolations.kt:17`; `api/BookingOutcomeResponder.kt:83`; RAISE texts with bigint ids at `ddl/03-functions.sql:250, 423, 429, 560`
- Evidence (probe): BK001 detail = "ERROR: the resource is occupied … Where: PL/pgSQL function fn_create_booking(bigint,…) line 53 at RAISE". BK008 also acts as a cross-provider existence oracle for resource refs (`find_resource_id.sql` is unscoped). Weakened defense → major; widespread: every BK rejection on every write path.
- Added journey @eef5ebc: a reschedule onto another provider's real resource returns the BK008 text with internal ids, while an unknown ref answers "no such resource" (`BookingLifecycleService.kt:83-85`).
- Cross-ref: CMP, ERR.

**SEC-004 · M · widespread — Public refs drawn from a non-cryptographic PRNG**
- `sys/TimeAndIdConfig.kt:21` (`RandomGenerator.getDefault()`, L32X64MixRandom on JDK 25); `sys/IdGenerator.kt:28-31`
- Evidence: every public_ref and event_id takes its random bits from it. Refs are the only barrier on SEC-001 and on "answer as absent", and architecture-design.md:313 calls them non-enumerable. Predictable tokens → major; widespread: every entity's ref.
- Cross-ref: CON-005.

**SEC-005 · M · isolated — Any token from the issuer is accepted; no audience restriction**
- `application.yaml:22-25`; `sys/SecurityConfig.kt:29`. Verified in bytecode: Boot 4.1.1 adds an audience validator only when `jwt.audiences` is set. A token minted for another relying party of the same IdP is accepted. Weakened defense → major.

**SEC-006 · m · isolated — Actuator metrics and prometheus endpoints are unauthenticated**
- `application.yaml:58-62`; `SecurityConfig.kt:26` (`/actuator/**` permitAll).
- Cross-ref: REQ-002 (same code, `application.yaml:58`); REQ-006 (same code, `sys/SecurityConfig.kt:26`).

**SEC-007 · m · isolated — `linkedSubject` lets an admin bind or squat any IdP subject (latent; idp_subject read by nothing)**
- `ProviderSetupController.kt:57`; `sql/management/insert_resource.sql:3`; UNIQUE conflict → 500 discloses an existing link.

**SEC-008 · m · isolated — Gate consumer resolves AWAITING_PROVIDER_APPROVAL as PROVIDER from any topic message (latent)**
- `core/gate/GateResolutionService.kt:47-63` (`actorType = PROVIDER`, `actorSubject = messageId`). Contradicts PD18; no producer exists.
- Cross-ref: REQ (PD18), TYP-002.

**SEC-009 · m · isolated — The scope gate relies on the IdP withholding both scopes from end-user tokens, and nothing records that obligation**
- Status: open, found @66308b9
- `sys/SecurityConfig.kt:37-38, 44-45`; comments that state it as fact: `api/InternalController.kt:13-15`, `core/listing/ListingService.kt:42-43`, `sys/SecurityConfig.kt:19-20`
- The gate reads the default `scope`/`scp` authorities. "Never an end-user token" holds only if the issuer never grants `booking.contacts.read` or `booking.providers.create` to end users. PD1 (claim mapping) is still open. Latent: there is no deployment.
- Cross-ref: REQ-017, PD1; ERR-008 (same code, `sys/SecurityConfig.kt:37`); CMP-004 (same code, `sys/SecurityConfig.kt:37`); LGG-006 (same code, `sys/SecurityConfig.kt:37`); RDB-004 (same code, `sys/SecurityConfig.kt:37`).

---

### Code pattern (PAT) — 6/10 · 5 open

**PAT-001 · M · isolated — Worker pods serve the whole HTTP API: only worker beans are profile-gated**
- `@Profile` appears only at `worker/*.kt` (`KafkaEventPublisher.kt:22`, `WorkerConfig.kt:28`, `KafkaConfig.kt:23`, `GateResolutionListener.kt:25`, `WorkerSchedules.kt:15,36`). All `@RestController` classes, `ApiExceptionHandler` and `SecurityConfig` are ungated, and `spring-boot-starter-web` is unconditional (`build.gradle.kts:28`).
- Worksheet: reach load-bearing (domain-context §2: the profile split "is the real module split"; `BookingApplication.kt:6-13`: "`api` serves HTTP") · residue none (structural: every worker replica also exposes `/internal/**` and every write endpoint) · signal n/a → major (load-bearing violation)
- Cross-ref: SEC-001.

**PAT-002 · m · isolated — Repo adapter re-implements the reschedule state decision**
- `repo/JdbcBookingLifecycle.kt:82-83` duplicates `ddl/03-functions.sql:603-606`; `fn_reschedule_booking` returns no state.
- Wider @eef5ebc: the SQL now has a third branch (HELD stays HELD whatever the gate, `ddl/03-functions.sql:619-628`), and the Kotlin still infers the state from the gate (`JdbcBookingLifecycle.kt:82-83`). They diverge only if a provider's confirmation mode changes while it has a HELD booking, and no API changes the mode. The `COMMENT ON FUNCTION` at `ddl/03:660` is now stale.
- Cross-ref: RDB-001 (same code, `ddl/03-functions.sql:604`).

**PAT-004 · m · isolated — Logging inside core**
- `core/outbox/OutboxRelay.kt:4, 21, 45-48`, against `BookingOutcomeResponder.kt:15-16` ("Business code does not log").

**PAT-005 · m · widespread — core/ ↔ sys/ package cycle via `IdGenerator`**
- `core/booking/BookingService.kt:4`, `BookingLifecycleService.kt:3`, `core/gate/GateResolutionService.kt:10`, `core/management/AvailabilityManagement.kt:5`, `ProviderSetup.kt:6`; reverse edges at `sys/BookingSqlExceptionTranslator.kt:3`, `sys/CoreConfig.kt:3-20`.

**PAT-006 · m · isolated — Port and adapter placement fights the feature packages**
- `ProviderLookup` is declared in `core/listing/ListingService.kt:48-50` and used by management; `JdbcInboxRepository` loads `sql/booking/record_gate_rejection.sql`; commands are split between `BookingPorts.kt:64-92` and `BookingDomain.kt:96`.

---

### Concurrency safety (CON) — 4/10 · 6 open

**CON-002 · M · isolated — Concurrent creates of the same new group session fail with BK001 or deadlock instead of joining**
- `ddl/03-functions.sql:336-351` (ON CONFLICT arbitrates only `session_identity`; the non-arbiter `session_no_overlap` makes the second racer wait and then fail), `:348-350`; same shape at `:582-598`; `ddl/01-create-tables.sql:300-302`
- Worksheet: reach two customers booking the same not-yet-existing slot of a capacity>1 service · residue request (409 or 500; rolled back) · signal caller → major
- Evidence (verifier probe): 300 new capacity-3 slots, 3 racers each → 828 confirmed, 29 BK001, 43 40P01. I1 and I2 still hold.
- Cross-ref: TSQ-004 (same code, `ddl/03-functions.sql:348`).

**CON-003 · M · isolated — Reschedule locks two sessions in request order; crossing moves deadlock**
- `ddl/03-functions.sql:579-580` then `:583-594`; versus the expiry batch at `:644-653` / `:489-491`
- Worksheet: reach two crosswise reschedules, or a reschedule against a sweep · residue request (40P01 → 500; a lost sweep batch delays expiry by at least 30 s) · signal caller → major
- Evidence: the probes reproduced 40P01 (8/311 and 1/600).
- Cross-ref: TSQ-003 (same code, `ddl/03-functions.sql:489`); TSQ-004 (same code, `ddl/03-functions.sql:589`); RDB-001 (same code, `ddl/03-functions.sql:650`); RDB-005 (same code, `ddl/03-functions.sql:579`); REQ-018 (same code, `ddl/03-functions.sql:579`).

**CON-004 · M · isolated — Two concurrent creates with the same Idempotency-Key: the second gets 409 or 500, not the replay**
- `ddl/03-functions.sql:315-325` (unlocked replay read), `:342-345`, `:371-377`; `booking_idempotency_key_uq` in `ddl/02-create-indexes.sql:5-7`
- Worksheet: reach a client double-submit or retry while the first create is uncommitted · residue request · signal caller (wrong: BK002 "at capacity" for capacity 1; 23505 → 500 for capacity > 1) → major
- Evidence: deterministic probe; R15 requires the replay.
- Cross-ref: ERR; LOG-011 (same code, `ddl/03-functions.sql:315`); TSQ-004 (same code, `ddl/03-functions.sql:342`).

**CON-005 · M · widespread — One non-thread-safe RandomGenerator shared by the UUIDv7 generator across virtual threads**
- `sys/TimeAndIdConfig.kt:21`; `sys/IdGenerator.kt:26-33` (no synchronization). Callers:
  - `CorrelationIdFilter.kt:30` (every request)
  - `BookingService.kt:60-61`
  - `BookingLifecycleService.kt:85,105`
  - `JdbcCustomerDirectory.kt:47`
  - `ProviderSetup.kt:62+`
  - `GateResolutionService.kt:66,81`
- Worksheet: reach concurrent requests on one replica in the same millisecond · residue request (duplicate public_ref or event_id → 23505 → 500; merged correlation ids) · signal caller → major; widespread: every id minted by both workloads.
- Evidence: probes found 2.7M duplicate draw pairs in 12.8M with 64 virtual threads, and duplicates even with 2 threads.
- Cross-ref: SEC-004; ERR-003 (same code, `core/management/ProviderSetup.kt:62`); ERR-004 (same code, `core/gate/GateResolutionService.kt:81`).

**CON-006 · M · isolated — "No preference" resource selection is check-then-act and deterministic, so concurrent requests collide while another resource is free**
- `core/booking/BookingService.kt:85-93`; `sql/availability/select_resource.sql:27-35`
- Worksheet: reach two concurrent no-preference creates for the same start of a capacity-1 service with ≥2 eligible resources · residue request (BK002 409; never re-selected) · signal caller → major
- Evidence: probe; both picked resource 1, and resource 2 stayed empty.

**CON-007 · m · isolated — `record_failure` has no `dispatched_at IS NULL` guard**
- `sql/outbox/record_failure.sql:3-8` versus `mark_dispatched.sql:7`. A stale claim on another replica writes failure data onto a dispatched row.

---

### Contract & compatibility (CMP) — 5/10 · 4 open

**CMP-001 · M · isolated — No documented working path delivers a schema change to a database already at V1..V4**
- `build.gradle.kts:64-80` copies only root `ddl/*.sql` and renames four fixed files. Related: README.md:96-99 (the DDL is the "single source of truth"), data-design.md:607 ("numbered directories"), `application.yaml:16-18` (Flyway at every pod startup), and `src/test/.../TestDatabase.kt:41-45` (always `clean(); migrate()`).
- Mechanism answer: Flyway at startup from generated V1–V4. The routes a maintainer could follow:
  - Editing in place, per README, changes the checksum, so `validateOnMigrate` fails at every pod startup.
  - A numbered directory, per data-design, is never copied.
  - A new `05-x.sql` is copied without the V prefix and silently ignored.
  - Only an undocumented hand-named `V5__x.sql` works.
- Worksheet: reach the first schema change after deployment · residue process (all pods fail at startup, on the README route) · signal operator (startup crash) → major. The data-design and new-file routes leave the change unapplied with no signal (external + none). The verifier confirmed the documents disagree, so the tier is read from the README route.
- Still open @eef5ebc, now exercised: that commit edited `fn_reschedule_booking` inside `ddl/03-functions.sql`, which is the generated V3. A database already at V3 fails checksum validation at startup. No database has been deployed.

**CMP-002 · M · isolated — Availability search with an unknown `resourceRef` silently widens to all resources**
- `sql/availability/search_availability.sql:13` (unknown ref → NULL); `ddl/03-functions.sql:88, 116`
- Worksheet: reach any caller with a mistyped or nonexistent ref · residue request (slots for every eligible resource instead of none) · signal none → major
- Verifier: a foreign ref returns empty; only unknown refs widen.
- Cross-ref: LOG, TYP.

**CMP-003 · m · widespread — Error-body drift**
- Spring Security 401 and 403 responses have no ErrorResponse body. `rule` mixes "shape", "none", "UC1", "UC3", "UC9", "PD7", "section 4.1", "R1/R31" and "R18" (`ApiExceptionHandler.kt:31,44`, `AvailabilityAdminController.kt:79`, `ProviderSetupController.kt:92`, `BookingOutcomeResponder.kt:97`, `AvailabilityController.kt:52`, `BookingDomain.kt:53`).

**CMP-004 · m · isolated — Two routes narrowed to scoped tokens with no contract note**
- Status: open, found @66308b9
- `sys/SecurityConfig.kt:37-38`: `GET /internal/**` and `POST /v1/providers` now answer 403 without the scope. There is no consumer, so nothing breaks; AQ8 defers the published contract.
- Cross-ref: ERR-008; SEC-009 (same code, `sys/SecurityConfig.kt:37`); LGG-006 (same code, `sys/SecurityConfig.kt:37`); RDB-004 (same code, `sys/SecurityConfig.kt:37`).

---

### Logging (LGG) — 9/10 · 6 open

**LGG-001 · m · isolated — Relay failure line loses its cause and blames the broker for DB errors**
- `core/outbox/OutboxRelay.kt:33-48`: a TimeoutException renders `reason=null`, and the exception is not passed to the logger. A `markDispatched` DB failure is logged as "event dispatch failed".

**LGG-002 · m · widespread — Rejection log lines carry no subject identifier**
- `api/BookingOutcomeResponder.kt:57, 71`; `AvailabilityAdminController.kt:114`; `ProviderSetupController.kt:107`; `ListingController.kt:49`.
- Cross-ref: LOG-010 (same code, `api/ProviderSetupController.kt:107`).

**LGG-003 · m · isolated — pgjdbc "Failing row contains (…)" row data reaches ERROR logs**
- `api/ApiExceptionHandler.kt:41` logs the full exception. Reachable today: free-text `availability_exception.reason`, provider name and timezone, and `Key (idp_subject)=(…)`. Customer PII is not reachable today (no CHECK or caller-trippable UNIQUE on customer). It becomes critical if one is added.
- Cross-ref: ERR-002 (same code, `api/ApiExceptionHandler.kt:41`).

**LGG-004 · m · isolated — Untrusted strings logged raw (log forging)**
- `api/BookingOutcomeResponder.kt:91` (`supplied=`); `worker/GateResolutionListener.kt:40-43` (latent).

**LGG-005 · m · isolated — Worker log lines have no correlation id**
- `sys/CorrelationIdFilter.kt` is HTTP-only; pattern at `application.yaml:73`. Relay, sweep and gate lines print `[booking-service,]` (NF7).

**LGG-006 · m · isolated — A refused contacts or onboarding call leaves no service log line**
- Status: open, found @66308b9
- `sys/SecurityConfig.kt:37-38`. No AccessDeniedHandler or authorization-event listener is configured; denials appear only at Spring Security DEBUG. No documented process reads such a line.
- Cross-ref: ERR-008 (same code, `sys/SecurityConfig.kt:37`); SEC-009 (same code, `sys/SecurityConfig.kt:37`); CMP-004 (same code, `sys/SecurityConfig.kt:37`); RDB-004 (same code, `sys/SecurityConfig.kt:37`).

---

### Test quality (TSQ) — 4/10 · 16 open

Every TSQ major below was confirmed by applying its named mutation to production code in a scratch clone and running `./gradlew test --offline`. "Green" means no failures beyond the 5 baseline failures.

**TSQ-001 · M · isolated — Relay-pair ITs broken by the wall clock since 2026-09-01; they mask the outbox SQL they exist to test**
- `src/test/kotlin/dev/booking/repo/BookingLifecycleIT.kt:45-47` (fixed clock 2026-09-01T08:00Z), `:183`, `:208`; `ddl/01-create-tables.sql:441` (`next_attempt_at DEFAULT now()`); `ddl/03-functions.sql:171`; `sql/outbox/claim_due_events.sql:28`
- Worksheet: reach every relay pass · residue external (mutation 1, never marking dispatched, republishes every event forever) · signal none (the suite is already red, so the regression adds no failure) → major
- Evidence:
  - Root cause confirmed: changing only the default makes both tests pass.
  - Mutation `mark_dispatched.sql:7 → AND false` was green; with the clock fixed it goes red.
  - These are the only real-DB tests of `mark_dispatched`, `record_failure` and `claim_due_events`.
- Narrowed @dc188b7: a new clock-independent test (a 2100 instant) covers `claim_due_events` and `record_failure` against the real database. `mark_dispatched` is still covered only by the red relay pair.
- Cross-ref: CON (app clock vs DB clock).

**TSQ-003 · M · isolated — Capacity release when a booking leaves HELD or CONFIRMED is untested**
- `ddl/03-functions.sql:489-491`. Mutation: release → `PERFORM 1` → green (also with the clock fixed). Worksheet: reach every cancel, decline, expiry and no-show · residue external (permanent capacity leak) · signal none → major.
- Cross-ref: CON-003 (same code, `ddl/03-functions.sql:489`).

**TSQ-004 · M · isolated — Session capacity guard (I2, NF4) untested, sequentially and concurrently**
- `ddl/03-functions.sql:342-353, 589-601, 492-497`; every fixture uses capacity 1. Mutation: drop `WHERE session.booked_count < session.capacity` (`:345`) → green. Worksheet: reach a second booking of a full session · residue external (overbooked) · signal none → major. README "Known gaps" records the missing NF4 test without accepting the consequence.
- Cross-ref: CON-002 (same code, `ddl/03-functions.sql:348`); CON-003 (same code, `ddl/03-functions.sql:589`); CON-004 (same code, `ddl/03-functions.sql:342`); TSQ-016 (same code, `ddl/03-functions.sql:597`); RDB-009 (same code, `ddl/03-functions.sql:597`).

**TSQ-005 · M · isolated — The cancel path, including R6 and R27, has no test**
- `ddl/03-functions.sql:468-481`; `BookingLifecycleService.kt:51-56` is never called by a test. Mutation: R6 check → `IF false` (`:476`) → green. Worksheet: reach a customer cancelling inside the window · residue external · signal none → major.
- Cross-ref: LOG-008 (same code, `ddl/03-functions.sql:473`); RDB-001 (same code, `ddl/03-functions.sql:473`); RDB-005 (same code, `ddl/03-functions.sql:469`); REQ-001 (same code, `ddl/03-functions.sql:468`).

**TSQ-006 · M · isolated — Reschedule (UC8) tests leave capacity release, R6 actor scoping and the deadline clamp unpinned**
- `ddl/03-functions.sql:535-660`; tests at `repo/BookingLifecycleIT.kt` (four reschedule tests since eef5ebc)
- Worksheet: reach any reschedule · residue external (capacity leak or double hold; provider moves refused; a hold outliving its start) · signal none → major
- Mutations, each run in a scratch copy, each green apart from the 2 baseline relay failures:
  - old-session release → `PERFORM 1` (`:579-580` @4781c64)
  - `IF p_actor_type_id = 1 AND b.booking_state_id = 2` → `IF b.booking_state_id = 2` (`:576` @eef5ebc): no provider reschedule of a CONFIRMED booking and no customer reschedule outside the window is tested
  - `LEAST(b.hold_deadline, v_s_starts)` → `b.hold_deadline` (`:627` @eef5ebc): the only HELD test moves to a later start, where the clamp is a no-op
- The `>=` and `>` boundaries and a provider rescheduling a HELD booking are untested.
- Narrowed @eef5ebc: R27, the customer window, the kept deadline and the named resource are now pinned.
- Cross-ref: LOG-001, LOG-002 (resolved).

**TSQ-007 · M · isolated — Tenancy filters in the listing SQL are untested**
- `sql/listing/customer_bookings.sql:19`, `provider_bookings.sql:18`, `booking_contacts.sql:12`; ListingServiceTest stubs the repository. Mutation: `WHERE b.customer_id = :customerId` → `WHERE :customerId IS NOT NULL` → green. Worksheet: reach any customer listing · residue external (cross-customer disclosure) · signal none → major.
- Cross-ref: REQ-008 (same code, `sql/listing/provider_bookings.sql:18`).

**TSQ-008 · M · isolated — Rule expansion in the provider timezone (R14, DST) has no test**
- `ddl/03-functions.sql:46-62`; every fixture uses `'UTC'` (`BookingLifecycleIT.kt:78`, `JdbcBookingRepositoryIT.kt:68`, `ProviderOnboardingIT.kt:86`, `AvailabilityManagementIT.kt:70`). Mutation: `AT TIME ZONE v_tz` → `'UTC'` → green. Worksheet: reach every non-UTC provider · residue external · signal none → major. The README known gap records the missing test and does not credit it.

**TSQ-009 · M · isolated — The wiring tier (ApplicationContextIT) always fails on the default Testcontainers path**
- `src/test/kotlin/dev/booking/ApplicationContextIT.kt:49-50` (`?: error("integration database not configured")`). This contradicts README.md:131 and `TestDatabase.kt:14`. Mutation: remove `@Repository` from JdbcSweepRepository (the worker cannot wire) → green. Worksheet: reach every default test run · residue process (a wiring regression ships, and the worker cannot start) · signal none → major ("suite or large parts disabled").

**TSQ-010 · m · isolated — TestDatabase runs Flyway `clean()` on whatever `BOOKING_TEST_JDBC_URL` names, with no guard**
- `src/test/kotlin/dev/booking/repo/TestDatabase.kt:23, 35, 41-45`, plus per-class `DELETE`s. This needs an operator to point a test-named variable at production, so it falls short of the critical rung.

**TSQ-011 · m · isolated — On the external-DB path, ApplicationContextIT leaves real-clock worker schedulers running against the shared test database**
- `ApplicationContextIT.kt:29, 54, 57`; `WorkerConfig.kt:29`; `TimeAndIdConfig.kt:18`. This is an order-dependent flake mechanism; it was not observed.

**TSQ-012 · m · isolated — Latent adapters untested**
- `GateResolutionListener.parse` (`:46-68`) and `KafkaEventPublisher` are untested; both are on the not-exercised list.

**TSQ-013 · m · isolated — Weak or tautological assertions**
- `ProviderOnboardingIT.kt:180-186` (`runCatching{}.isFailure` passes on any failure); `GatePolicyTest.kt:28-32` asserts nothing.

**Candidates (unverified, not scored)**
- TSQ · M · fn_auto_complete and attendance (BK009) never executed by a test · `ddl/03-functions.sql:660-682, 483-486` — named mutation not run; a green run of e.g. `fn_auto_complete` → no-op would confirm.
- TSQ · M · I4 (no PII in event payload) not asserted · `BookingLifecycleIT.kt:186` — mutation (add `email` to `fn_emit_event` payload) not run.

**TSQ-014 · m · isolated — Route rules are tested against stub controllers that restate the paths**
- Status: open, found @66308b9
- `src/test/kotlin/dev/booking/sys/SecurityConfigTest.kt:41-46` restates `/v1/providers` and the contacts route instead of using `ProviderSetupController.kt:28` and `InternalController.kt:29`. Moving the real contacts route outside `/internal/` leaves the suite green. `jwt()` injects authorities directly, so the scope-claim conversion is not exercised. The real wiring is covered only by ApplicationContextIT, which is red (TSQ-009).

**TSQ-015 · m · isolated — The scheduling test does not pin the pool size to the job count**
- Status: open, found @4bdacf6
- `src/test/kotlin/dev/booking/worker/WorkerSchedulingTest.kt` uses two stand-in jobs, so `JOBS = 2` or a fourth real job stays green. `poolSize = 1` is caught; the author ran that mutation before committing.
- Cross-ref: RDB-007.

**TSQ-016 · M · isolated — The R20 lock protocol is pinned only for create against a BLOCK; the reschedule and end-rule locks are untested**
- Status: open, found @862df06
- `ddl/03-functions.sql:597-598` (reschedule `FOR SHARE`); `sql/management/end_availability_rule.sql:15` (`FOR UPDATE OF res`)
- Worksheet: reach a reschedule or a rule end racing the other side · residue external (a booking stored inside time that was already withdrawn, missing from the R20 list) · signal none → major
- Mutations, each run in a scratch copy: delete the reschedule lock → 86 tests, the 5 baseline failures only; delete the end-rule lock → the same. Both stay green.
- Cross-ref: CON-001 (resolved); TSQ-004 (same code, `ddl/03-functions.sql:597`); RDB-009 (same code, `ddl/03-functions.sql:597`).

**TSQ-017 · m · isolated — The race tests prove "blocked" with a fixed sleep**
- Status: open, found @862df06
- `repo/AvailabilityManagementIT.kt:245-246`, `:285-286`: `Thread.sleep(500)` then `!isDone`. On a slow runner a removed lock could still pass. Polling `pg_stat_activity` for a lock wait would be deterministic.

---

### Type & null safety (TYP) — 9/10 · 2 open

**TYP-001 · m · isolated — JSON `null` in a gate resolution reads as "", so null message ids collide in dedupe (latent)**
- `worker/GateResolutionListener.kt:49-51, 57, 65` (Jackson 3 `NullNode.asString()` returns ""). No producer exists.

**TYP-002 · m · widespread — Authority-bearing identifiers passed as raw String/UUID**
- IdP subjects as bare `String`: `BookingLifecycleService.kt:39/51`, `BookingDomain.kt:70-71`, `BookingPorts.kt:42,51,61`.
- Sibling UUID refs: `ProviderSetup.kt:82-87`, `AvailabilityPorts.kt:11-17`.
- `GateResolutionService.kt:61` writes `messageId` into `actorSubject`. No swapped call site was found.

---

### Readability & maintainability (RDB) — 9/10 · 9 open

**RDB-001 · m · isolated — Hard-coded lookup ids in plpgsql**
- `ddl/03-functions.sql:67, 72, 261, 357, 360, 473, 502-504, 604, 606, 650, 676, 678`. Drift risk is settled by `04-seed-lookups.sql:1-2`; only readability remains.
- Cross-ref: LOG-008 (same code, `ddl/03-functions.sql:473`); PAT-002 (same code, `ddl/03-functions.sql:604`); CON-003 (same code, `ddl/03-functions.sql:650`); TSQ-005 (same code, `ddl/03-functions.sql:473`); RDB-005 (same code, `ddl/03-functions.sql:473`); REQ-001 (same code, `ddl/03-functions.sql:473`); REQ-003 (same code, `ddl/03-functions.sql:676`).

**RDB-002 · m · isolated — Take, deadline and event mapping duplicated between fn_create_booking and fn_reschedule_booking**
- `ddl/03-functions.sql:336-354` vs `:582-601`; `:363-368` vs `:607-611`; `:384, 389` vs `:519-526, 628`.
- Wider @862df06: the R20 resource lock and its comment are a third piece duplicated between create (`ddl/03-functions.sql:327-332`) and reschedule (`:597-598`).
- Cross-ref: REQ-003 (same code, `ddl/03-functions.sql:519`).

**RDB-003 · m · isolated — Default values stated twice**
- DDL defaults (`ddl/01:96-100, 161-164`) restated in `sql/management/insert_provider.sql:9-13` and `insert_service.sql:6-9`; `Page.first` (`core/listing/Listing.kt:43`) restated in `api/ListingController.kt:27-28, 41-42`.

**RDB-004 · m · isolated — The `SCOPE_` authority prefix is restated in main and in the test**
- Status: open, found @66308b9
- `sys/SecurityConfig.kt:37-38`, `src/test/kotlin/dev/booking/sys/SecurityConfigTest.kt:57`: an unnamed convention written in two places.
- Cross-ref: ERR-008 (same code, `sys/SecurityConfig.kt:37`); SEC-009 (same code, `sys/SecurityConfig.kt:37`); CMP-004 (same code, `sys/SecurityConfig.kt:37`); LGG-006 (same code, `sys/SecurityConfig.kt:37`).

**RDB-005 · m · isolated — The R27 and R6 predicates are written twice**
- Status: open, found @eef5ebc
- `ddl/03-functions.sql:569-583` (reschedule) restates `:469-480` (cancel). A change to the window rule has to be made in both places.
- Cross-ref: LOG-008 (same code, `ddl/03-functions.sql:473`); CON-003 (same code, `ddl/03-functions.sql:579`); TSQ-005 (same code, `ddl/03-functions.sql:469`); RDB-001 (same code, `ddl/03-functions.sql:473`); REQ-001 (same code, `ddl/03-functions.sql:469`); REQ-018 (same code, `ddl/03-functions.sql:571`).

**RDB-006 · m · isolated — Second-resource test setup hard-codes the fixture date**
- Status: open, found @eef5ebc
- `repo/BookingLifecycleIT.kt`, the named-resource test, repeats `DATE '2026-09-02'` instead of deriving it from `slot`.

**RDB-007 · m · isolated — The scheduler pool size is hand-counted against the scheduled jobs**
- Status: open, found @4bdacf6
- `worker/WorkerScheduling.kt:32-34` (`JOBS = 3`) against the three `@Scheduled` methods in `worker/WorkerSchedules.kt`. A fourth job would share the three threads, and nothing would flag it.

**RDB-008 · m · isolated — The `max.block.ms` comment claims a bounded relay pass the code does not give**
- Status: open, found @4bdacf6
- `application.yaml:33-36`: `max.block.ms` bounds only `send()`. `KafkaEventPublisher.kt:37-38` then waits up to 10 s more on `get()`, and `OutboxRelay` runs up to 100 sends in sequence, so a pass has no overall bound. The 10000 also restates `send-timeout-seconds` as a second literal.

**RDB-009 · m · isolated — `fn_assert_bookable`'s lock precondition is stated only in its callers**
- Status: open, found @862df06
- `ddl/03-functions.sql:327-332`, `:597-598`. The function is STABLE and cannot lock, and its `COMMENT ON FUNCTION` does not say that callers must take the resource lock first.
- Cross-ref: TSQ-004 (same code, `ddl/03-functions.sql:597`); TSQ-016 (same code, `ddl/03-functions.sql:597`).

---

### Requirements alignment (REQ) — 0/10 · 19 open

**REQ-001 · C · isolated — Provider cancellation accepted without a reason (R7, UC7)**
- `api/BookingDtos.kt:35`; `api/BookingController.kt:69-76`; `core/booking/BookingLifecycleService.kt:51-56`; `ddl/03-functions.sql:468-481, 500-516`; the column comment at `ddl/01:397` claims "mandatory … (R7)" but nothing enforces it
- Worksheet: reach provider admin POSTing `/cancel` with no body · residue external (a CANCELLED booking with a NULL reason in append-only history) · signal none → critical
- Requirement: R7 "must supply a reason"; UC7 "The resulting record states who cancelled and why."
- Cross-ref: LOG-008 (same code, `ddl/03-functions.sql:473`); TSQ-005 (same code, `ddl/03-functions.sql:468`); RDB-001 (same code, `ddl/03-functions.sql:473`); RDB-005 (same code, `ddl/03-functions.sql:469`).

**REQ-002 · C · widespread — Undispatched events are neither observable nor alertable (NF11)**
- `core/outbox/OutboxRelay.kt:33-48` (comment `:36-37` claims "attemptCount drives the NF11 alert"); `sql/outbox/record_failure.sql:1-2`; `application.yaml:58-62` exposes prometheus with no registry dependency in `build.gradle.kts:25-48`; there is no gauge or metric
- Worksheet: reach any broker outage or persistently failing event · residue external (lifecycle events withheld for an unbounded time; the booking's later events blocked) · signal none (no alerting, domain-context §7) → critical
- Requirement: NF11 "sustained lag or repeated dispatch failure raises an alert rather than accumulating silently". There is no known-gap marker; the code claims the alert exists.
- Cross-ref: ERR; SEC-006 (same code, `application.yaml:58`).

**REQ-003 · C · isolated — BookingCompleted does not distinguish system auto-completion from a provider's mark (UC12)**
- `ddl/03-functions.sql:179-195` (payload has no completion source), `:519-526`, `:676-678`
- Worksheet: reach every completion (an outbox row is written each time) · residue external (indistinguishable events) · signal none → critical
- Requirement: UC12 "The record and the event distinguish …". The record half is met; the event half is not.
- Cross-ref: CMP (draft topic); RDB-001 (same code, `ddl/03-functions.sql:676`); RDB-002 (same code, `ddl/03-functions.sql:519`).

**REQ-004 · C · isolated — No erasure, export or retention for customer data (NF5)**
- `customer.erased_at` (`ddl/01-create-tables.sql:206`) is read (`booking_contacts.sql:8`) but never written. There is no export or erasure endpoint and no retention job.
- Worksheet: reach any erasure or export request, and every customer 24 months after their last booking · residue external (PII kept and cannot be erased) · signal none → critical
- Requirement: NF5 "Export and erasure on request must be possible." PD9 leaves open only the period. Domain-context §4 states the absence as a fact and does not accept it.
- Cross-ref: SEC.

**REQ-005 · M · isolated — Search results do not state the provider timezone (UC4)**
- `api/BookingDtos.kt:48-57`; `api/AvailabilityController.kt:37-45`. Worksheet: reach every search · residue request · signal none → major.

**REQ-006 · M · isolated — Availability search requires a token; the requirements make it public (UC4, §3)**
- `sys/SecurityConfig.kt:26-27`; `api/AvailabilityController.kt:23`. Worksheet: reach any anonymous browser · residue request (401) · signal caller → major. No ruling marks the deviation as known.
- Cross-ref: SEC; SEC-006 (same code, `sys/SecurityConfig.kt:26`).

**REQ-007 · M · isolated — A "no preference" booking of an unavailable time is rejected as R19 with 404 (UC5, NF8)**
- `core/booking/BookingService.kt:43-47`; `core/booking/BookingDomain.kt:55`; `api/BookingOutcomeResponder.kt:122`. Worksheet: reach a no-preference create at a full or unpublished time · residue request · signal caller (wrong rule) → major.

**REQ-008 · M · isolated — Provider calendar cannot be filtered by resource or state (UC10)**
- `api/ListingController.kt:36-43`; `core/listing/ListingService.kt:29-39`; `sql/listing/provider_bookings.sql:18-20`. Worksheet: request · none → major.
- Cross-ref: TSQ-007 (same code, `sql/listing/provider_bookings.sql:18`).

**REQ-009 · M · isolated — No transition history is exposed anywhere (UC10)**
- `api/BookingDtos.kt:72-82`; no single-booking read; `booking_transition` is never read. Worksheet: request · none → major.

**REQ-010 · M · isolated — A resource-linked subject gets no read access (R24, UC10)**
- `api/BookingDtos.kt:140-141`; `repo/JdbcProviderSetupRepository.kt:51`; `resource.idp_subject` is read by nothing. Worksheet: reach any linked subject (linking is reachable) · residue request · signal none → major.

**REQ-011 · M · isolated — Resources and services cannot be deactivated or edited (§4.2, R19)**
- `api/ProviderSetupController.kt:28-86` (create and link only); `is_active` is never written (`ddl/01:101,140,165`). Worksheet: request · none → major.

**REQ-012 · m · widespread — No metrics by outcome or rule, and no trace propagated through events (NF7)**
- No Micrometer meter; no tracing dependency; the envelope at `worker/KafkaEventPublisher.kt:31-43` carries no trace context. Cross-ref LGG-005.

**REQ-013 · m · isolated — Several rules share the label "section 4.1" (NF8)**
- `core/booking/BookingDomain.kt:53` (BK006 for R27, UC6 and R28).

**REQ-014 · m · isolated — Reschedule validated with current service values, not the booking's snapshot (R10, R25; latent, as no API edits a service)**
- `ddl/03-functions.sql:572-588`, `:237-242`.

**REQ-015 · m · isolated — Idempotency-Key is optional**
- `api/BookingController.kt:37` (`required = false`); architecture-design.md:243 says it is required.

**REQ-016 · m · isolated — Unrequested `slotStepMinutes` (default 15) shapes offered starts**
- `api/BookingDtos.kt:150`; `sql/management/insert_service.sql:9`; `ddl/03-functions.sql:128`.
- Cross-ref: LOG-007 (same code, `ddl/03-functions.sql:128`).

**REQ-017 · m · isolated — The design documents and comments still describe the old access rules, and the scope names appear nowhere else**
- Status: open, found @66308b9
- `core/management/ProviderSetup.kt:46-52` (the creating subject becomes the first admin; nothing says a scope is required); domain-context §6 I5 and §7 hazards ("not enforced", "no authorization check"); `docs/backend-design/architecture-design.md:256` (service-to-service auth).
- An operator reading the documents cannot learn which scopes to issue.
- Cross-ref: SEC-009.

**REQ-018 · m · isolated — The reschedule window rule exists only in a SQL comment**
- Status: open, found @eef5ebc
- `ddl/03-functions.sql:571-583`: a customer may not reschedule a CONFIRMED booking inside the R6 window. UC8 and requirements §4.1 do not state it.
- Cross-ref: LOG-008; CON-003 (same code, `ddl/03-functions.sql:579`); RDB-005 (same code, `ddl/03-functions.sql:571`).

**REQ-019 · m · isolated — The data design still says availability edits take no lock**
- Status: open, found @862df06
- `docs/backend-design/data-design.md:441` says UC2 and UC3 are "Plain DML, single statement, no locking". The R20 lock protocol added at 862df06 is documented only in SQL comments.

## Credited as intentional (recorded to prevent re-litigation)

- Outbox at-least-once delivery: an unlocked claim, a republish after a lost ack or a timed-out send, and duplicates across relays. Evidence: `claim_due_events.sql:6-10` and domain-context §7 ("consumers must dedupe on eventId"). This covers duplicates only, not reordering (LOG-003).
- The outbox never drops an event: the row is retained, the error recorded, and backoff capped at 5 min (`OutboxRelay.kt:9-12`, domain-context §7). Escalation is a separate matter (REQ-002).
- The Idempotency-Key is optional, so a keyless retry creates a new booking (`ddl/01-create-tables.sql:394`, R15). REQ-015 records the deviation from the design document only.
- The customer profile commits before the booking; provisioning on first use is idempotent (`BookingPorts.kt:46-61`, `upsert_customer.sql:1-4`).
- Both sweeps run on every replica, with SKIP LOCKED and re-evaluation under lock (`Sweeps.kt:7-9`, `ddl/03:640-648`, domain-context §4). This does not cover the deadlock exposure (CON-003).
- Lookup ids are stable and never renumbered (`04-seed-lookups.sql:1-2`); RDB-001 is kept for readability only.
- Client contact details fill only the gaps the token leaves (domain-context §5, owner-confirmed).

## Resolved findings (archive)

One line per resolved finding — `<ID> · <C|M|m> · <title> · <files> ·
resolved @<hash>`; full bodies live in this document's git history. A
reintroduced defect reopens its ID here (moves back to Open findings with
`reopened @<hash>`), never gets a new one.

- SEC-001 · C · Internal contacts endpoint serves any booking's customer PII to any token holder (I5 violated) · `api/InternalController.kt`, `core/listing/ListingService.kt`, `repo/JdbcListingRepository.kt` · resolved @66308b9
- SEC-002 · C · `POST /v1/providers` has no authorization and makes the caller the first admin (owner declined, domain-context §7) · `api/ProviderSetupController.kt`, `core/management/ProviderSetup.kt`, `sql/management/insert_provider.sql` · resolved @66308b9
- LOG-001 · C · Reschedule never checks the original start, so R27 (and the R6 window) can be bypassed · `docs/backend-design/ddl/03-functions.sql`, `04-seed-lookups.sql` · resolved @eef5ebc
- LOG-002 · C · Rescheduling a HELD booking renews its hold deadline · `ddl/03-functions.sql`, `core/booking/GatePolicy.kt` · resolved @eef5ebc
- LOG-005 · C · Reschedule accepts `resourceRef` on the wire and silently drops it · `api/BookingDtos.kt`, `api/BookingController.kt`, `ddl/03-functions.sql` · resolved @eef5ebc
- LOG-003 · C · Outbox claim applies backoff before picking each booking's oldest event, so N+1 is published while N waits · `src/main/resources/sql/outbox/claim_due_events.sql`, `record_failure.sql`, `core/outbox/OutboxRelay.kt` · resolved @dc188b7
- LOG-004 · C · Ending a rule with no body sets effective_until to today's UTC date, not the provider's local date · `api/AvailabilityAdminController.kt`, `ddl/03-functions.sql` · resolved @dc188b7
- PAT-003 · m · Clock-derived policy default computed in the controller · `api/AvailabilityAdminController.kt`, `sys/TimeAndIdConfig.kt` · resolved @dc188b7
- TSQ-002 · M · Per-booking event ordering has no test · `sql/outbox/claim_due_events.sql` · resolved @dc188b7
- ERR-001 · C · A broker outage starves the hold-expiry and auto-complete sweeps: all three jobs share one scheduler thread · `worker/WorkerSchedules.kt`, `application.yaml`, `core/outbox/OutboxRelay.kt` · resolved @4bdacf6
- CON-001 · C · An availability edit racing a create stores a booking inside blocked time and omits it from the R20 conflict list · `core/management/AvailabilityManagement.kt`, `ddl/03-functions.sql`, `sql/management/availability_conflicts.sql` · resolved @862df06

## History

| Date | Hash | LOG | ERR | SEC | PAT | CON | CMP | LGG | TSQ | TYP | RDB | REQ | Worst | Avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-17 | 4781c64 | 0 | 3 | 2 | 6 | 3 | 5 | 9 | 4 | 9 | 9 | 0 | LOG, REQ (0) | 4.5 |
| 2026-10-17 | 66308b9 | 0 | 3 | 4 | 6 | 3 | 5 | 9 | 4 | 9 | 9 | 0 | LOG, REQ (0) | 4.7 |
| 2026-10-17 | eef5ebc | 2 | 3 | 4 | 6 | 3 | 5 | 9 | 4 | 9 | 9 | 0 | REQ (0) | 4.9 |
| 2026-10-17 | dc188b7 | 4 | 3 | 4 | 6 | 3 | 5 | 9 | 4 | 9 | 9 | 0 | REQ (0) | 5.1 |
| 2026-10-17 | 4bdacf6 | 4 | 4 | 4 | 6 | 3 | 5 | 9 | 4 | 9 | 9 | 0 | REQ (0) | 5.2 |
| 2026-10-17 | 862df06 | 4 | 4 | 4 | 6 | 4 | 5 | 9 | 4 | 9 | 9 | 0 | REQ (0) | 5.3 |

Per-aspect baselines (diff basis for the next incremental review): LOG, ERR, SEC, PAT, CON, CMP, LGG, TSQ, TYP, RDB, REQ @ 862df06, whole repo.
