<script lang="ts">
  import { countdown, localStart } from '$lib/next-raid';
  import { fastestClear, minutes, totalProgress, type GuildPulse } from '$lib/pulse';
  import { clearTime } from '$lib/sheets';

  // Three guild-level facts for the public homepage. Signups and names stay behind the login.
  let { pulse }: { pulse: GuildPulse } = $props();

  const progress = $derived(totalProgress(pulse.progression));
  const fastest = $derived(fastestClear(pulse.trend));
  const shortDate = (iso: string) =>
    new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', timeZone: 'UTC' });
</script>

<section class="pulse" aria-label="The guild right now">
  <div class="card">
    <h2>Next raid</h2>
    {#if pulse.next}
      <p class="big"><time datetime={pulse.next.starts_at}>{localStart(pulse.next.starts_at)}</time></p>
      <p class="muted">{pulse.next.name} · {countdown(pulse.next.starts_at, pulse.now, pulse.next.under_way)}</p>
    {:else}
      <p class="muted">Officers post raids as Discord events.</p>
    {/if}
  </div>
  <div class="card">
    <h2>Progression</h2>
    <p class="big">{progress.killed} / {progress.total} bosses</p>
    <p class="muted">{pulse.progression.map((z) => `${z.zone} ${z.killed}/${z.total}`).join(' · ')}</p>
  </div>
  <div class="card">
    <h2>Fastest clear</h2>
    {#if fastest}
      <p class="big">{fastest.zone} in {clearTime(fastest.seconds)}</p>
      <p class="muted">
        {#if fastest.saved}
          {minutes(fastest.saved)} faster than on {shortDate(fastest.since)}
        {:else if fastest.clears > 1}
          Our best since {shortDate(fastest.since)}
        {:else}
          Our first timed clear
        {/if}
      </p>
    {:else}
      <p class="muted">Clear times appear after the next raid sheet.</p>
    {/if}
  </div>
</section>

<style>
  .pulse { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr)); }
  .pulse .card { display: grid; gap: 0.25rem; align-content: start; }
  .pulse h2 { margin: 0; font-size: 0.85rem; color: var(--muted); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
  .big { font-size: 1.35rem; font-weight: 600; margin: 0; font-variant-numeric: tabular-nums; }
  p { margin: 0; }
</style>
