Sample-data versions of the hub pages, rendered only in the static preview build (`PREVIEW=1`, see
`.github/workflows/pages.yml`). Normal builds show the route placeholders until each page reads from the API.

- `/` is the public landing page (`$lib/Landing.svelte`, copy in `$lib/landing.ts`), the same in every build apart
  from the guild pulse, which only the preview draws from the sample raid sheets. `/how-we-raid` has the raid night
  model in full, `/toolkit` what each tier can do (`$lib/access.ts`), and `Story` and `Recruit` the rest of the public
  face; everything else opens after sign-in. `/welcome` is the first sign-in checklist (`$lib/welcome.ts`), and
  `/admin` the super admins' console (`$lib/admin.ts`, with the bank's grants answered by `bank-fake.ts`).
- `Hub` is the customisable home: `$lib/components/HomeView.svelte` draws the member's widgets in their order and the
  customiser. Hub widgets use the mock data; analyzer widgets draw `$lib/mock/analyzer.ts`, a sample in the analyzer's
  home page contract (`$lib/home-payload.ts`), including the officers' badge roster from `$lib/mock/badges.ts`,
  which also gives Hopscotch's own badges on `Me`. The `flasks` table (off by default; place it with Customise) follows wcl_app.home's `flasks` widget. `Officers` is the officer view.
- The preview opens signed out on the landing page. Its "Log in with Discord" goes to a pretend sign-in at `/login`
  (preview only; the real site answers 404 there) where the visitor picks the raider, the officer or the super admin view.
  `session.svelte.ts` keeps the choice in localStorage; the top bar switches views and logs out, and the layout uses
  `gate.ts` to ask signed-out visitors to sign in on member pages and to keep raiders out of the officer console.
- Data comes from `$lib/mock/data.ts` and `$lib/mock/community.ts`. The preview visitor is Hopscotch, who raids both
  nights: the raider view has no officer powers, the officer view is Wednesday's raid leader, and the super admin view
  is a global officer who also manages bank grants and officer tokens. The e2e suite signs in with
  `e2e/auth.ts`.
- `Bank` is the real bank page (`$lib/components/BankLive.svelte`) answered by `bank-fake.ts`, an in-memory stand-in for
  the hub's bank routes installed with `useBankFetch`. The officer view works Wednesday's request queue and imports; the
  super admin view also sees grants, officer tokens and the break-glass notice, and a token minted there can be
  redeemed in the raider view. The state lasts until the page reloads.
- `state.svelte.ts` holds in-memory copies of the community data and the preview visitor's home layout. Officer actions, spotlight consent and the compose
  form change only that state (kept across client-side navigation, reset on reload); nothing is sent anywhere, and the
  recruit form only shows its success message.
- The logic these pages use (`clips`, `posts`, `recruitment`, `application`, `progression`) lives in `$lib` with unit
  tests, so the API-backed pages can reuse it. `npm run e2e` runs Playwright against this preview build.
