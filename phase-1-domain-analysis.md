# User Service — Phase 1: Domain Analysis and Requirements

**Service:** user-service
**Phase:** 1 (analysis only: no code, no database, no migrations)
**Status:** Draft, awaiting review and approval
**Depends on:** `docs/phase-0-conventions.md`

## 1. Purpose and method

This document defines the User domain before implementation. It contains the four deliverables required by the roadmap: a domain glossary (section 2), a responsibility matrix (section 3), an initial use-case list (section 4) and an open decisions document (section 6). Sections 5 and 7 cover the lifecycle and the remaining scope items.

**Method.** Everything below comes from the master specification (`aida-readme.md`), the Phase 0 conventions and the Auth Service code and docs. No product requirement is invented. Where the specification says a decision is needed, the item is listed in section 6 with its options and consequences, and **no answer is chosen**.

Marking used in this document:

- **[Spec]** stated in `aida-readme.md`.
- **[Auth]** observed in the Auth Service or its docs.
- **[Open]** undecided; see section 6.

## 2. Domain glossary

| Term | Meaning in NextMinds User Service |
|---|---|
| **Account** | An authenticated identity owned by Auth Service: login identifiers (username or email), credentials, status, roles. [Auth] |
| **Auth user id** | The UUID Auth generates for an account. It appears as `sub` in the access token. [Auth] |
| **User profile** | Personal, non-credential information about a person, owned by User Service: first name, last name, display name, avatar reference, birth date. [Spec] |
| **Profile owner** | The account whose Auth user id matches the profile. Ownership comes from the authenticated token, never from the request body. [Spec] |
| **Role** | An authorization label (`ROLE_USER`, `ROLE_ADMIN`) owned by Auth. It is not a business identity. [Spec, Auth] |
| **Business identity** | What a person is in the product (student, parent, school representative). Different from a role and not automatically part of the profile. [Spec] |
| **Display name** | Optional name shown instead of the full name. Length limit and fallback rule are undecided. [Spec, Open] |
| **Avatar reference** | A URL or storage key for a profile image. No binary data is stored. Upload is out of scope. [Spec] |
| **Birth date** | Date-only value, treated as personal information, cannot be in the future. Whether it is mandatory is undecided. [Spec, Open] |
| **Profile completion** | A value calculated from explicit business rules (which fields are present and valid). Not a manually stored flag. [Spec] |
| **Profile visibility** | Server-side rule saying who may see which profile fields. Candidate levels: `PRIVATE`, `PUBLIC`, `AUTHENTICATED_USERS`. [Spec, Open] |
| **User preferences** | User-specific settings (locale, timezone, theme). A later phase. [Spec] |
| **Administrator** | An account holding `ROLE_ADMIN`, assigned by Auth. User Service does not manage roles. [Spec, Auth] |
| **Gateway** | Public entry point. Validates the access token and routes `/api/v1/users/**` to User Service. [Phase 0] |
| **Soft delete** | Marking an account as deleted without removing the row. Auth does this for accounts (`deleted_at`). Whether profiles follow is undecided. [Auth, Open] |

## 3. Responsibility matrix

Legend: **Owner** = source of truth. **Not here** = must not be implemented or stored in User Service.

| Information / capability | Auth | User | Other / future |
|---|---|---|---|
| Account id (UUID) | Owner | Reference only (same value, not generated here) | |
| Login identifiers (username, email) | Owner | Not here (unless a business requirement says otherwise) | |
| Passwords, hashes, reset tokens | Owner | Not here | |
| Access and refresh tokens | Owner | Not here (validates the access token only) | |
| Roles and permissions | Owner | Not here (reads roles from the token) | |
| Account status (`ACTIVE`, `SUSPENDED`, ...) | Owner | Not here (reacts only if an integration is agreed) | |
| Login history | Owner | Not here | |
| First name, last name | | Owner | |
| Display name | | Owner | |
| Avatar reference | | Owner | |
| Birth date | | Owner | |
| Profile completion | | Owner (calculated) | |
| Profile visibility / privacy settings | | Owner | |
| User preferences | | Owner (later phase) | |
| Parent-child relationships | | Not here | Future domain |
| Student-school relationships, enrollment | | Not here | School domain |
| School entities and information | | Not here | School domain |
| Academic and educational records | | Not here | Educational services |
| Payments | | Not here | Payment service |
| Notification delivery | | Not here | Notification service |
| National ID, home address, gender, marital status | | Not here without explicit requirement | |

