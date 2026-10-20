<script lang="ts">
  import { base } from '$app/paths';

  // Gail, the bank's toad at the request counter: the guild's own art (static/art/gail-*.webp, re-encoded from the
  // drawing the guild shared). Her "please include" sign is the request form's fields, so the caption points at the
  // form. `formId` is the form's first field on the live page; the held Forever notice has no form and passes none.
  let { formId }: { formId?: string } = $props();
</script>

<figure class="counter" aria-labelledby="counter-h">
  <picture>
    <source
      type="image/webp"
      srcset="{base}/art/gail-640.webp 640w, {base}/art/gail-960.webp 960w, {base}/art/gail-1312.webp 1312w"
      sizes="(max-width: 40rem) 100vw, 20rem"
    />
    <img
      src="{base}/art/gail-640.webp"
      width="1312"
      height="1199"
      decoding="async"
      alt="Gail, the guild's bank toad, behind the request counter with a quill, a box of request forms, a mug and a bell marked Ring for guild bank."
    />
  </picture>
  <figcaption>
    <h2 id="counter-h">Gail keeps the counter</h2>
    {#if formId}
      <p>
        Bring Gail a character name, the item and how many, and the slip goes to the banker on duty. Requests typed in
        Discord land in the same pile.
      </p>
      <p class="aside">One request at a time, please. <a href="#{formId}">Fill in a slip</a></p>
    {:else}
      <p>
        From launch, bring Gail a character name, the item and how many, and the slip goes to the banker on duty, from
        the site or from Discord.
      </p>
      <p class="aside">One request at a time, please.</p>
    {/if}
  </figcaption>
</figure>

<style>
  .counter {
    margin: 0 0 1.25rem;
    display: grid;
    grid-template-columns: minmax(0, 20rem) minmax(0, 1fr);
    gap: 1.5rem;
    align-items: center;
  }
  img {
    display: block;
    width: 100%;
    height: auto;
    border-radius: 10px;
    border: 1px solid var(--line);
    box-shadow: 0 14px 30px rgb(5 3 30 / 0.55);
  }
  h2 {
    margin: 0 0 0.5rem;
    font-family: 'Cinzel', Georgia, serif;
    font-weight: 600;
    letter-spacing: 0.03em;
    font-size: clamp(1.3rem, 3.5vw, 1.7rem);
    color: var(--bronze-hi);
    text-wrap: balance;
  }
  p { margin: 0 0 0.6rem; max-width: 52ch; color: var(--cream); text-wrap: pretty; }
  .aside { color: var(--muted); font-style: italic; }
  a { color: var(--teal); font-style: normal; text-underline-offset: 0.2em; }
  a:hover { color: var(--bronze-hi); }
  a:focus-visible { outline: 2px solid var(--bronze-hi); outline-offset: 3px; }

  @media (max-width: 40rem) {
    .counter { grid-template-columns: 1fr; gap: 1rem; }
    /* A phone gets Gail and the sign above the counter, not the whole booth. */
    img { aspect-ratio: 4 / 3; object-fit: cover; object-position: 50% 35%; }
  }
</style>
