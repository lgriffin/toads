<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import '$lib/pond.css';
  import { base } from '$app/paths';
  import { DISCORD_INVITE } from '$lib/application';
  import { FOREVER_LAUNCH, UPCOMING } from '$lib/launch';
  import PondHero from './PondHero.svelte';

  // The one page a raider sees while the launch hold is on: what the hub will open with, in the public pages' pond.
</script>

<svelte:head><title>Coming soon · Toads</title></svelte:head>

<div class="pond-page">
  <PondHero
    title="The pond is filling"
    line="Opens with World of Warcraft: Forever · {FOREVER_LAUNCH.label}"
    lede="You are signed in and on the list. The members' hub opens on launch day; until then, here is what it is being built to do for you."
    toads={['roles/tank-badge', 'roles/healer-badge', 'roles/damage-badge']}
  >
    <a class="medal" href={DISCORD_INVITE} target="_blank" rel="noopener noreferrer">Open the Toads Discord</a>
    <a class="ghost" href="{base}/how-we-raid/">See how we raid</a>
  </PondHero>

  <section class="band dusk" aria-labelledby="soon-h">
    <div class="head">
      <h2 id="soon-h">What opens at launch</h2>
      <p>Three things, built around the guild's own logs and bank rather than a generic guild site.</p>
    </div>
    <ul class="upcoming">
      {#each UPCOMING as u (u.id)}
        <li id={u.id}>
          <img src="{base}/logos/{u.toad}.svg" alt="" width="96" height="115" />
          <div>
            <h3>{u.title}</h3>
            <p>{u.body}</p>
          </div>
        </li>
      {/each}
    </ul>
  </section>

  <section class="band close" aria-labelledby="meantime-h">
    <h2 id="meantime-h">Until launch day</h2>
    <p>
      Raid times, officer posts and the bank bot all run in Discord as they do now. Reserve your names for
      <time datetime={FOREVER_LAUNCH.date}>{FOREVER_LAUNCH.label}</time> and tell the officers who you are bringing.
    </p>
    <div class="actions">
      <a class="ghost" href={DISCORD_INVITE} target="_blank" rel="noopener noreferrer">Open the Toads Discord</a>
      <a class="ghost" href="{base}/story/">Read our story</a>
    </div>
  </section>
</div>

<style>
  .upcoming { list-style: none; margin: 0; padding: 0; display: grid; }
  .upcoming li {
    display: grid;
    grid-template-columns: 6rem minmax(0, 1fr);
    gap: 1.5rem;
    align-items: center;
    padding: 1.6rem 0;
    border-top: 1px solid var(--line);
  }
  .upcoming li:last-child { border-bottom: 1px solid var(--line); }
  .upcoming img { width: 6rem; height: auto; filter: drop-shadow(0 8px 14px rgb(5 3 30 / 0.55)); }
  .upcoming div { display: grid; gap: 0.35rem; }
  .upcoming h3 { font-size: 1.35rem; color: var(--bronze-hi); }
  .upcoming p, .close p { margin: 0; max-width: 62ch; }
  @media (min-width: 48rem) {
    .upcoming li { grid-template-columns: 7rem 16rem minmax(0, 1fr); align-items: baseline; }
    .upcoming img { align-self: center; width: 7rem; }
    .upcoming div { display: contents; }
  }
  .close { justify-items: start; }
</style>
