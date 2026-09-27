<script lang="ts">
  import type { Spotlight } from '$lib/community';

  let { spotlight, headingLevel = 3 }: { spotlight: Spotlight; headingLevel?: 3 | 4 } = $props();
</script>

<article class="spot">
  <p class="who">
    <span class="avatar" aria-hidden="true">{spotlight.characterName.slice(0, 1)}</span>
    <span><strong>{spotlight.characterName}</strong> <span class="muted">{spotlight.className}</span></span>
  </p>
  <svelte:element this={`h${headingLevel}`} class="headline">{spotlight.headline}</svelte:element>
  <p class="body">{spotlight.body}</p>
  <p class="muted small">Written by {spotlight.writtenBy}</p>
</article>

<style>
  .spot { min-width: 0; }
  .who { display: flex; align-items: center; gap: 0.6rem; margin: 0 0 0.5rem; }
  .avatar {
    display: grid;
    place-items: center;
    width: 2.2rem;
    height: 2.2rem;
    border-radius: 50%;
    background: #24402c;
    color: var(--accent);
    font-weight: 700;
  }
  .headline { font-size: 1.05rem; margin: 0 0 0.35rem; }
  .body { white-space: pre-line; overflow-wrap: anywhere; margin: 0 0 0.35rem; }
  .small { font-size: 0.8rem; margin: 0; }
</style>