Rules that follow from the matrix: User Service never creates an identity, never stores credentials, never manages roles, never reads the Auth database, and other services reach profile data only through an API or an agreed integration, never through the User database. [Spec]

## 4. Initial use-case list

Each use case lists the actor and the source. Items marked [Open] depend on a decision in section 6. Use cases beyond the MVP are listed so the boundary is visible; they must not be implemented early.

### 4.1 Profile creation scenarios

| ID | Use case | Actor | Notes |
|---|---|---|---|
| UC-C1 | Create a profile for an authenticated account | Account owner | The profile id is the Auth user id from the token. Creating a second profile for the same account must be handled (conflict or idempotent). [Open: Q1, Q3] |
| UC-C2 | Create the profile as part of registration | System | Flow not decided: REST orchestration, event, or client orchestration. [Open: Q2] |
| UC-C3 | Reject creation with invalid data | System | Validation errors use the RFC 9457 format of Phase 0. Mandatory fields are undecided. [Open: Q5, Q6] |

### 4.2 Profile retrieval scenarios

| ID | Use case | Actor | Notes |
|---|---|---|---|
| UC-R1 | Get my profile (`GET /api/v1/users/me`) | Account owner | Defined in the specification. In MVP. |
| UC-R2 | Handle "account has no profile yet" | System | Behavior undecided (404 or empty profile). [Open: Q4] |
| UC-R3 | View another user's profile | Authenticated user | Depends on visibility rules. [Open: Q7, Q8] |
| UC-R4 | Provide permitted profile data to another service | Service | Through an explicit API contract only. [Open: Q12] |
| UC-R5 | Administrator lists or views profiles | Administrator | Paginated; fields visible to admins undecided. Not in MVP. [Open: Q10] |

### 4.3 Profile update scenarios

| ID | Use case | Actor | Notes |
|---|---|---|---|
| UC-U1 | Update my profile | Account owner | In MVP. Full replace versus partial update undecided; optimistic locking (`version`) only if the strategy needs it. [Open: Q11] |
| UC-U2 | Attempt to change someone else's profile | Account owner | Must be impossible: ownership comes from the token. |
| UC-U3 | Administrator edits a profile | Administrator | Not in MVP. Which fields are editable is undecided. [Open: Q10] |
| UC-U4 | Update timestamps automatically | System | `createdAt` and `updatedAt` are never client-editable. |

### 4.4 Visibility, completion, privacy (post-MVP)

| ID | Use case | Notes |
|---|---|---|
| UC-V1 | Read and change my profile visibility | Not in MVP. [Open: Q7, Q8] |
| UC-P1 | Read my profile completion (status, missing fields, optional percentage) | Not in MVP. Calculated centrally from explicit rules. [Open: Q5, Q9] |
| UC-P2 | Read and change my preferences (locale, timezone, theme) | Not in MVP. Fields depend on product requirements. |

### 4.5 Lifecycle use cases

| ID | Use case | Notes |
|---|---|---|
| UC-L1 | Account deleted in Auth | Effect on the profile undecided. [Open: Q13] |
| UC-L2 | Account disabled or suspended in Auth | Effect on the profile undecided. [Open: Q13] |
| UC-L3 | Delete my profile | Deletion and retention behavior must be defined. [Open: Q13] |

## 5. Lifecycle, privacy and boundaries

### 5.1 Initial user lifecycle (proposed shape, no decisions)

