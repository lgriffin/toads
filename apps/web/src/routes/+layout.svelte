<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { PUBLIC_NAV, isActive, memberNav } from '$lib/nav';
  import { previewGate } from '$lib/preview/gate';
  import { loadPreviewSession, previewSession, previewSignIn, previewSignOut } from '$lib/preview/session.svelte';
  let { children } = $props();
  // undefined while loading; null when signed out. The preview never calls the API.
  let session = $state<Session | null | undefined>(undefined);
  onMount(async () => {
    if (__PREVIEW__) loadPreviewSession();
    else session = await getSession().catch(() => null);
  });
  let path = $derived($page.url.pathname.slice(base.length) || '/');
  // The preview signs in on /login as a raider or an officer. Officer links only hide; the API is the real gate.
  let officer = $derived(__PREVIEW__ ? previewSession.role === 'officer' : (session?.officer_days.length ?? 0) > 0);
  let members = $derived(memberNav(officer));
  // Everything past the public pages opens on login, so the member links show only to a signed-in member.
  let signedIn = $derived(__PREVIEW__ ? previewSession.role !== null : !!session);
  // The preview has no API to refuse a page, so it gates member pages and the officer console itself.
  let gate = $derived(__PREVIEW__ ? previewGate(path, previewSession.role) : 'open');

  function switchView() {
    const next = officer ? 'member' : 'officer';
    previewSignIn(next);
    if (next === 'member' && previewGate(path, next) !== 'open') goto(`${base}/hub/`);
  }
  function logOut() {
    previewSignOut();
    goto(`${base}/`);
  }
</script>

<a class="skip" href="#main">Skip to content</a>

{#if __PREVIEW__}
  <div class="preview">Preview with sample data. Nothing here is live.</div>
{/if}

<header>
  <a class="brand" href="{base}/">Toads</a>
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
        <span>Signed in as Hopscotch <span class="pill">{officer ? 'Officer' : 'Raider'}</span></span>
        <button type="button" onclick={switchView}>{officer ? 'Switch to raider view' : 'Switch to officer view'}</button>
        <button type="button" onclick={logOut}>Log out</button>
      </div>
    {:else}
      <a class="login" href="{base}/login/">Log in with Discord</a>
    {/if}
  {:else if session}
    <form class="login" method="post" action="/auth/logout">
      <span>Signed in as {session.display_name}</span>
      <button type="submit">Log out</button>
    </form>
  {:else if session === null}
    <a class="login" href="/auth/login" data-sveltekit-reload>Log in with Discord</a>
  {/if}
</header>

<main id="main" tabindex="-1">
  {#if __PREVIEW__ && gate !== 'open' && !previewSession.ready}
    <p class="muted" role="status">Loading…</p>
  {:else if gate === 'sign-in'}
    <section class="card gate" aria-labelledby="gate-h">
      <h1 id="gate-h">Sign in to see this</h1>
      <p>This page is for guild members. Log in to explore it with sample data.</p>
      <p><a class="btn primary" href="{base}/login/">Log in with Discord</a></p>
    </section>
  {:else if gate === 'officers-only'}
    <section class="card gate" aria-labelledby="gate-h">
      <h1 id="gate-h">Officers only</h1>
      <p>The officer console is for raid leaders. Switch to the officer view to see it.</p>
      <p>
        <button class="btn primary" type="button" onclick={() => previewSignIn('officer')}>Switch to officer view</button>
      </p>
    </section>
  {:else}
    {@render children()}
  {/if}
</main>

<style>
  :global(:root) {
    --bg: #0f1411;
    --surface: #18201b;
    --text: #e6efe8;
    --muted: #93a79a;
    --accent: #5fbf6a;
    --line: #2a352e;
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
  :global(.btn.primary), :global(main a.btn.primary) { background: var(--accent); border-color: var(--accent); color: #0f1411; font-weight: 600; }
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
    background: var(--surface);
  }
  nav { display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; }
  .members { padding-left: 1rem; border-left: 1px solid var(--line); }
  .brand { color: var(--text); font-weight: 700; }
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
