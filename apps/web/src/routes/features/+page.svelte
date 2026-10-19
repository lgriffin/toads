<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import '$lib/pond.css';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { getSession, type Session } from '$lib/api';
  import {
    APPS,
    FEATURE_LABEL,
    LOCKED,
    TIER_LABEL,
    featureTier,
    held,
    needsRole,
    raidRoleOf,
    standing,
    tierOf,
    unlocked,
    type App,
    type RaidRole,
    type Tier
  } from '$lib/access';
  import { FOREVER_LAUNCH } from '$lib/launch';
  import type { PreviewRole } from '$lib/preview/gate';
  import { previewSession } from '$lib/preview/session.svelte';
  import PondHero from '$lib/components/PondHero.svelte';

  // Hub features: a public page where anyone can see what the hub does for each tier, across the three apps. Signed
  // out, the raider and officer columns are dimmed so a visitor sees what joining gets them. The routes behind each
  // line check their own permission; this page only explains.
  let session = $state<Session | null | undefined>(undefined);
  onMount(async () => {
    if (!__PREVIEW__) session = await getSession().catch(() => null);
  });
  const PREVIEW_TIER: Record<PreviewRole, Tier> = { member: 'raider', officer: 'officer', admin: 'admin' };
  let tier = $derived<Tier>(
    __PREVIEW__ ? (previewSession.role ? PREVIEW_TIER[previewSession.role] : 'visitor') : tierOf(session)
  );
  let shownAs = $derived(featureTier(tier));
  // Raider lines a plain member or a trial does not hold yet say which role they need. The preview's Hopscotch raids
  // both nights.
  let raidRole = $derived<RaidRole>(__PREVIEW__ ? 'raider' : raidRoleOf(session));
  let signedIn = $derived(tier !== 'visitor');

  const TOAD: Record<App['id'], string> = {
    analyzer: 'milestones/raids-50-badge',
    bank: 'ranks/banker-badge',
    discord: 'ranks/officer-badge'
  };
</script>

<svelte:head><title>Hub features · Toads</title></svelte:head>

