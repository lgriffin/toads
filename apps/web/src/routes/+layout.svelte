<script lang="ts">
  import '@fontsource/cinzel/600.css';
  import '@fontsource/cinzel/700.css';
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { myAwards, titlesOf } from '$lib/awards';
  import { previewAwardsOf } from '$lib/preview/awards-fake';
  import { PREVIEW_ROLE_BADGES } from '$lib/preview/role-badges-fake';
  import { ROLE_BADGES_CHANGED, myRoleBadges } from '$lib/role-badges';
  import type { Title } from '$lib/toads';
  import { forgetRecruitDraft } from '$lib/application';
  import { PUBLIC_NAV, isActive, memberNav } from '$lib/nav';
  import { TIER_LABEL, tierOf, type Tier } from '$lib/access';
  import { hasOfficerPowers, previewGate, type PreviewRole } from '$lib/preview/gate';
  import { LAUNCH_HOLD, heldNav, isMemberPath, launchHold } from '$lib/launch';
  import { setMe } from '$lib/me-context';
  import ComingSoon from '$lib/components/ComingSoon.svelte';
  import ForeverNotice from '$lib/components/ForeverNotice.svelte';
  import MemberToads from '$lib/components/MemberToads.svelte';
  import ToadGreeting from '$lib/components/ToadGreeting.svelte';
  import ToadsMark from '$lib/components/ToadsMark.svelte';
  import { loadPreviewSession, previewSession, previewSignIn, previewSignOut } from '$lib/preview/session.svelte';
  let { children } = $props();
  // undefined while loading; null when signed out. The preview never calls the API.
  let session = $state<Session | null | undefined>(undefined);
  // The session request failed (not a 401): we cannot tell who this is, so held member pages stay closed.
  let sessionFailed = $state(false);
  // Titles (banker, developer, Discord admin) are awards; they show as toads beside the rank toad.
  let titles = $state<Title[]>([]);
  // Badges the member's Discord roles earn (Wednesday Toad, Healer, ...), tied to roles by a super admin.
  let roleBadges = $state<string[]>([]);
  onMount(async () => {
    if (__PREVIEW__) {
      loadPreviewSession();
      titles = titlesOf(previewAwardsOf(1));
      roleBadges = PREVIEW_ROLE_BADGES;
      return;
    }
    session = await getSession().catch(() => {
      sessionFailed = true;
      return null;
    });
    if (!session) return;
    const [awards] = await Promise.all([myAwards().catch(() => []), loadRoleBadges()]);
    titles = titlesOf(awards);
  });
  async function loadRoleBadges() {
    roleBadges = (await myRoleBadges().catch(() => [])).map((b) => b.id);
  }
  // A super admin's change on the admin page shows in the header without a reload.
  $effect(() => {
    if (__PREVIEW__ || !session) return;
    window.addEventListener(ROLE_BADGES_CHANGED, loadRoleBadges);
    return () => window.removeEventListener(ROLE_BADGES_CHANGED, loadRoleBadges);
  });
  let path = $derived($page.url.pathname.slice(base.length) || '/');
  // The preview signs in on /login as a raider or an officer. Officer links only hide; the API is the real gate.
  let officer = $derived(__PREVIEW__ ? hasOfficerPowers(previewSession.role) : (session?.officer_days.length ?? 0) > 0);
  // The tier chip in the top bar opens Hub features, which says what this tier can do.
  const PREVIEW_TIER: Record<PreviewRole, Tier> = { member: 'raider', officer: 'officer', admin: 'admin' };
  let tier = $derived<Tier>(
    __PREVIEW__ ? (previewSession.role ? PREVIEW_TIER[previewSession.role] : 'visitor') : tierOf(session)
  );
  const VIEWS: { role: PreviewRole; label: string }[] = [
    { role: 'member', label: 'Switch to raider view' },
    { role: 'officer', label: 'Switch to officer view' },
    { role: 'admin', label: 'Switch to super admin view' }
  ];
  let members = $derived(heldNav(memberNav(officer, tier === 'admin'), tier));
  // Everything past the public pages opens on login, so the member links show only to a signed-in member.
  let signedIn = $derived(__PREVIEW__ ? previewSession.role !== null : !!session);
  // The preview has no API to refuse a page, so it gates member pages and the officer console itself.
  let gate = $derived(__PREVIEW__ ? previewGate(path, previewSession.role) : 'open');
  // Until the Forever launch, raiders get one coming-soon page and officers a notice on each tab (src/lib/launch.ts).
  // The real site waits for the session on member pages so a held page never starts its own API calls.
  let hold = $derived(launchHold(path, tier));
  // The signed-in member's own toad greets them on the hub home and on the held pages (ToadGreeting).
  let me = $derived(
    __PREVIEW__
      ? { name: 'Hopscotch', tier, username: 'hopscotch', titles, roleBadges, className: 'Rogue', role: 'Melee' as const }
      : { name: session?.display_name ?? '', tier, username: session?.discord_username, titles, roleBadges }
  );
  // Pages that show the member's toads (/me) read these facts, so they match the header.
  setMe(() => me);
  let isHubHome = $derived(path === '/hub' || path === '/hub/');
  let holdPending = $derived(LAUNCH_HOLD && !__PREVIEW__ && isMemberPath(path) && (session === undefined || sessionFailed));

  function switchView(next: PreviewRole) {
    previewSignIn(next);
    if (previewGate(path, next) !== 'open') goto(`${base}/hub/`);
  }
  function logOut() {
    previewSignOut();
    forgetRecruitDraft();
    goto(`${base}/`);
  }
