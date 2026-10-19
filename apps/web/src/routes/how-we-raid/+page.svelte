<script lang="ts">
  import '@fontsource/alegreya-sans/400.css';
  import '@fontsource/alegreya-sans/700.css';
  import '$lib/pond.css';
  import { base } from '$app/paths';
  import ModelPillars from '$lib/components/ModelPillars.svelte';
  import PondHero from '$lib/components/PondHero.svelte';
  import RaidWeek from '$lib/components/RaidWeek.svelte';
  import { sheetTrend } from '$lib/mock/sheets';

  // How a Toads raid night works, in full: the same pillars as the homepage, each with its approach, how it is
  // measured and what members see. The preview adds the last four raids' guild totals from the sample raid sheets;
  // the real site will once a public summary exists.
  const trend = __PREVIEW__ ? sheetTrend : [];
</script>

<svelte:head><title>How we raid · Toads</title></svelte:head>

<div class="pond-page">
  <PondHero
    title="How we raid"
    line="Wednesday and Sunday · 21:00 to midnight"
    lede="Two nights a week, the same expectations for everyone, and the same numbers on show for everyone. Here is what we ask of raiders, how we measure it and what you see once you join."
    toads={['roles/tank-badge', 'roles/healer-badge', 'roles/damage-badge']}
  >
    <a class="medal" href="{base}/recruit/">Apply to raid with us</a>
    <a class="ghost" href="{base}/story/">Read our story</a>
  </PondHero>

  <section class="band dusk" aria-labelledby="pillars-h">
    <div class="head">
      <h2 id="pillars-h">Six things we ask</h2>
      <p>Each one says what we expect, how the hub measures it and what you see once you are in.</p>
    </div>
    <ModelPillars {trend} />
  </section>

  <section class="band" aria-labelledby="week-h">
    <h2 id="week-h">A raid week in the pond</h2>
    <RaidWeek />
  </section>

  <section class="band dusk close" aria-labelledby="next-h">
    <h2 id="next-h">Sound like your kind of pond?</h2>
    <p>Tell us who you play. You will be talking to our officers in a private Discord room within a minute.</p>
    <div class="actions">
      <a class="medal" href="{base}/recruit/">Apply to raid with us</a>
      <a class="ghost" href="{base}/story/">Read our story</a>
    </div>
  </section>
</div>

<style>
  .close { justify-items: start; }
  .close p { margin: 0; max-width: 56ch; }
</style>
