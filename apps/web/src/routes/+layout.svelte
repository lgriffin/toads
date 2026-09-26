<script lang="ts">
  import { page } from '$app/stores';
  import { NAV, isActive } from '$lib/nav';
  let { children } = $props();
</script>

<header>
  <strong>Toads</strong>
  <nav>
    {#each NAV as item}
      <a href={item.href} aria-current={isActive($page.url.pathname, item.href) ? 'page' : undefined}>{item.label}</a>
    {/each}
  </nav>
  <a class="login" href="/auth/login">Log in with Discord</a>
</header>

<main>{@render children()}</main>

<style>
  :global(:root) {
    --bg: #0f1411;
    --surface: #18201b;
    --text: #e6efe8;
    --muted: #93a79a;
    --accent: #5fbf6a;
    color-scheme: dark;
  }
  :global(body) {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, sans-serif;
  }
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
  main { max-width: 72rem; margin: 0 auto; padding: 1rem; }
</style>