1. An account is created in Auth (status `PENDING_VERIFICATION`, role `ROLE_USER`). [Auth]
2. A profile is created for that account (how and when: Q2).
3. The profile is read and updated by its owner.
4. The account may become `ACTIVE`, `INACTIVE` or `SUSPENDED`, or be soft-deleted in Auth. [Auth] What happens to the profile is Q13.

### 5.2 Privacy requirements [Spec]

- Store only information the product needs.
- Birth date is personal information.
- Restrict private fields; enforce visibility on the server, never only in the client.
- Do not expose internal identifiers unnecessarily.
- Do not log sensitive user data.
- Define deletion and retention.
- Control administrative access using Auth and Gateway rules, not a second role mechanism.

### 5.3 Future student and parent requirements

The platform will serve students, parents and schools. Student academic data, parent-child relationships and school enrollment do not belong in User Service and need their own domain analysis. User Service may later provide profile information for those users. Nothing here models them. [Spec]

### 5.4 School-related boundaries

A school is an organization, not a user profile. A school representative is a user associated with a school. No school business data is stored in User Service. The link between accounts and schools is defined when the School domain is designed. [Spec]

### 5.5 Relationship to existing code (observation only)

The current `user-service` module has a profile with `authUserId`, first name, last name and date of birth, and an age rule (8 to 16). The specification proposes a different shape (`id` equal to the Auth id, `displayName`, `avatarReference`, optional `version`, no age rule). Differences are decided in Phase 2, not here (see Q1 and Q14).

## 6. Open decisions document

For each question: the ambiguity, the affected domain, the options, the consequences, and who must decide. No option is chosen.

### Q1. Can one person have multiple profiles?

- **Affects:** profile identity, database key, Auth link.
- **Option A, one profile per account.** The profile id equals the Auth user id; simple ownership.
  Consequence: a person with several business roles shares one profile.
- **Option B, several profiles per account.** Needs a separate profile id and a selection mechanism.
  Consequence: conflicts with the rule "profile UUID = Auth UUID"; ownership checks become harder.
- **Decision needed from:** product owner.

### Q2. Which service owns the registration and profile-creation workflow?

- **Affects:** integration with Auth.
- **Option A, REST orchestration.** One component calls Auth, then User. Consequence: a failure between the two calls leaves an account without a profile; retries and compensation needed.
- **Option B, event-driven.** Auth publishes a "user created" event and User consumes it. Consequence: new infrastructure (a message broker), which needs approval; eventual consistency.
- **Option C, client orchestration.** The client registers, then creates the profile. Consequence: no new infrastructure, but the profile may never be created and the client must handle failures.
- **Decision needed from:** project lead and architect.

### Q3. How are duplicate profile-creation requests handled?

- **Affects:** UC-C1.
- **Options:** reject with a conflict error, or return the existing profile (idempotent).
- **Consequence:** idempotent creation is friendlier to retries but hides client mistakes.

### Q4. Can an account exist without a profile?

- **Affects:** UC-R2, onboarding.
- **Option A, yes.** `GET /me` returns not found until the profile is created.
- **Option B, no.** A profile is created automatically with the account (ties to Q2).
- **Consequence:** A pushes work to the client; B needs integration.

### Q5. Which profile information is mandatory at initial onboarding?

- **Affects:** validation, completion rules.
- **Candidates from the specification:** first name, last name; birth date is not mandatory unless the product requires it.
- **Consequence:** the mandatory set defines the completion rule and creation validation.

### Q6. Length limits and format rules for names and display name

- **Affects:** validation and database column sizes.
- **Needed:** maximum lengths, allowed characters (Persian and Latin names), display-name fallback.
- **Decision needed from:** product owner.

### Q7. Can users make their profile publicly visible?

- **Affects:** privacy model, API for other users.
- **Options:** all profiles private; or visibility levels `PRIVATE`, `PUBLIC`, `AUTHENTICATED_USERS`.
- **Consequence:** public visibility needs a read path for other users and server-side field filtering; children are among the platform users, so default values matter.

