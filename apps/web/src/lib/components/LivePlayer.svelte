<script lang="ts">
  import { twitchChannelUrl, twitchPlayerUrl, type Stream } from '$lib/gallery';

  interface Props {
    stream: Stream;
  }
  let { stream }: Props = $props();

  // Click-to-load, as clips are: nothing is asked of Twitch until the member chooses to watch. Then it plays muted
  // in the page for as long as the stream runs.
  let src = $state<string | null>(null);
  let failed = $state(false);
  const channelUrl = $derived(twitchChannelUrl(stream.channel));

  function watch() {
    const url = twitchPlayerUrl(stream.channel, window.location.hostname);
    if (url) src = url;
    else failed = true;
  }
</script>

<figure class="live">
  <div class="frame always-dusk">
    {#if src}
      <iframe
        {src}
        title="{stream.streamer_name} live on Twitch"
        sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"
        referrerpolicy="strict-origin-when-cross-origin"
        allow="autoplay; fullscreen; picture-in-picture"
        allowfullscreen
      ></iframe>
    {:else if failed}
      <p class="poster unavailable">This stream can’t be played here.</p>
    {:else}
      <button type="button" class="poster" onclick={watch} aria-label="Watch {stream.streamer_name} live (loads from Twitch)">
        <span class="badge">Live</span>
        <span class="play" aria-hidden="true"></span>
        <span class="hint">Watch here (loads from Twitch)</span>
      </button>
    {/if}
  </div>
  <figcaption>
    <h3 class="title">{stream.streamer_name}{stream.title ? `: ${stream.title}` : ''}</h3>
    {#if channelUrl}
      <a class="meta" href={channelUrl} target="_blank" rel="noopener noreferrer">twitch.tv/{stream.channel}</a>
    {/if}
  </figcaption>
</figure>

<style>
  .live { margin: 0; display: flex; flex-direction: column; gap: 0.5rem; min-width: 0; }
  .frame {
    position: relative;
    aspect-ratio: 16 / 9;
    border-radius: 8px;
    overflow: hidden;
    background: radial-gradient(circle at 30% 30%, #3a2a6e, #120f33 70%);
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
  .badge {
    position: absolute;
    top: 0.6rem;
    left: 0.6rem;
    padding: 0.1rem 0.5rem;
    border-radius: 4px;
    background: var(--bad-bg);
    color: var(--bad-text);
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  .play { width: 3.2rem; height: 3.2rem; border-radius: 50%; background: var(--accent); position: relative; }
  .play::after {
    content: '';
    position: absolute;
    left: 1.25rem;
    top: 0.95rem;
    border-style: solid;
    border-width: 0.65rem 0 0.65rem 1.05rem;
    border-color: transparent transparent transparent var(--on-accent);
  }
  .poster:hover .play { filter: brightness(1.15); }
  .hint { font-size: 0.85rem; }
  .unavailable { color: var(--muted); }
  .title { font-size: 1rem; margin: 0; }
  .meta { font-size: 0.85rem; }
</style>
