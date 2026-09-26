Sample-data versions of the hub pages, rendered only in the static preview build (`PREVIEW=1`, see
`.github/workflows/pages.yml`). Normal builds show the route placeholders until each page reads from the API.

- `Story`, `Recruit`, `Highlights` are the public face; `Hub` and `Officers` are the member and officer views.
- Data comes from `$lib/mock/data.ts` and `$lib/mock/community.ts`. The preview visitor is Hopscotch, a Wednesday
  officer who raids both nights, so every section shows.
- `state.svelte.ts` holds in-memory copies of the community data. Officer actions, spotlight consent and the compose
  form change only that state (kept across client-side navigation, reset on reload); nothing is sent anywhere, and the
  recruit form only shows its success message.
- The logic these pages use (`clips`, `posts`, `recruitment`, `application`, `progression`) lives in `$lib` with unit
  tests, so the API-backed pages can reuse it. `npm run e2e` runs Playwright against this preview build.
