<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import { ADMIN_GUIDE, INTEGRATIONS, JOBS } from '$lib/admin';
  import { useBankFetch } from '$lib/bank';
  import BankGrants from '$lib/components/BankGrants.svelte';
  import { previewBankFetch } from '$lib/preview/bank-fake';

  // The super admin console: who else runs the bank, and where each integration is set up. The hub's routes are the
  // gate (MANAGE_GRANTS); the preview gates this page in the layout and answers the bank from sample data.
  if (__PREVIEW__) useBankFetch(previewBankFetch);
  let session = $state<Session | null | undefined>(__PREVIEW__ ? null : undefined);
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const allowed = $derived(__PREVIEW__ || !!session?.super_admin);
  const days = $derived(__PREVIEW__ ? ['wed', 'sun'] : (session?.officer_days ?? []));
  const outside = (href: string) => href.startsWith('https://');
</script>

<svelte:head><title>Admin · Toads</title></svelte:head>

<h1>Admin console</h1>

{#if !__PREVIEW__ && session === undefined}
  <p class="muted" role="status">Loading…</p>
{:else if !allowed}
  <section class="card" aria-labelledby="no-h">
    <h2 id="no-h">Super admins only</h2>
    <p>This console is for the guild's super admins, who are named in the hub's configuration.</p>
  </section>
{:else}
  <p class="lede">
    Grants, officer tokens and the hub's integrations. Super admins are named in the hub's configuration, and the
    break-glass admin's changes are always audited.
  </p>

  <section class="block" aria-labelledby="integrations-h">
    <h2 id="integrations-h">Integrations</h2>
    <ul class="tiles">
      {#each INTEGRATIONS as it (it.title)}
        <li class="card">
          <h3>{it.title}</h3>
          <p>{it.body}</p>
          {#if outside(it.href)}
            <a href={it.href} target="_blank" rel="noopener noreferrer">{it.action}</a>
          {:else}
            <a href="{base}{it.href}/">{it.action}</a>
          {/if}
        </li>
      {/each}
    </ul>
  </section>

  <section class="block card" aria-labelledby="jobs-h">
    <h2 id="jobs-h">Scheduled jobs</h2>
    <p class="muted">What the worker's scheduler refreshes, at its default intervals. Live run times are not shown yet.</p>
    <div class="scroll">
      <table>
        <thead><tr><th scope="col">Job</th><th scope="col">Refreshes</th><th scope="col">Every</th></tr></thead>
        <tbody>
          {#each JOBS as j (j.name)}
            <tr><td><code>{j.name}</code></td><td>{j.what}</td><td>{j.every}</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <div class="block">
    <BankGrants
      {days}
      manage
      breakGlass={__PREVIEW__ ? false : (session?.break_glass ?? false)}
      breakGlassAdmin={__PREVIEW__ ? '1000' : null}
    />
  </div>

  <p><a href={ADMIN_GUIDE} target="_blank" rel="noopener noreferrer">Read the admin guide</a> for every setting.</p>
{/if}

<style>
  .lede { max-width: 46rem; margin: 0 0 1.25rem; }
  .block { margin-bottom: 1.5rem; }
  .block > h2 { margin: 0 0 0.75rem; }
  .tiles { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
  .tiles li { display: grid; gap: 0.4rem; align-content: start; }
  .tiles h3 { margin: 0; font-size: 1rem; }
  .tiles p { margin: 0; }
</style>
