<script lang="ts">
  import { onMount } from 'svelte';
  import { DEFAULT_DISPLAY, THEMES, applyDisplay, loadDisplay, saveDisplay, type Display, type Theme } from '$lib/display';

  // The reader's own display settings, inside the top bar's account or Display menu: the theme and easier reading.
  // Each change applies at once and is remembered in this browser.
  let display = $state<Display>({ ...DEFAULT_DISPLAY });

  onMount(() => {
    display = loadDisplay();
    // A "Match my device" reader follows their device when it changes from day to night.
    const media = matchMedia('(prefers-color-scheme: light)');
    const follow = () => display.theme === 'system' && applyDisplay(display);
    media.addEventListener('change', follow);
    return () => media.removeEventListener('change', follow);
  });

  function setTheme(theme: Theme) {
    display = { ...display, theme };
    saveDisplay(display);
    applyDisplay(display);
  }
  function setEasyReading(on: boolean) {
    display = { ...display, easyReading: on };
    saveDisplay(display);
    applyDisplay(display);
  }
</script>

<fieldset class="themes">
  <legend>Theme</legend>
  {#each THEMES as t (t.id)}
    <label>
      <input type="radio" name="toads-theme" value={t.id} checked={display.theme === t.id} onchange={() => setTheme(t.id)} />
      {t.label}
    </label>
  {/each}
</fieldset>
<label class="reading">
  <input type="checkbox" checked={display.easyReading} onchange={(e) => setEasyReading(e.currentTarget.checked)} />
  <span>
    Easier reading
    <span class="hint">Bigger text, more space between lines and plain headings</span>
  </span>
</label>

<style>
  fieldset { border: 0; border-top: 1px solid var(--line); margin: 0.35rem 0 0; padding: 0.5rem 0.5rem 0.25rem; display: grid; gap: 0.15rem; }
  legend { float: left; width: 100%; padding: 0 0 0.25rem; margin: 0; font-size: 0.8rem; font-weight: 600; color: var(--muted); }
  label { display: flex; align-items: center; gap: 0.6rem; min-height: 2.5rem; padding: 0 0.25rem; border-radius: 6px; cursor: pointer; }
  label:hover { background: var(--nav-hover); }
  .reading { align-items: flex-start; padding: 0.5rem; margin: 0 0.25rem; min-height: 0; }
  .reading input { margin-top: 0.2rem; }
  .reading > span { display: grid; gap: 0.1rem; }
  input { width: 1.1rem; height: 1.1rem; accent-color: var(--accent); margin: 0; flex: none; }
</style>
