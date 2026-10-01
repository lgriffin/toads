Sample-data versions of the hub pages, rendered only in the static preview build (`PREVIEW=1`, see
`.github/workflows/pages.yml`). Normal builds show the route placeholders until each page reads from the API.

- `/` is the public landing page (`$lib/Landing.svelte`, copy in `$lib/landing.ts`), the same in every build.
  `Story` (at `/story`) and `Recruit` are the rest of the public face; everything else opens after sign-in.
- `Hub` is the customisable home: `$lib/components/HomeView.svelte` draws the member's widgets in their order and the
  customiser. Hub widgets use the mock data; analyzer widgets draw `$lib/mock/analyzer.ts`, a sample in the analyzer's
  home page contract (`$lib/home-payload.ts`), including the officers' badge roster from `$lib/mock/badges.ts`,
  which also gives Hopscotch's own badges on `Me`. `Officers` is the officer view.
- The preview opens signed out on the landing page. Its "Log in with Discord" goes to a pretend sign-in at `/login`
  (preview only; the real site answers 404 there) where the visitor picks the raider or the officer view.
  `session.svelte.ts` keeps the choice in localStorage; the top bar switches views and logs out, and the layout uses
  `gate.ts` to ask signed-out visitors to sign in on member pages and to keep raiders out of the officer console.
- Data comes from `$lib/mock/data.ts` and `$lib/mock/community.ts`. The preview visitor is Hopscotch, a Wednesday
  officer who raids both nights; the raider view signs in without the officer powers. The e2e suite signs in with
  `e2e/auth.ts`.
- `Bank` is the real bank page (`$lib/components/BankLive.svelte`) answered by `bank-fake.ts`, an in-memory stand-in for
  the hub's bank routes installed with `useBankFetch`. The officer view is also a super admin there, so the request
  queue, imports, grants, officer tokens and the break-glass notice all show; a token minted as the officer can be
  redeemed in the raider view. The state lasts until the page reloads.
- `state.svelte.ts` holds in-memory copies of the community data and the preview visitor's home layout. Officer actions, spotlight consent and the compose
  form change only that state (kept across client-side navigation, reset on reload); nothing is sent anywhere, and the
  recruit form only shows its success message.
- The logic these pages use (`clips`, `posts`, `recruitment`, `application`, `progression`) lives in `$lib` with unit
  tests, so the API-backed pages can reuse it. `npm run e2e` runs Playwright against this preview build.
