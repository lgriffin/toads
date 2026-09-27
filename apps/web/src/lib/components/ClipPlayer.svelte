<script lang="ts">
  import { PROVIDER_LABELS, embedUrl, type ClipProvider } from '$lib/clips';

  interface Props {
    provider: ClipProvider;
    clipId: string;
    title: string;
    /** Small line under the title, e.g. boss and who submitted it. */
    meta?: string;
    headingLevel?: 3 | 4;
  }
  let { provider, clipId, title, meta = '', headingLevel = 3 }: Props = $props();

  // Click-to-load: nothing is requested from the provider until the visitor asks for the clip.
  let src = $state<string | null>(null);
  let failed = $state(false);
  const label = $derived(PROVIDER_LABELS[provider] ?? 'the provider');

  function load() {
    const url = embedUrl({ provider, clipId }, window.location.hostname, { autoplay: true });
    if (url) src = url;
    else failed = true;
  }
</script>

<figure class="clip">
  <div class="frame">
    {#if src}
      <iframe
        {src}
        {title}
        sandbox="allow-scripts allow-same-origin allow-presentation"
        referrerpolicy="strict-origin-when-cross-origin"
        loading="lazy"
        allow="autoplay; fullscreen; picture-in-picture"
        allowfullscreen
      ></iframe>
    {:else if failed}
      <p class="poster unavailable">This clip can’t be played.</p>
    {:else}
      <button type="button" class="poster" onclick={load} aria-label="Play “{title}” (loads from {label})">
        <span class="play" aria-hidden="true"></span>
        <span class="hint">Click to load from {label}</span>
      </button>
    {/if}
  </div>
  <figcaption>
    <svelte:element this={`h${headingLevel}`} class="title">{title}</svelte:element>
    {#if meta}<p class="muted meta">{meta}</p>{/if}
  </figcaption>
</figure>

<style>
  .clip { margin: 0; display: flex; flex-direction: column; gap: 0.5rem; min-width: 0; }
  .frame {
    position: relative;
    aspect-ratio: 16 / 9;
    border-radius: 8px;
    overflow: hidden;
    background: radial-gradient(circle at 30% 30%, #2d4a35, #101712 70%);
  }
  iframe, .poster { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
  .poster {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    margin: 0;
    background: transparent;
    color: var(--text);
    font: inherit;
    cursor: pointer;
  }
  .poster:focus-visible { outline: 3px solid var(--accent); outline-offset: -3px; }
  .play {
    width: 3.2rem;
    height: 3.2rem;
    border-radius: 50%;
    background: var(--accent);
    position: relative;
  }
  .play::after {
    content: '';
    position: absolute;
    left: 1.25rem;
    top: 0.95rem;
    border-style: solid;
    border-width: 0.65rem 0 0.65rem 1.05rem;
    border-color: transparent transparent transparent #0f1411;
  }
  .poster:hover .play { filter: brightness(1.15); }
  .hint { font-size: 0.85rem; color: var(--text); }
  .unavailable { color: var(--muted); }
  .title { font-size: 1rem; margin: 0; }
  .meta { margin: 0; font-size: 0.85rem; }
</style>
