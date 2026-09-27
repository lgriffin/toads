<script lang="ts">
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { NAV, isActive } from '$lib/nav';
  let { children } = $props();
  // undefined while loading; null when signed out. The preview never calls the API.
  let session = $state<Session | null | undefined>(undefined);
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  let path = $derived($page.url.pathname.slice(base.length) || '/');
</script>

{#if __PREVIEW__}
  <div class="preview">Preview with sample data. Nothing here is live.</div>
{/if}

<header>
  <strong>Toads</strong>
  <nav>
    {#each NAV as item}
      <a href="{base}{item.href}" aria-current={isActive(path, item.href) ? 'page' : undefined}>{item.label}</a>
    {/each}
  </nav>
  {#if __PREVIEW__}
    <span class="login">Signed in as Hopscotch</span>
  {:else if session}
    <form class="login" method="post" action="/auth/logout">
      <span>Signed in as {session.display_name}</span>
      <button type="submit">Log out</button>
    </form>
  {:else if session === null}
    <a class="login" href="/auth/login" data-sveltekit-reload>Log in with Discord</a>
  {/if}
</header>

<main>{@render children()}</main>

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
  header {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1.25rem;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--surface);
  }
  nav { display: flex; flex-wrap: wrap; gap: 1rem; }
  a { color: var(--muted); text-decoration: none; }
  a[aria-current='page'], a:hover { color: var(--text); }
  .login { margin-left: auto; color: var(--accent); }
  form.login { display: flex; gap: 0.75rem; align-items: center; }
  form.login button { background: none; border: 0; color: var(--muted); cursor: pointer; font: inherit; padding: 0; }
  form.login button:hover { color: var(--text); }
  .preview {
    padding: 0.4rem 1rem;
    background: var(--warn);
    color: #1b1406;
    font-size: 0.85rem;
    text-align: center;
  }
  main { max-width: 72rem; margin: 0 auto; padding: 1rem; }
</style>