</script>

<a class="skip" href="#main">Skip to content</a>

{#if __PREVIEW__}
  <div class="preview">Preview with sample data. Nothing here is live.</div>
{/if}

<header>
  <a class="brand" href="{base}/"><ToadsMark size={28} />Toads</a>
  <nav aria-label="Guild">
    {#each PUBLIC_NAV as item}
      <a href="{base}{item.href}{item.href === '/' ? '' : '/'}" aria-current={isActive(path, item.href) ? 'page' : undefined}
        >{item.label}</a
      >
    {/each}
  </nav>
  {#if signedIn}
    <nav aria-label="Members" class="members">
      {#each members as item}
        <a href="{base}{item.href}/" aria-current={isActive(path, item.href) ? 'page' : undefined}>{item.label}</a>
      {/each}
    </nav>
  {/if}
  {#if __PREVIEW__}
    {#if !previewSession.ready}
      <span class="login"></span>
    {:else if signedIn}
      <div class="login">
        <span>Signed in as Hopscotch <MemberToads {tier} username="hopscotch" {titles} {roleBadges} className="Rogue" role="Melee" size={24} /> <a class="pill" href="{base}/features/" title="What you can do">{TIER_LABEL[tier]}</a></span>
        {#each VIEWS.filter((v) => v.role !== previewSession.role) as v (v.role)}
          <button type="button" onclick={() => switchView(v.role)}>{v.label}</button>
        {/each}
        <button type="button" onclick={logOut}>Log out</button>
      </div>
    {:else}
      <a class="login" href="{base}/login/">Log in with Discord</a>
    {/if}
  {:else if session}
    <form class="login" method="post" action="/auth/logout" onsubmit={forgetRecruitDraft}>
      <span>Signed in as {session.display_name} <MemberToads {tier} username={session.discord_username} {titles} {roleBadges} size={24} /> <a class="pill" href="/features" title="What you can do">{TIER_LABEL[tier]}</a></span>
      <button type="submit">Log out</button>
    </form>
  {:else if session === null}
    <a class="login" href="/auth/login" data-sveltekit-reload>Log in with Discord</a>
  {/if}
</header>

<main id="main" tabindex="-1">
  {#if holdPending && sessionFailed}
    <section class="card gate" aria-labelledby="gate-h">
      <h1 id="gate-h">The hub did not answer</h1>
      <p>We could not check your sign-in just now. Reload the page to try again.</p>
    </section>
  {:else if (__PREVIEW__ && gate !== 'open' && !previewSession.ready) || holdPending}
    <p class="muted" role="status">Loading…</p>
  {:else if gate === 'sign-in'}
    <section class="card gate" aria-labelledby="gate-h">
      <h1 id="gate-h">Sign in to see this</h1>
      <p>This page is for guild members. Log in to explore it with sample data.</p>
      <p><a class="btn primary" href="{base}/login/">Log in with Discord</a></p>
    </section>
  {:else if gate === 'admins-only'}
    <section class="card gate" aria-labelledby="gate-h">
      <h1 id="gate-h">Super admins only</h1>
      <p>The admin console is for the guild's super admins. Switch to the super admin view to see it.</p>
      <p>
        <button class="btn primary" type="button" onclick={() => previewSignIn('admin')}>Switch to super admin view</button>
      </p>
    </section>
  {:else if gate === 'officers-only'}
    <section class="card gate" aria-labelledby="gate-h">
      <h1 id="gate-h">Officers only</h1>
      <p>The officer console is for raid leaders. Switch to the officer view to see it.</p>
      <p>
        <button class="btn primary" type="button" onclick={() => previewSignIn('officer')}>Switch to officer view</button>
      </p>
    </section>
  {:else if hold === 'coming-soon'}
    <ComingSoon {...me} />
  {:else if hold === 'forever-notice'}
    <ForeverNotice {path} {...me} />
  {:else}
    {#if signedIn && isHubHome}
      <ToadGreeting {...me} />
    {/if}
    {@render children()}
  {/if}
</main>

<style>
  /* The pond at dusk, as on the homepage: twilight ink and violet, a teal accent, bronze and cream. */
  :global(:root) {
    --ink: #120f33;
    --dusk: #1b1a4d;
    --teal: #3fd6c8;
    --bronze: #d9a85a;
    --bronze-hi: #f4dc9c;
    --cream: #f7ecd2;
    --bg: var(--ink);
    --surface: #1d1c52;
    --text: var(--cream);
    --muted: #c4c0ea;
    --accent: var(--teal);
    --line: #3d3d86;
    --warn: #e0b04f;
    --bad: #e06a5f;
    color-scheme: dark;
  }
  :global(body) {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, sans-serif;
  }
  :global(h1) { font-size: 1.5rem; margin: 0.5rem 0 1rem; }
  :global(h2) { font-size: 1.1rem; margin: 0 0 0.75rem; }
  :global(.muted) { color: var(--muted); }
  :global(.grid) { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr)); }
  :global(.card) { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 1rem; }
  :global(.scroll) { overflow-x: auto; }
  :global(table) { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
  :global(th), :global(td) { text-align: left; padding: 0.45rem 0.5rem; border-bottom: 1px solid var(--line); }
  :global(th) { color: var(--muted); font-weight: 500; }
  :global(td.num), :global(th.num) { text-align: right; font-variant-numeric: tabular-nums; }
  :global(.pill) { display: inline-block; padding: 0.1rem 0.5rem; border-radius: 999px; font-size: 0.8rem; background: var(--line); }
  :global(.ok) { color: var(--accent); }
  :global(.warn) { color: var(--warn); }
  :global(.bad) { color: var(--bad); }
  :global(main a) { color: var(--accent); }
  :global(:focus-visible) { outline: 2px solid var(--accent); outline-offset: 2px; }
  :global(main:focus) { outline: none; }
  :global(.sr-only) {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  :global(.btn) {
    display: inline-block;
    padding: 0.5rem 0.9rem;
    border-radius: 6px;
    border: 1px solid var(--line);
    background: var(--surface);
    color: var(--text);
    font: inherit;
    font-size: 0.95rem;
    text-decoration: none;
    cursor: pointer;
  }
  :global(main a.btn) { color: var(--text); }
  :global(.btn:hover) { border-color: var(--muted); }
  :global(.btn.primary), :global(main a.btn.primary) { background: var(--accent); border-color: var(--accent); color: #0d0b28; font-weight: 600; }
  :global(.btn.danger) { border-color: var(--bad); color: #f0a39c; }
  :global(.btn:disabled) { opacity: 0.55; cursor: not-allowed; }
  :global(.field) { display: flex; flex-direction: column; gap: 0.3rem; min-width: 0; }
  :global(.field label), :global(legend) { font-size: 0.9rem; }
  :global(input:not([type='checkbox'])), :global(select), :global(textarea) {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.45rem 0.55rem;
    font: inherit;
    max-width: 100%;
    box-sizing: border-box;
  }
  :global(textarea) { resize: vertical; width: 100%; }
  :global([aria-invalid='true']) { border-color: var(--bad) !important; }
  :global(.hint) { font-size: 0.8rem; color: var(--muted); }
  :global(.err) { font-size: 0.85rem; color: #f0a39c; }
  :global(main) { overflow-wrap: break-word; }
  header {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1.25rem;
    align-items: center;
    padding: 0.75rem 1rem;
    background: #0d0b28;
    border-bottom: 1px solid color-mix(in srgb, var(--bronze) 45%, transparent);
  }
  nav { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; }
  .members { padding-left: 1rem; border-left: 1px solid var(--line); }
  .brand { color: var(--cream); font-family: 'Cinzel', Georgia, serif; font-weight: 700; letter-spacing: 0.08em; display: inline-flex; align-items: center; gap: 0.5rem; }
  .skip { position: absolute; left: -999px; top: 0; background: var(--accent); color: #0f1411; padding: 0.5rem; z-index: 10; }
  .skip:focus { left: 0.5rem; }
  @media (max-width: 40rem) {
    .members { padding-left: 0; border-left: 0; }
  }
  a { color: var(--muted); text-decoration: none; }
  a[aria-current='page'], a:hover { color: var(--text); }
  .login { margin-left: auto; color: var(--accent); }
  form.login, div.login { display: flex; flex-wrap: wrap; gap: 0.4rem 0.75rem; align-items: center; }
  div.login { color: var(--text); }
  div.login button, form.login button { background: none; border: 0; color: var(--muted); cursor: pointer; font: inherit; padding: 0; }
  div.login button:hover, form.login button:hover { color: var(--text); }
  .preview {
    padding: 0.4rem 1rem;
    background: var(--warn);
    color: #1b1406;
    font-size: 0.85rem;
    text-align: center;
  }
  .gate { max-width: 36rem; margin: 2rem auto; }
  main { max-width: 72rem; margin: 0 auto; padding: 1rem; }
</style>
