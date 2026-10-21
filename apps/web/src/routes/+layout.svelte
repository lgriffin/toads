<script lang="ts">
  import '@fontsource/cinzel/600.css';
  import '@fontsource/cinzel/700.css';
  import '$lib/theme.css';
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
  import { PUBLIC_NAV, currentIn, hubMenu, inMenu, isActive, memberNav, officerMenu, type NavGroup } from '$lib/nav';
  import { TIER_LABEL, tierOf, type Tier } from '$lib/access';
  import { hasOfficerPowers, previewGate, type PreviewRole } from '$lib/preview/gate';
  import { LAUNCH_HOLD, heldNav, isMemberPath, launchHold } from '$lib/launch';
  import { setMe } from '$lib/me-context';
  import { dayName, raidDaysOf } from '$lib/absences';
  import { previewRaidSession } from '$lib/preview/absences-fake';
  import ComingSoon from '$lib/components/ComingSoon.svelte';
  import DisplaySettings from '$lib/components/DisplaySettings.svelte';
  import ForeverNotice from '$lib/components/ForeverNotice.svelte';
  import NavMenu from '$lib/components/NavMenu.svelte';
  import ToadGreeting from '$lib/components/ToadGreeting.svelte';
  import ToadsMark from '$lib/components/ToadsMark.svelte';
  import { loadPreviewSession, previewSession, previewSignIn, previewSignOut } from '$lib/preview/session.svelte';
  let { children } = $props();
  // undefined while loading; null when signed out. The preview never calls the API.
  let session = $state<Session | null | undefined>(undefined);
  // The session request failed (not a 401): we cannot tell who this is, so held member pages stay closed.
  let sessionFailed = $state(false);
  // Titles (banker, developer, Discord admin) are awards; they show as toads beside the rank toad on the hub home and Me.
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
  // The top bar: a Hub menu, Me, and one Officers menu that lists only the raid nights this officer runs.
  let hubGroups = $derived(hubMenu(members));
  let raidDays = $derived(raidDaysOf(__PREVIEW__ ? previewRaidSession(previewSession.role) : session));
  let officerGroups = $derived(
    officerMenu(
      officer,
      tier === 'admin',
      raidDays.officerDays.map((day) => ({ day, name: dayName(day, raidDays.names) }))
    )
  );
  let meOpen = $derived(members.some((i) => i.href === '/me'));
  let settingsOpen = $derived(launchHold('/me/settings', tier) === 'open');
  let displayName = $derived(__PREVIEW__ ? 'Hopscotch' : (session?.display_name ?? ''));
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

  let accountOpen = $state(false);
  function switchView(next: PreviewRole) {
    accountOpen = false;
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

{#snippet links(groups: NavGroup[])}
  {@const here = currentIn(path, groups)}
  {#each groups as group (group.label)}
    {#if group.items.length}
      <p class="group">{group.label}</p>
      <ul>
        {#each group.items as item (item.href)}
          <li>
            <a href="{base}{item.href}{item.href === '/' ? '' : '/'}" aria-current={here === item.href ? 'page' : undefined}>
              <span class="name">{item.label}</span>
              {#if item.hint}<span class="hint">{item.hint}</span>{/if}
            </a>
          </li>
        {/each}
      </ul>
    {/if}
  {/each}
{/snippet}

<header>
  <a class="brand" href="{base}/"><ToadsMark size={28} /><span class="brand-name">Toads</span></a>
  {#if signedIn}
    <nav aria-label="Main" class="main">
      <NavMenu id="menu-hub" label="Hub" current={inMenu(path, hubGroups)}>{@render links(hubGroups)}</NavMenu>
      {#if meOpen}
        <a class="top" href="{base}/me/" aria-current={isActive(path, '/me') ? 'page' : undefined}>Me</a>
      {/if}
      {#if officerGroups.length}
        <NavMenu id="menu-officers" label="Officers" current={inMenu(path, officerGroups)}>{@render links(officerGroups)}</NavMenu>
      {/if}
    </nav>
  {:else}
    <nav aria-label="Guild" class="guild">
      {#each PUBLIC_NAV as item}
        <a href="{base}{item.href}{item.href === '/' ? '' : '/'}" aria-current={isActive(path, item.href) ? 'page' : undefined}
          >{item.label}</a
        >
      {/each}
    </nav>
  {/if}
  <div class="account">
    {#if __PREVIEW__ && !previewSession.ready}
      <span></span>
    {:else if signedIn}
      <NavMenu id="menu-account" label={displayName} prefix="Account:" align="end" bind:open={accountOpen}>
        <div class="who">
          <span>Signed in as <strong>{displayName}</strong></span>
          <span class="pill">{TIER_LABEL[tier]}</span>
        </div>
        <ul>
          {#if settingsOpen}
            <li><a href="{base}/me/settings/"><span class="name">Account settings</span><span class="hint">Your name and Warcraft Logs key</span></a></li>
          {/if}
          <li><a href="{base}/setup/"><span class="name">Your setup</span><span class="hint">Your main, specs and alts</span></a></li>
          <li><a href="{base}/features/"><span class="name">What you can do</span><span class="hint">What your rank opens in the hub</span></a></li>
        </ul>
        <DisplaySettings />
        {#if __PREVIEW__}
          <p class="group">Preview</p>
          {#each VIEWS.filter((v) => v.role !== previewSession.role) as v (v.role)}
            <button class="item" type="button" onclick={() => switchView(v.role)}>{v.label}</button>
          {/each}
          <button class="item out" type="button" onclick={logOut}>Log out</button>
        {:else}
          <form method="post" action="/auth/logout" onsubmit={forgetRecruitDraft}>
            <button class="item out" type="submit">Log out</button>
          </form>
        {/if}
      </NavMenu>
    {:else}
      <NavMenu id="menu-display" label="Display" align="end"><DisplaySettings /></NavMenu>
      {#if __PREVIEW__}
        <a class="login" href="{base}/login/">Log in with Discord</a>
      {:else if session === null}
        <a class="login" href="/auth/login" data-sveltekit-reload>Log in with Discord</a>
      {/if}
    {/if}
  </div>
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
  /* Colour tokens for both themes, and easier reading, live in src/lib/theme.css. */
  :global(body) {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, sans-serif;
    line-height: 1.5;
  }
  :global(.always-dusk) { color: var(--text); }
  :global(::selection) { background: var(--bronze); color: var(--on-bronze); }
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
  :global(.btn.primary), :global(main a.btn.primary) { background: var(--accent); border-color: var(--accent); color: var(--on-accent); font-weight: 600; }
  :global(.btn.danger) { border-color: var(--bad); color: var(--bad-text); }
  /* Thumb-sized buttons on touch screens (44px), without making every desktop button tall. */
  @media (pointer: coarse) {
    :global(.btn) { display: inline-flex; align-items: center; justify-content: center; min-height: 2.75rem; }
  }
  /* Placeholders carry hints, so they keep the muted text colour (4.5:1 or better in both themes). */
  :global(::placeholder) { color: var(--muted); opacity: 1; }
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
  :global(.err) { font-size: 0.85rem; color: var(--bad-text); }
  :global(main) { overflow-wrap: break-word; }
  header {
    position: relative;
    z-index: 15;
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    align-items: center;
    padding: 0.4rem 1rem;
    background: var(--header-bg);
    border-bottom: 1px solid color-mix(in srgb, var(--bronze) 45%, transparent);
  }
  nav { display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem; }
  .brand-name { display: inline; }
  .brand { color: var(--cream); font-family: 'Cinzel', Georgia, serif; font-weight: 700; letter-spacing: 0.08em; display: inline-flex; align-items: center; gap: 0.5rem; min-height: 2.75rem; margin-right: 0.5rem; }
  .skip { position: absolute; left: -999px; top: 0; background: var(--accent); color: var(--on-accent); padding: 0.5rem; z-index: 30; }
  .skip:focus { left: 0.5rem; }
  a { color: var(--nav-text); text-decoration: none; }
  .guild a, a.top { display: inline-flex; align-items: center; min-height: 2.75rem; padding: 0 0.75rem; border-radius: 8px; }
  .guild a:hover, a.top:hover { color: var(--text); background: var(--nav-hover); }
  /* The current page: brighter text and an accent rule under it, so it never rests on colour alone. */
  .guild a[aria-current='page'], a.top[aria-current='page'] { color: var(--text); box-shadow: inset 0 -2px 0 var(--accent); border-radius: 8px 8px 2px 2px; }
  .account { margin-left: auto; display: flex; align-items: center; gap: 0.5rem; }
  .login { color: var(--accent); display: inline-flex; align-items: center; min-height: 2.75rem; padding: 0 0.5rem; }
  .login:hover { color: var(--text); }

  /* Inside a top bar menu: small group labels, then each link with one plain line under it. */
  header ul { list-style: none; margin: 0 0 0.25rem; padding: 0; }
  .group { margin: 0.5rem 0.5rem 0.2rem; font-size: 0.8rem; font-weight: 600; color: var(--muted); }
  .group:first-child { margin-top: 0.15rem; }
  header li a, .item {
    display: grid;
    gap: 0.05rem;
    width: 100%;
    min-height: 2.75rem;
    align-content: center;
    padding: 0.35rem 0.6rem;
    border-radius: 6px;
    box-sizing: border-box;
    color: var(--text);
  }
  header li a:hover, .item:hover { background: var(--nav-hover); }
  header li a[aria-current='page'] { background: var(--nav-hover); box-shadow: inset 3px 0 0 var(--accent); }
  .name { font-weight: 600; }
  .hint { font-size: 0.85rem; color: var(--muted); }
  .who { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 0.6rem; padding: 0.4rem 0.6rem 0.6rem; border-bottom: 1px solid var(--line); margin-bottom: 0.35rem; color: var(--text); }
  .who .pill { color: var(--text); }
  .item { background: none; border: 0; font: inherit; text-align: left; cursor: pointer; }
  .item.out { margin-top: 0.35rem; border-top: 1px solid var(--line); border-radius: 0 0 6px 6px; color: var(--muted); }
  .item.out:hover { color: var(--text); }
  form { margin: 0; }
  @media (max-width: 40rem) {
    header { padding: 0.25rem 0.75rem; gap: 0.25rem 0.5rem; }
    .guild { order: 3; width: 100%; }
    .main { order: 2; }
    .account { order: 2; margin-left: auto; }
    .main :global(button), a.top { padding: 0 0.55rem; }
    .account :global(.label) { max-width: 6.5rem; }
  }
  /* On the narrowest phones the toad mark alone stands for the brand, so the top bar stays on one line. */
  @media (max-width: 26rem) {
    .brand-name { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; }
    .brand { margin-right: 0; }
  }
  .preview {
    padding: 0.4rem 1rem;
    /* A fixed amber strip in both themes: it labels the whole site as sample data. */
    background: #e0b04f;
    color: #1b1406;
    font-size: 0.85rem;
    text-align: center;
  }
  .gate { max-width: 36rem; margin: 2rem auto; }
  main { max-width: 72rem; margin: 0 auto; padding: 1rem; }
  /* The pond pages' bands start flush under the top bar, so no strip of page colour shows above a dusk hero. */
  :global(main > .pond:first-child), :global(main > .pond-page:first-child) { margin-top: -1rem; }
</style>
