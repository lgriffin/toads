# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Members of the Toads guild (a Warcraft raiding guild), in three roles. The user gave no preference on who is primary, so this is inferred from the repo and the weighting is open:
- Raiders: log in with Discord, check how each raid went for them against the guild's median for their role, browse raids and screenshots, request items from the guild bank.
- Officers and raid leaders: run the raid leader desk and Officers console, approve or reject character claims, review applications, curate posts.
- Recruits and the public: read the Story, Recruit and Highlights pages and apply.

## Product Purpose
The guild's web hub. It turns Warcraft Logs analysis (WCL Analyzer, `wcl-core` / `wcl-store`) into something each member can read about their own play, and puts the guild's bank, raid schedule, applications and community posts in one Discord-authenticated place.

## Positioning
Per-role median comparison: each raider sees how a raid went for them against the guild's median for their role. A generic guild site or a raw Warcraft Logs page cannot show that, because it depends on the guild's own analysis and role overrides.

## Operating Context
- Sign-in is Discord OAuth2 with Redis sessions; roles come from Discord and drive RBAC with raid-day scoping.
- Backend is a FastAPI Hub API over Postgres (wcl-store + hub-db), with an RQ worker, a Discord bot, and the ToadsBank adapter. See `README.md` and `docs/`.
- The web app is SvelteKit; a Pages preview runs on sample data.

## Capabilities and Constraints
- Public pages: Story, Recruit, Highlights. Inward pages: Hub (posts feed, raid leader desk), Officers console, Raids & Logs, Bank, Me.
- Character claims, applications with private Discord interview rooms, consent-gated spotlights, highlight reels.
- Zone progress and the claim flow's character list wait on wcl-store (`POST /api/claims` answers 404 until then).
- Unconfirmed: which audience the design should optimize for first.

## Evidence on Hand
- Sample data under `apps/web/src/lib/mock/` is for the Pages preview only. Real stats, testimonials and progress claims must not be fabricated.

## Product Principles
- Show each member their own play first, against a fair role-based yardstick.
- Discord is identity: access follows Discord roles, and the interface never exposes more than a role allows.
- Spotlights and personal data are consent-gated.
- Sample data is labelled as sample.

## Accessibility & Inclusion
Accessibility is enforced: Playwright e2e runs axe on pages in CI, and new work must stay axe-clean (target WCAG 2.1 AA).