<div class="pond-page">
  <PondHero
    title="Hub features"
    line="Opens with World of Warcraft: Forever · {FOREVER_LAUNCH.label}"
    lede="The Toads Hub joins up our raid logs, the guild bank and Discord, behind the Discord account you already use with us. Here is what it does for everyone, for raiders and for officers."
    toads={[TOAD.analyzer, TOAD.bank, TOAD.discord]}
  >
    {#if signedIn}
      <a class="medal" href="{base}/hub/">Go to your hub</a>
    {:else}
      <a class="medal" href="{base}/recruit/">Apply to raid with us</a>
    {/if}
    <a class="ghost" href="{base}/how-we-raid/">See how we raid</a>
  </PondHero>

  <p class="standing band" role="status">
    <span class="you">{signedIn ? `You: ${TIER_LABEL[shownAs]}` : 'Signed out'}</span>
    {standing(tier)}
  </p>

  {#each APPS as app, i (app.id)}
    <section class="band app" class:dusk={i % 2 === 0} aria-labelledby="{app.id}-h">
      <header>
        <img src="{base}/logos/{TOAD[app.id]}.svg" alt="" width="96" height="115" loading="lazy" />
        <div>
          <h2 id="{app.id}-h">{app.title}</h2>
          <p>{app.where}</p>
        </div>
      </header>
      <ol class="ladder" aria-label="{app.title} by role">
        {#each app.rows as row (row.tier)}
          {@const open = unlocked(row, shownAs)}
          <li class="step" class:locked={!open} class:here={signedIn && row.tier === shownAs} data-tier={row.tier}>
            <h3>
              {FEATURE_LABEL[row.tier]}
              {#if signedIn && row.tier === shownAs}<span class="mark">You</span>{/if}
            </h3>
            {#if !open}<p class="lock">{LOCKED[row.tier]}</p>{/if}
            <ul>
              {#each row.can as c (c.text)}
                {#if open && !held(c, raidRole)}
                  <li class="needs" data-needs={needsRole(c)}>
                    {c.text} <span class="muted">(needs a {needsRole(c)} role on a raid night)</span>
                  </li>
                {:else}
                  <li>{c.text}</li>
                {/if}
              {/each}
            </ul>
          </li>
        {/each}
      </ol>
    </section>
  {/each}

  <section class="band close" class:dusk={APPS.length % 2 === 0} aria-labelledby="launch-h">
    <h2 id="launch-h">Opening with Forever</h2>
    <p>
      The raid analyser and the guild bank open to members through the hub once World of Warcraft: Forever releases on
      <time datetime={FOREVER_LAUNCH.date}>{FOREVER_LAUNCH.label}</time>. Until then, raid times, officer posts and the
      bank bot run in Discord.
    </p>
    <div class="actions">
      {#if !signedIn}<a class="medal" href="{base}/recruit/">Apply to raid with us</a>{/if}
      <a class="ghost" href="{base}/story/">Read our story</a>
    </div>
  </section>
</div>

<style>
  .standing {
    padding: 1.1rem 0;
    margin: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.9rem;
    color: var(--muted);
    border-bottom: 1px solid var(--line);
  }
  .you {
    font-family: 'Cinzel', Georgia, serif;
    font-weight: 600;
    letter-spacing: 0.08em;
    color: var(--ink);
    background: var(--bronze-hi);
    border-radius: 999px;
    padding: 0.2rem 0.8rem;
    font-size: 0.85rem;
  }

  .app { gap: 1.75rem; }
  .app header { display: grid; grid-template-columns: 5rem minmax(0, 1fr); gap: 1.25rem; align-items: center; }
  .app header img { width: 5rem; height: auto; filter: drop-shadow(0 8px 14px rgb(5 3 30 / 0.55)); }
  .app header h2 { font-size: clamp(1.6rem, 4vw, 2.2rem); color: var(--bronze-hi); }
  .app header p { margin: 0.25rem 0 0; color: var(--muted); max-width: 60ch; }

  /* The three tiers read as one climb: a bronze rail runs under the column heads, and each step adds to the last. */
  .ladder {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    position: relative;
  }
  .ladder::before {
    content: '';
    position: absolute;
    top: 1.85rem;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(to right, var(--bronze), rgb(217 168 90 / 0.15));
  }
  .step { position: relative; padding: 0 1.5rem 0 0; display: grid; gap: 0.6rem; align-content: start; min-width: 0; }
  .step + .step { padding-left: 1.5rem; border-left: 1px solid var(--line); }
  .step h3 {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--bronze-hi);
    background: inherit;
    padding-bottom: 0.4rem;
  }
  .mark {
    font-family: 'Alegreya Sans', system-ui, sans-serif;
    letter-spacing: 0.04em;
    text-transform: none;
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--ink);
    background: var(--teal);
    border-radius: 999px;
    padding: 0.05rem 0.55rem;
  }
  .step ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 0.5rem; }
  .step ul li { padding-left: 1.1rem; position: relative; }
  .step ul li::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.62em;
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 50%;
    background: var(--teal);
  }
  .step.here ul li::before { background: var(--bronze-hi); }
  .needs .muted { color: var(--muted); font-size: 0.92em; }
  .lock { margin: 0; font-style: italic; color: var(--muted); font-size: 0.95rem; }
  .locked h3 { color: var(--muted); }
  .locked ul { color: var(--muted); }
  .locked ul li::before { background: transparent; border: 1px solid var(--muted); }

  .close { justify-items: start; }
  .close p { margin: 0; max-width: 62ch; }

  @media (max-width: 52rem) {
    .ladder { grid-template-columns: 1fr; gap: 1.5rem; }
    .ladder::before { display: none; }
    .step,
    .step + .step { padding: 0 0 0 1.1rem; border-left: 1px solid var(--bronze); }
    .locked,
    .step.locked + .step { border-left-color: var(--line); }
  }
</style>
