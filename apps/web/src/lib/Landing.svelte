<script lang="ts">
  import { base } from '$app/paths';
  import { LANDING, MEMBER_APPS } from '$lib/landing';
  import type { GuildPulse as Pulse } from '$lib/pulse';
  import GuildPulse from './components/GuildPulse.svelte';
  import ModelPillars from './components/ModelPillars.svelte';
  import RaidWeek from './components/RaidWeek.svelte';

  // null: signed out; a name: signed in. The page is the same for both apart from the calls to action.
  // loginHref: /auth/login on the real site, the preview's pretend sign-in on GitHub Pages.
  // pulse: guild-level facts (next raid, progression, clear times); left out until there is data to show.
  let {
    member,
    loginHref = '/auth/login',
    pulse = null
  }: { member: string | null; loginHref?: string; pulse?: Pulse | null } = $props();
  const reload = $derived(loginHref === '/auth/login' ? '' : 'off');
</script>

<section class="hero" aria-labelledby="landing-h">
  <p class="realm">{LANDING.realm} · {LANDING.game}</p>
  <h1 id="landing-h">{LANDING.guild}</h1>
  <p class="tagline">{LANDING.tagline}</p>
  <div class="cta">
    {#if member}
      <a class="btn primary" href="{base}/hub/">Go to your hub</a>
    {:else}
      <a class="btn primary" href="{base}/recruit/">Apply to raid with us</a>
    {/if}
    <a class="btn" href="{base}/how-we-raid/">See how we raid</a>
  </div>
  {#if member}<p class="muted welcome">Welcome back, {member}.</p>{/if}
</section>

{#if pulse}<GuildPulse {pulse} />{/if}

<section class="block" aria-labelledby="model-h">
  <div class="head">
    <h2 id="model-h">How a Toads raid night works</h2>
    <p class="muted">What we expect, how we measure it and what you see once you join. Everyone sees the same numbers.</p>
  </div>
  <ModelPillars compact />
  <p><a href="{base}/how-we-raid/">Read how we raid in full</a></p>
</section>

<section class="block" aria-labelledby="week-h">
  <h2 id="week-h">A raid week in the pond</h2>
  <RaidWeek />
</section>

<section class="block" aria-labelledby="apps-h">
  <div class="head">
    <h2 id="apps-h">What opens when you join</h2>
    <p class="muted">Sign in with the Discord account you use in the Toads server. Officers get more on top.</p>
  </div>
  <ul class="apps">
    {#each MEMBER_APPS as app (app.title)}
      <li class="card"><h3>{app.title}</h3><p>{app.body}</p></li>
    {/each}
  </ul>
  <p class="cta">
    {#if !member}<a class="btn primary" href={loginHref} data-sveltekit-reload={reload}>Log in with Discord</a>{/if}
    <a class="btn" href="{base}/toolkit/">See what each role can do</a>
  </p>
</section>

<div class="grid block">
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

<style>
  .hero { padding: 1.5rem 0 1.25rem; }
  .realm { color: var(--accent); margin: 0; font-size: 0.9rem; }
  .hero h1 { font-size: clamp(2rem, 8vw, 3.2rem); margin: 0.25rem 0 0.5rem; }
  .tagline { font-size: 1.1rem; max-width: 40rem; margin: 0 0 1.25rem; }
  .cta { display: flex; flex-wrap: wrap; gap: 0.75rem; }
  .welcome { margin: 0.75rem 0 0; }
  .block { margin-top: 2rem; display: grid; gap: 1rem; }
  .block > p { margin: 0; }
  .head { display: grid; gap: 0.25rem; }
  .head h2, .block > h2 { margin: 0; font-size: 1.3rem; }
  .head p { margin: 0; }
  .apps { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
  .apps h3 { margin: 0 0 0.3rem; font-size: 1.05rem; }
  .apps p { margin: 0; }
  .values { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.75rem; }
  .values li { display: flex; flex-direction: column; gap: 0.2rem; }
</style>
