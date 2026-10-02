<script lang="ts">
  import { base } from '$app/paths';
  import ModelPillars from '$lib/components/ModelPillars.svelte';
  import RaidWeek from '$lib/components/RaidWeek.svelte';
  import { sheetTrend } from '$lib/mock/sheets';

  // How a Toads raid night works, in full: the same pillars as the homepage, each with its approach, how it is
  // measured and what members see. The preview adds the last four raids' guild totals from the sample raid sheets;
  // the real site will once a public summary exists.
  const trend = __PREVIEW__ ? sheetTrend : [];
</script>

<svelte:head><title>How we raid · Toads</title></svelte:head>

<h1>How we raid</h1>
<p class="lede">
  Two nights a week, the same expectations for everyone, and the same numbers on show for everyone. Here is what we ask
  of raiders, how we measure it and what you see once you join.
</p>

<ModelPillars {trend} />

<section class="week" aria-labelledby="week-h">
  <h2 id="week-h">A raid week in the pond</h2>
  <RaidWeek />
</section>

<p class="next">
  <a class="btn primary" href="{base}/recruit/">Apply to raid with us</a>
  <a class="btn" href="{base}/story/">Read our story</a>
</p>

<style>
  .lede { max-width: 44rem; margin: 0 0 1.5rem; }
  .week { margin-top: 2rem; display: grid; gap: 0.75rem; }
  .week h2 { margin: 0; }
  .next { margin-top: 1.5rem; display: flex; flex-wrap: wrap; gap: 0.75rem; }
</style>
