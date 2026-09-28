<script lang="ts">
  import { countdown, localStart, signupLink, type NextRaid } from '$lib/next-raid';

  // The next raid (GET /api/home/next-raid). Event names come from Discord, so they are only interpolated as text.
  let { raid, now }: { raid: NextRaid | null; now: Date } = $props();

  const link = $derived(raid ? signupLink(raid) : null);
</script>

<section class="card" aria-labelledby="next-h">
  <h2 id="next-h">Next raid</h2>
  {#if raid}
    <p class="big">{raid.name}</p>
    <p>
      <time datetime={raid.starts_at}>{localStart(raid.starts_at)}</time>
      <span class="muted">· {countdown(raid.starts_at, now, raid.under_way)}</span>
    </p>
    <p class="muted">
      {#if raid.raid_day_name}{raid.raid_day_name} team{/if}
      {#if raid.source === 'discord'}
        {#if raid.interested !== null}{raid.raid_day_name ? ' · ' : ''}{raid.interested} signed up in Discord{/if}
      {:else}
        {raid.raid_day_name ? ' · ' : ''}usual start time; no Discord event posted yet
      {/if}
    </p>
    {#if link}<a href={link} target="_blank" rel="noopener noreferrer">Sign up in Discord</a>{/if}
  {:else}
    <p class="muted">No raid is scheduled. Officers post raids as Discord events.</p>
  {/if}
</section>

<style>
  .big { font-size: 1.3rem; margin: 0; }
</style>
