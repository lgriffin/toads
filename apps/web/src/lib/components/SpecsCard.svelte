<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { CLASSES, classOf, clearMySpecs, compError, getMySpecs, saveMySpecs, specLabel, specsOfClass, type MySpecs } from '$lib/comp';
  import { ROLE_BADGES_CHANGED } from '$lib/role-badges';

  // A member's class and the specs they raid as: officers seat them by these in the comp builder, and filter the
  // roster by them (an Elemental filter finds everyone with Elemental as their primary or secondary).
  let loaded = $state(__PREVIEW__);
  let saved = $state<MySpecs | null>(null);
  let wowClass = $state('');
  let primary = $state('');
  let secondary = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  const specs = $derived(wowClass ? specsOfClass(wowClass) : []);
  // Specs an officer imported from the Raid-Helper sign-up can be confirmed as they are, which makes them the member's.
  const changed = $derived(
    !saved ||
      !!saved.imported ||
      saved.wow_class !== wowClass ||
      saved.primary !== primary ||
      (saved.secondary ?? '') !== secondary
  );

  function show(s: MySpecs | null) {
    saved = s;
    wowClass = s?.wow_class ?? '';
    primary = s?.primary ?? '';
    secondary = s?.secondary ?? '';
  }

  function pickClass(id: string) {
    if (id === wowClass) return;
    wowClass = id;
    primary = '';
    secondary = '';
  }

  function pickPrimary(id: string) {
    primary = id;
    if (secondary === id) secondary = '';
  }

  onMount(async () => {
    if (__PREVIEW__) return;
    try {
      show(await getMySpecs());
    } catch (e) {
      message = compError(e);
      failed = true;
    } finally {
      loaded = true;
    }
  });

  async function save(event: SubmitEvent) {
    event.preventDefault();
    if (!wowClass || !primary) return;
    const next: MySpecs = { wow_class: wowClass, primary, secondary: secondary || null };
    busy = true;
    try {
      show(__PREVIEW__ ? next : await saveMySpecs(next));
      // The class and role badges follow the primary spec, so the header fetches them again.
      window.dispatchEvent(new Event(ROLE_BADGES_CHANGED));
      message = `Saved. Officers now see you as ${specLabel(primary)}${secondary ? `, or ${specLabel(secondary)}` : ''}.`;
      failed = false;
    } catch (e) {
      message = compError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }

  async function clearAll() {
    busy = true;
    try {
      if (!__PREVIEW__) await clearMySpecs();
      show(null);
      window.dispatchEvent(new Event(ROLE_BADGES_CHANGED));
      message = 'Your specs are cleared.';
      failed = false;
    } catch (e) {
      message = compError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }
</script>

<section class="card specs" aria-labelledby="specs-h">
  <h2 id="specs-h">Your specs</h2>
  <p class="muted lede">
    The class you raid as, the spec you play most and the one you can swap to. Officers build each night's comp from
    these, so keep them current when you respec.
  </p>

  {#if !loaded}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if saved?.imported}
      <p class="imported" role="note">
        An officer filled these in from the Raid-Helper sign-up. Change them if they are wrong, or confirm them as
        they are.
      </p>
    {/if}
    <form onsubmit={save}>
      <fieldset disabled={busy}>
        <legend>Class</legend>
        <div class="classes">
          {#each CLASSES as c (c.id)}
            <label class="class" class:picked={wowClass === c.id} style="--class: {c.colour}">
              <input type="radio" name="spec-class" value={c.id} checked={wowClass === c.id} onchange={() => pickClass(c.id)} />
              <img src="{base}/logos/classes/{c.id}.svg" alt="" width="40" height="35" loading="lazy" />
              <span>{c.name}</span>
            </label>
          {/each}
        </div>
      </fieldset>

      {#if wowClass}
        <div class="pickers">
          <fieldset disabled={busy}>
            <legend>Primary spec</legend>
            <div class="chips">
              {#each specs as s (s.id)}
                <label class="chip" class:picked={primary === s.id}>
                  <input type="radio" name="spec-primary" value={s.id} checked={primary === s.id} onchange={() => pickPrimary(s.id)} />
                  {s.name}
                </label>
              {/each}
            </div>
          </fieldset>
          <fieldset disabled={busy || !primary}>
            <legend>Secondary spec <span class="hint">optional</span></legend>
            <div class="chips">
              <label class="chip" class:picked={secondary === ''}>
                <input type="radio" name="spec-secondary" value="" bind:group={secondary} />
                None
              </label>
              {#each specs.filter((s) => s.id !== primary) as s (s.id)}
                <label class="chip" class:picked={secondary === s.id}>
                  <input type="radio" name="spec-secondary" value={s.id} bind:group={secondary} />
                  {s.name}
                </label>
              {/each}
            </div>
          </fieldset>
        </div>
      {/if}

      <div class="actions">
        <button class="btn primary" type="submit" disabled={busy || !wowClass || !primary || !changed}>{saved?.imported ? 'Confirm my specs' : 'Save my specs'}</button>
        {#if saved}
          <button class="btn" type="button" disabled={busy} onclick={clearAll}>Clear</button>
          <span class="hint">
            Saved as {specLabel(saved.primary)}{saved.secondary ? ` and ${specLabel(saved.secondary)}` : ''}
            <span class="dot" style="--class: {classOf(saved.wow_class)?.colour}" aria-hidden="true"></span>
          </span>
        {/if}
      </div>
    </form>
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  {/if}
</section>

<style>
  .specs { display: grid; gap: 0.9rem; margin-block: 1rem; }
  .specs h2 { margin: 0; }
  .lede { margin: 0; max-width: 62ch; }
  .imported {
    margin: 0;
    max-width: 62ch;
    padding: 0.6rem 0.8rem;
    border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
    border-radius: 6px;
    background: color-mix(in srgb, var(--accent) 10%, var(--bg));
  }
  form { display: grid; gap: 1rem; }
  fieldset { border: 0; margin: 0; padding: 0; min-width: 0; }
  legend { padding: 0; margin-bottom: 0.45rem; }
  .classes { display: grid; grid-template-columns: repeat(auto-fill, minmax(5.5rem, 1fr)); gap: 0.5rem; }
  .class {
    position: relative;
    display: grid;
    justify-items: center;
    gap: 0.2rem;
    padding: 0.5rem 0.25rem 0.45rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--bg);
    font-size: 0.85rem;
    cursor: pointer;
    transition: border-color 160ms cubic-bezier(0.16, 1, 0.3, 1), background-color 160ms cubic-bezier(0.16, 1, 0.3, 1);
  }
  .class:hover { border-color: var(--muted); }
  .class.picked { border-color: var(--class); background: color-mix(in srgb, var(--class) 14%, var(--bg)); }
  .class img { width: 2.5rem; height: auto; }
  .class:has(input:focus-visible), .chip:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: 2px; }
  input[type='radio'] { position: absolute; opacity: 0; pointer-events: none; }
  .pickers { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
  .chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .chip {
    position: relative;
    padding: 0.35rem 0.8rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--bg);
    font-size: 0.9rem;
    cursor: pointer;
  }
  .chip:hover { border-color: var(--muted); }
  .chip.picked { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 16%, var(--bg)); }
  .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; }
  .dot { display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 50%; background: var(--class); margin-left: 0.25rem; }
  fieldset:disabled .chip { opacity: 0.55; cursor: not-allowed; }
  @media (prefers-reduced-motion: reduce) { .class { transition: none; } }
</style>
