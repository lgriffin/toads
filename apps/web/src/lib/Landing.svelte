<script lang="ts">
  import '@fontsource/cinzel/600.css';
  import '@fontsource/cinzel/700.css';
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/500.css';
  import '@fontsource/alegreya-sans/700.css';
  import { base } from '$app/paths';
  import { DISCORD_INVITE } from '$lib/application';
  import { FOREVER_LAUNCH } from '$lib/launch';
  import { HOMES, LANDING, MEMBER_APPS, RECRUITING, SOCIAL } from '$lib/landing';
  import { RECORD_GROUPS, clearClock, reportUrl } from '$lib/records';
  import { CLASS_COLOUR, classToad, roleToad, toadSrc } from '$lib/toads';
  import type { GuildPulse as Pulse } from '$lib/pulse';
  import BrandLogo from './components/BrandLogo.svelte';
  import GuildPulse from './components/GuildPulse.svelte';
  import ModelPillars from './components/ModelPillars.svelte';
  import PondScene from './components/PondScene.svelte';
  import ToadsMark from './components/ToadsMark.svelte';

  // null: signed out; a name: signed in. The page is the same for both apart from the calls to action.
  // loginHref: /auth/login on the real site, the preview's pretend sign-in on GitHub Pages.
  // pulse: guild-level facts (next raid, progression, clear times); left out until there is data to show.
  let {
    member,
    loginHref = '/auth/login',
    pulse = null
  }: { member: string | null; loginHref?: string; pulse?: Pulse | null } = $props();
  const reload = $derived(loginHref === '/auth/login' ? '' : 'off');

  // Horde key art from Blizzard's press kit, saved by the guild as static/art/horde-key-art.jpg. Without the file the
  // painted pond scene stands alone.
  const shortMonth = (iso: string) =>
    new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' });
  let logoFailed = $state<Record<string, boolean>>({ forever: false, tbc: false });
  let artFailed = $state(false);
  let mounted = $state(false);
  $effect(() => {
    mounted = true;
  });
</script>

