<script lang="ts">
  import { base } from '$app/paths';
  import { LANDING, MEMBER_FEATURES } from '$lib/landing';

  // null: signed out; a name: signed in. The page is the same for both apart from the call to action.
  // loginHref: /auth/login on the real site, the preview's pretend sign-in on GitHub Pages.
  let { member, loginHref = '/auth/login' }: { member: string | null; loginHref?: string } = $props();
</script>

<section class="hero" aria-labelledby="landing-h">
  <p class="realm">{LANDING.realm} · {LANDING.game}</p>
  <h1 id="landing-h">{LANDING.guild}</h1>
  <p class="tagline">{LANDING.tagline}</p>
  <div class="cta">
    {#if member}
      <a class="btn primary" href="{base}/hub/">Go to your hub</a>
    {:else}
      <a class="btn primary" href={loginHref} data-sveltekit-reload={loginHref === '/auth/login' ? '' : 'off'}
        >Log in with Discord</a
      >
    {/if}
    <a class="btn" href="{base}/recruit/">Apply to raid with us</a>
  </div>
  {#if member}<p class="muted welcome">Welcome back, {member}.</p>{/if}
</section>

<div class="grid">
  <section class="card" aria-labelledby="who-h">
    <h2 id="who-h">Who we are</h2>
    {#each LANDING.who as para}<p>{para}</p>{/each}
    <p><strong>Raid nights:</strong> {LANDING.schedule}.</p>
    <p><a href="{base}/story/">Read our story, progression and highlights</a></p>
  </section>

  <section class="card" aria-labelledby="values-h">
    <h2 id="values-h">What we stand for</h2>
    <ul class="values">
      {#each LANDING.values as v (v.title)}
        <li><strong>{v.title}</strong><span>{v.body}</span></li>
      {/each}
    </ul>
  </section>
</div>

<section class="card members" aria-labelledby="members-h">
  <h2 id="members-h">For members</h2>
  <p class="muted">Sign in with the Discord account you use in the Toads server to open the hub.</p>
  <ul>
    {#each MEMBER_FEATURES as f}<li>{f}</li>{/each}
  </ul>
</section>

<style>
  .hero { padding: 1.5rem 0 1.25rem; }
  .realm { color: var(--accent); margin: 0; font-size: 0.9rem; }
  .hero h1 { font-size: clamp(2rem, 8vw, 3.2rem); margin: 0.25rem 0 0.5rem; }
  .tagline { font-size: 1.1rem; max-width: 40rem; margin: 0 0 1.25rem; }
  .cta { display: flex; flex-wrap: wrap; gap: 0.75rem; }
  .welcome { margin: 0.75rem 0 0; }
  .values { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.75rem; }
  .values li { display: flex; flex-direction: column; gap: 0.2rem; }
  .members { margin-top: 1rem; }
  .members ul { margin: 0; padding-left: 1.2rem; display: grid; gap: 0.3rem; }
</style>
