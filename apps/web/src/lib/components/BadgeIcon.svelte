<script lang="ts">
  import { badgeLabel, qualityColour, stacksLabel, type Badge } from '$lib/badges';

  // One badge as a small round icon, ringed in its tier's item-quality colour; dimmed until earned. The glyph and
  // text come from the analyzer, so they are only ever interpolated as text.
  let { badge, size = 'small' }: { badge: Badge; size?: 'small' | 'large' } = $props();

  const colour = $derived(qualityColour(badge.quality));
  const stacks = $derived(stacksLabel(badge));
</script>

<span
  class="badge {size}"
  class:dim={badge.tier === 0}
  style={colour ? `--q: ${colour}` : undefined}
  title={badgeLabel(badge)}
  role="img"
  aria-label={badgeLabel(badge)}
>
  <!-- Drawn from an attribute so a dimmed glyph is decoration, not text that has to meet contrast. -->
  <span class="glyph" data-glyph={badge.glyph} aria-hidden="true"></span>
  {#if stacks}<span class="stacks" aria-hidden="true">{stacks}</span>{/if}
</span>

<style>
  .badge {
    --q: var(--line);
    position: relative;
    display: inline-grid;
    place-items: center;
    flex: none;
    border-radius: 50%;
    border: 2px solid var(--q);
    background: color-mix(in srgb, var(--q) 18%, var(--surface));
    box-shadow: 0 0 6px color-mix(in srgb, var(--q) 45%, transparent);
  }
  .small { width: 1.9rem; height: 1.9rem; font-size: 0.95rem; }
  .large { width: 2.6rem; height: 2.6rem; font-size: 1.3rem; }
  .glyph::before { content: attr(data-glyph); }
  .dim { opacity: 0.4; filter: grayscale(1); box-shadow: none; }
  .stacks {
    position: absolute;
    right: -0.45rem;
    bottom: -0.35rem;
    padding: 0 0.2rem;
    border-radius: 4px;
    background: var(--bg);
    border: 1px solid var(--q);
    font-size: 0.6rem;
    line-height: 1.2;
    font-variant-numeric: tabular-nums;
  }
</style>