### Q8. Which fields are visible to others and which only to the owner?

- **Affects:** response DTOs per audience.
- **Consequence:** at least two response shapes (owner view, other-user view).

### Q9. Does a user need a completed profile before using the platform?

- **Affects:** onboarding and access rules.
- **Options:** no restriction; or restriction enforced by another service/Gateway using the completion result.
- **Consequence:** User Service must not decide authentication or access on its own.

### Q10. Administrator access

- **Affects:** admin API (`/api/v1/admin/users`).
- **Needed:** which fields an admin can read and change; whether admins can edit profiles at all.
- **Rule:** uses Auth roles; no second role system.

### Q11. Update strategy

- **Affects:** UC-U1.
- **Options:** full replace (`PUT`) or partial update (`PATCH`); optimistic locking with `version` or not.
- **Consequence:** `PATCH` needs rules for "absent field versus null"; locking prevents lost updates but adds a field.

### Q12. How do other services obtain profile data?

- **Affects:** integration contract.
- **Options:** a REST endpoint for service callers; or none until a service needs it.
- **Consequence:** avoid synchronous calls everywhere; only services that really need it depend on User Service.

### Q13. Account deletion, disabling and profile retention

- **Affects:** lifecycle, privacy.
- **Questions:** What happens to the profile when the account is deleted or suspended? Can a user delete only the profile? How long is data retained?
- **Options:** hard delete the profile; soft delete; anonymize; keep unchanged.
- **Consequence:** depends on the integration chosen in Q2 and on legal and privacy requirements.

### Q14. Age rule and the target age range

- **Affects:** validation of birth date.
- **Observation:** the existing code enforces 8 to 16; the specification only says birth date must not be in the future and not mandatory by default.
- **Question:** is the age range a profile rule, or an onboarding rule of another domain?
- **Decision needed from:** product owner.

### Q15. Can a person be both a parent and a student, or represent several schools? (spec questions 2 to 5)

- **Affects:** business identity modelling.
- **Position of this document:** these relationships do not belong in User Service. They are recorded here so the School and relationship domains answer them.
- **Decision needed from:** the future School and relationship domain analysis.

## 7. Coverage of the Phase 1 scope list

| # | Scope item | Where |
|---|---|---|
| 1 | Meaning of a user profile | 2 (Glossary) |
| 2 | Auth identity and profile relationship | 2, 3 |
| 3 | Information owned by User Service | 3 |
| 4 | Information owned by other services | 3 |
| 5 | Initial user lifecycle | 5.1 |
| 6 | Profile creation scenarios | 4.1 |
| 7 | Profile update scenarios | 4.3 |
| 8 | Profile retrieval scenarios | 4.2 |
| 9 | Profile visibility requirements | 4.4, Q7, Q8 |
| 10 | Profile completion requirements | 4.4, Q5, Q9 |
| 11 | Privacy requirements | 5.2 |
| 12 | Future student and parent requirements | 5.3 |
| 13 | School-related boundaries | 5.4 |
| 14 | Unresolved product decisions | 6 |

## 8. Phase completion report

- **Phase:** 1, Domain Analysis and Requirements.
- **Summary:** glossary, responsibility matrix, use-case list and open decisions document produced.
- **Files added:** `user-service/docs/phase-1-domain-analysis.md` (this file).
- **Files modified:** none.
- **Domain decisions:** none. Q1 to Q15 are open.
- **Architectural decisions:** none.
- **Deferred requirements:** everything marked [Open].
- **Dependencies on future phases:** Q1, Q6, Q14 before Phase 2 (domain model); Q5, Q6 before Phase 3 (database); Q2, Q3, Q4 before Phase 9 and 17; Q7, Q8 before Phase 13; Q10 before Phase 16; Q13 before Phase 17.
- **Changes to approved scope:** none.

Waiting for explicit approval before starting Phase 2.
