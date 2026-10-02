<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import type { PreviewRole } from '$lib/preview/gate';
  import { previewSession, previewSignIn } from '$lib/preview/session.svelte';

  const CHOICES: { role: PreviewRole; title: string; body: string }[] = [
    {
      role: 'member',
      title: 'Sign in as a raider',
      body: 'Your hub home, raids and logs, highlights, the guild bank and your own page with badges and performance.'
    },
    {
      role: 'officer',
      title: 'Sign in as an officer',
      body: 'Everything a raider sees, plus Wednesday’s raid leader desk, the badge roster, the officer console and Wednesday’s bank.'
    },
    {
      role: 'admin',
      title: 'Sign in as a super admin',
      body: 'Everything an officer sees on both nights, plus bank grants, officer tokens and the break-glass notice.'
    }
  ];

  const VIEW: Record<PreviewRole, string> = { member: 'raider', officer: 'officer', admin: 'super admin' };

  function choose(role: PreviewRole) {
    previewSignIn(role);
    goto(`${base}/hub/`);
  }
</script>

<svelte:head><title>Log in · Toads</title></svelte:head>

<section class="login" aria-labelledby="login-h">
  <h1 id="login-h">Log in with Discord</h1>
  <p>
    This is a demo, so there is no real Discord sign-in. Pick a view to explore as Hopscotch, one of our raiders.
    You can switch views or log out from the top bar at any time.
  </p>
  {#if previewSession.role}
    <p class="muted">You are signed in with the {VIEW[previewSession.role]} view. Picking again switches views.</p>
  {/if}
  <div class="choices">
    {#each CHOICES as c (c.role)}
      <div class="card">
        <h2>{c.title}</h2>
        <p>{c.body}</p>
        <button class="btn primary" type="button" onclick={() => choose(c.role)}>{c.title}</button>
      </div>
    {/each}
  </div>
  <p><a href="{base}/">Back to the home page</a></p>
</section>

<style>
  .login { max-width: 44rem; margin: 1rem auto; }
  .choices { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); margin: 1rem 0; }
  .choices .card { display: flex; flex-direction: column; gap: 0.5rem; }
  .choices .card p { flex: 1; margin: 0; }
  .choices .card h2 { margin: 0; }
  .choices .btn { align-self: flex-start; }
</style>