<div class="pond">
  <section class="hero band always-dusk" aria-labelledby="landing-h">
    <div class="backdrop" aria-hidden="true">
      <PondScene />
      {#if mounted && !artFailed}
        <img
          class="art"
          src="{base}/art/horde-key-art.jpg"
          alt=""
          onerror={() => (artFailed = true)}
        />
      {/if}
      <div class="veil"></div>
    </div>

    <div class="seal">
      <span class="ripple"></span>
      <ToadsMark size={168} title="The Toads medallion" />
    </div>
    <h1 id="landing-h">{LANDING.guild}</h1>
    <p class="line">Horde · PvP · EU</p>
    <p class="tagline">{LANDING.tagline}</p>
    <div class="cta">
      {#if member}
        <a class="medal" href="{base}/hub/">Go to your hub</a>
      {:else}
        <a class="medal" href="{base}/recruit/">Apply to raid with us</a>
      {/if}
      <a class="ghost" href="{base}/how-we-raid/">See how we raid</a>
    </div>
    {#if member}
      <p class="welcome">Welcome back, {member}. New here? <a href="{base}/welcome/">Start with the checklist</a>.</p>
    {/if}
  </section>

  <section class="homes band" aria-labelledby="homes-h">
    <h2 id="homes-h">Two ponds, one guild</h2>
    <ul>
      {#each HOMES as home (home.id)}
        <li id={home.id}>
          {#if !logoFailed[home.id]}
            <div class="logo">
              <BrandLogo
                src="{base}/{home.logo.src}"
                alt={home.logo.alt}
                height={home.id === 'forever' ? 150 : 110}
                bind:failed={logoFailed[home.id]}
              />
            </div>
          {/if}
          <p class="status" class:live={home.id === 'tbc'}>{home.status}</p>
          <h3>{home.title}</h3>
          <p class="faction">{home.line}</p>
          <p>{home.body}</p>
        </li>
      {/each}
    </ul>
  </section>

  <section class="records band" aria-labelledby="records-h">
    <div class="head">
      <h2 id="records-h">Our fastest clears</h2>
      <p>The best full-clear time we have logged in each raid, with the report to prove it.</p>
    </div>
    <div class="rec-groups">
      {#each RECORD_GROUPS as g (g.id)}
        <section aria-labelledby="rec-{g.id}">
          <h3 id="rec-{g.id}">{g.title}</h3>
          <p class="faction">{g.blurb}</p>
          <ol class="rec">
            {#each g.records as r (r.raid)}
              <li>
                <span class="raid">{r.raid}</span>
                <a class="time" href={reportUrl(r.code)} rel="noopener noreferrer" target="_blank"
                  >{clearClock(r.ms)}<span class="sr-only"> on Warcraft Logs, {shortMonth(r.date)}</span></a
                >
                <time class="when" datetime={r.date}>{shortMonth(r.date)}</time>
              </li>
            {/each}
          </ol>
        </section>
      {/each}
    </div>
  </section>

  <section class="recruit band" aria-labelledby="recruit-h">
    <div class="head">
      <h2 id="recruit-h">Who we are looking for</h2>
      <p>Healers and damage dealers of every class are welcome. Tanks are full for now.</p>
    </div>
    <div class="roles">
      {#each RECRUITING as role (role.id)}
        {@const toad = roleToad(role.id === 'damage' ? 'Melee' : role.id === 'healer' ? 'Healer' : 'Tank')}
        <section class="role" class:full={!role.open} aria-labelledby="role-{role.id}">
          <div class="role-head">
            {#if toad}<img src={toadSrc(base, toad, true)} alt="" width="110" height="132" loading="lazy" />{/if}
            <div>
              <h3 id="role-{role.id}">{role.title}</h3>
              <p class="state" class:open={role.open}>{role.open ? 'Recruiting' : 'Full for now'}</p>
            </div>
          </div>
          <p class="note">{role.note}</p>
          {#if role.classes.length}
            <ul class="classes">
              {#each role.classes as c (c.name)}
                {@const ct = classToad(c.name)}
                <li style="--c: {CLASS_COLOUR[c.name.toLowerCase()]}">
                  {#if ct}<img src={toadSrc(base, ct)} alt="" width="48" height="42" loading="lazy" />{/if}
                  <span class="cname">{c.name}</span>
                  <span class="specs">{c.specs.join(', ')}</span>
                </li>
              {/each}
            </ul>
          {/if}
        </section>
      {/each}
    </div>
    <p class="apply-how">
      Applying is six questions. Join our Discord first: the moment you send them, the Toad Bot opens a private
      interview room there for you and our recruitment officers.
    </p>
    <p class="cta left">
      <a class="medal" href="{base}/recruit/">Apply to raid with us</a>
      <a class="ghost" href={DISCORD_INVITE} target="_blank" rel="noopener noreferrer"
        >Join our Discord<span class="sr-only"> (opens in a new tab)</span></a
      >
      <a class="ghost" href="{base}/how-we-raid/">See what we expect</a>
    </p>
  </section>

  {#if pulse}<div class="band pulse"><GuildPulse {pulse} /></div>{/if}

  <section class="who band" aria-labelledby="who-h">
    <h2 id="who-h">Who we are</h2>
    <div class="story">
      {#each LANDING.who as para}<p>{para}</p>{/each}
      <p class="when">We raid as {LANDING.schedule}.</p>
      <p><a href="{base}/story/">Read our story, progression and highlights</a></p>
    </div>
  </section>

  <section class="rules band" aria-labelledby="values-h">
    <h2 id="values-h">What we stand for</h2>
    <ol>
      {#each LANDING.values as v (v.title)}
        <li><h3>{v.title}</h3><p>{v.body}</p></li>
      {/each}
    </ol>
  </section>

  <section class="social band" aria-labelledby="social-h">
    <div class="social-grid">
      <div class="social-text">
        <h2 id="social-h">{SOCIAL.title}</h2>
        <p class="big">{SOCIAL.intro}</p>
        <ul class="points">
          {#each SOCIAL.points as p (p.title)}
            <li><h3>{p.title}</h3><p>{p.body}</p></li>
          {/each}
        </ul>
      </div>
      <img class="pond-art" src="{base}/logos/pond-medallion.svg" alt="Toads sharing a pond: a croaking toad, one chasing a firefly and one asleep on a lily pad" width="300" height="300" loading="lazy" />
    </div>
  </section>

  <section class="band" aria-labelledby="model-h">
    <div class="head">
      <h2 id="model-h">How a Toads raid night works</h2>
      <p>What we expect, how we measure it and what you see once you join. Everyone sees the same numbers.</p>
    </div>
    <ModelPillars compact />
    <p><a href="{base}/how-we-raid/">Read how we raid in full</a></p>
  </section>

  <section class="band" aria-labelledby="apps-h">
    <div class="head">
      <h2 id="apps-h">What opens when you join</h2>
      <p>Sign in with the Discord account you use in the Toads server. Officers get more on top.</p>
    </div>
    <p class="opens">
      Once World of Warcraft: Forever releases on {FOREVER_LAUNCH.label}, our raid analyser and guild bank open to
      members through the hub.
    </p>
    <ul class="apps">
      {#each MEMBER_APPS as app (app.title)}
        <li><h3>{app.title}</h3><p>{app.body}</p></li>
      {/each}
    </ul>
    <p class="cta">
      {#if !member}<a class="medal" href={loginHref} data-sveltekit-reload={reload}>Log in with Discord</a>{/if}
      <a class="ghost" href="{base}/features/">See the hub’s features</a>
    </p>
  </section>
</div>

<style>
  /* The pond's palette (WoW Forever key art: twilight violet, a teal medallion, bronze and cream) is the hub's own
     theme, so the bands follow the reader's light or dark choice. The hero stays at dusk (.always-dusk): its text sits
     on the night-time key art. */
  .pond {
    font-family: 'Alegreya Sans', system-ui, sans-serif;
    font-size: 1.1rem;
    line-height: 1.5;
    color: var(--text);
    display: grid;
  }
  .pond :global(a) { color: var(--teal); }
  .pond :global(a:hover) { color: var(--bronze-hi); }
  .pond :global(a:focus-visible),
  .pond :global(button:focus-visible) { outline: 2px solid var(--bronze-hi); outline-offset: 3px; }
  .pond ::selection { background: var(--bronze); color: var(--on-bronze); }

  /* Each band paints edge to edge behind the centred column, without a horizontal scrollbar. */
  .band {
    position: relative;
    background: var(--ink);
    box-shadow: 0 0 0 100vmax var(--ink);
    clip-path: inset(0 -100vmax);
    padding: 3.5rem 0;
    display: grid;
    gap: 1rem;
  }
  .band:nth-of-type(even) { background: var(--dusk); box-shadow: 0 0 0 100vmax var(--dusk); }
  h1, h2, h3 { font-family: 'Cinzel', Georgia, serif; font-weight: 600; letter-spacing: 0.03em; margin: 0; }
  h2 { font-size: clamp(1.5rem, 4vw, 2.1rem); color: var(--bronze-hi); text-wrap: balance; }
  h3 { font-size: 1.15rem; color: var(--cream); }
  p { margin: 0; max-width: 62ch; }
  .head { display: grid; gap: 0.35rem; }
  .head p { color: var(--muted); }

  /* Hero */
  .hero {
    overflow-x: clip;
    min-height: min(46rem, 92svh);
    padding: 3rem 0 4rem;
    justify-items: center;
    align-content: center;
    text-align: center;
    background: var(--ink);
    gap: 0.6rem;
  }
  .backdrop {
    position: absolute;
    inset: 0;
    overflow: hidden;
    mask-image: linear-gradient(to right, transparent, #000 14%, #000 86%, transparent);
  }
  .backdrop :global(svg) { position: absolute; inset: 0; }
  .art { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 40%; opacity: 1; }
  .veil { position: absolute; inset: 0; background: radial-gradient(ellipse 60% 55% at 50% 52%, rgb(18 15 51 / 0.72), transparent 75%), linear-gradient(to bottom, rgb(18 15 51 / 0.5), rgb(18 15 51 / 0.05) 35%, rgb(18 15 51 / 0.85)); }
  .hero > :not(.backdrop) { position: relative; }
  .seal { position: relative; display: grid; place-items: center; filter: drop-shadow(0 10px 22px rgb(5 3 30 / 0.6)); }
  .ripple {
    position: absolute;
    width: 11rem;
    height: 11rem;
    border-radius: 50%;
    border: 2px solid var(--teal);
    opacity: 0;
    animation: ripple 2.6s 0.4s cubic-bezier(0.16, 1, 0.3, 1) 2;
  }
  .hero h1 { font-size: clamp(3rem, 12vw, 6rem); color: var(--cream); letter-spacing: 0.12em; text-shadow: 0 2px 18px rgb(5 3 30 / 0.7); }
  .line { font-family: 'Cinzel', Georgia, serif; letter-spacing: 0.22em; text-transform: uppercase; color: var(--bronze-hi); font-size: 0.95rem; }
  .tagline { font-size: 1.3rem; text-shadow: 0 1px 10px rgb(5 3 30 / 0.8); text-wrap: balance; }
  .cta { display: flex; flex-wrap: wrap; gap: 0.75rem; justify-content: center; margin-top: 0.8rem; }
  .welcome { color: var(--muted); }

  .medal, .ghost {
    display: inline-block;
    padding: 0.7rem 1.4rem;
    border-radius: 999px;
    font-family: 'Cinzel', Georgia, serif;
    font-weight: 600;
    letter-spacing: 0.06em;
    font-size: 0.95rem;
    text-decoration: none;
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), background 0.2s;
  }
  .pond a.medal { background: linear-gradient(#f4dc9c, #c58f45); color: #2a1706; border: 1px solid #7a4f23; box-shadow: 0 3px 10px rgb(5 3 30 / 0.5), inset 0 1px 0 #fff3c4; }
  .pond a.medal:hover { color: #2a1706; transform: translateY(-2px); }
  .pond a.ghost { color: var(--cream); border: 1px solid var(--bronze); background: color-mix(in srgb, var(--ink) 45%, transparent); }
  .pond a.ghost:hover { background: color-mix(in srgb, var(--teal) 18%, transparent); color: var(--cream); }

  /* Two homes */
  .homes ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 2.5rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); }
  .homes li { display: grid; gap: 0.5rem; align-content: start; }
  .logo { min-height: 9.5rem; display: flex; align-items: flex-end; margin-bottom: 0.5rem; }
  .status { color: var(--bronze-hi); font-weight: 700; letter-spacing: 0.05em; }
  .status.live::before { content: ''; display: inline-block; width: 0.55em; height: 0.55em; border-radius: 50%; background: var(--teal); margin-right: 0.5em; box-shadow: 0 0 0 3px rgb(63 214 200 / 0.25); }
  .faction { color: var(--muted); font-family: 'Cinzel', Georgia, serif; font-size: 0.9rem; letter-spacing: 0.1em; text-transform: uppercase; }

  .pulse { padding: 2rem 0; }

  /* Who we are, values */
  .who { grid-template-columns: minmax(0, 1fr); }
  .story { display: grid; gap: 1rem; font-size: 1.2rem; }
  .when { color: var(--bronze-hi); }
  .rules ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 0; }
  .rules li { display: grid; gap: 0.3rem 3rem; padding: 1.4rem 0; border-top: 1px solid var(--line); }
  .rules li:last-child { border-bottom: 1px solid var(--line); }
  @media (min-width: 48rem) {
    .rules li { grid-template-columns: 16rem minmax(0, 1fr); align-items: baseline; }
  }
  .rules h3 { font-size: 1.3rem; color: var(--bronze-hi); }

  .opens { margin: 0; max-width: 62ch; padding: 0.8rem 1.1rem; border: 1px solid var(--bronze); border-radius: 10px; background: color-mix(in srgb, var(--bronze) 10%, transparent); color: var(--cream); }
  .apps { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
  .apps li { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1.1rem; display: grid; gap: 0.3rem; align-content: start; }
  .cta:last-child { justify-content: flex-start; }


  /* Fastest clears */
  .rec-groups { display: grid; gap: 2rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr)); }
  .rec { list-style: none; margin: 0.6rem 0 0; padding: 0; }
  .rec li { display: grid; grid-template-columns: 1fr auto 5.5rem; gap: 1rem; align-items: baseline; padding: 0.7rem 0; border-top: 1px solid var(--line); }
  .rec li:last-child { border-bottom: 1px solid var(--line); }
  .raid { font-family: 'Cinzel', Georgia, serif; font-weight: 600; letter-spacing: 0.03em; }
  .pond .time { font-family: 'Cinzel', Georgia, serif; font-weight: 700; font-size: 1.5rem; font-variant-numeric: tabular-nums; color: var(--bronze-hi); text-decoration: none; }
  .pond .time:hover { color: var(--teal); text-decoration: underline; }
  .when { color: var(--muted); text-align: right; font-size: 0.95rem; }

  /* Recruiting */
  .roles { display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); align-items: start; }
  .role { display: grid; gap: 0.7rem; align-content: start; }
  .role-head { display: flex; gap: 1rem; align-items: center; }
  .role-head img { width: 110px; height: auto; flex: none; }
  .role.full .role-head img { filter: grayscale(0.85) brightness(0.8); }
  .state { font-weight: 700; letter-spacing: 0.05em; color: var(--muted); }
  .state.open { color: var(--teal); }
  .state.open::before { content: ''; display: inline-block; width: 0.55em; height: 0.55em; border-radius: 50%; background: var(--teal); margin-right: 0.5em; box-shadow: 0 0 0 3px rgb(63 214 200 / 0.25); }
  .note { color: var(--muted); }
  .classes { list-style: none; margin: 0.3rem 0 0; padding: 0; display: grid; gap: 0; }
  .classes li { display: grid; grid-template-columns: 3rem 1fr; grid-template-areas: 'i n' 'i s'; column-gap: 0.7rem; align-items: center; padding: 0.55rem 0; border-top: 1px solid var(--line); }
  .classes img { grid-area: i; width: 3rem; height: auto; }
  .cname { grid-area: n; font-family: 'Cinzel', Georgia, serif; font-weight: 600; letter-spacing: 0.04em; color: color-mix(in srgb, var(--c) var(--class-mix), var(--cream)); border-bottom: 2px solid var(--c); justify-self: start; line-height: 1.2; }
  .specs { grid-area: s; color: var(--muted); font-size: 0.95rem; }
  .cta.left { justify-content: flex-start; }
  .apply-how { max-width: 60ch; margin: 1.5rem 0 0; color: var(--muted); }

  /* Social */
  .social-grid { display: grid; gap: 2rem; align-items: center; }
  @media (min-width: 52rem) { .social-grid { grid-template-columns: minmax(0, 1fr) 18rem; } }
  .social-text { display: grid; gap: 1rem; }
  .big { font-size: 1.25rem; }
  .points { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; }
  .points li { display: grid; gap: 0.15rem; }
  .pond-art { width: 100%; max-width: 18rem; height: auto; justify-self: center; filter: drop-shadow(0 10px 22px rgb(5 3 30 / 0.55)); }

  @keyframes ripple {
    from { transform: scale(0.8); opacity: 0.8; }
    to { transform: scale(2.4); opacity: 0; }
  }
  @media (prefers-reduced-motion: reduce) {
    .ripple { animation: none; }
    .medal { transition: none; }
  }
</style>
