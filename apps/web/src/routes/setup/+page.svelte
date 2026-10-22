<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { claimError, type CharacterMatch, type Claim } from '$lib/api';
  import { classOf } from '$lib/comp';
  import { getMe } from '$lib/me-context';
  import { previewSetup } from '$lib/preview/setup-fake';
  import { MAIN_STATUS, WELCOME, altsOf, hubSetup, setupError, type Alt, type SetupState } from '$lib/setup';
  import SetupPicker from '$lib/components/SetupPicker.svelte';
  import SpecsCard from '$lib/components/SpecsCard.svelte';

  // The first sign-in setup (docs/setup.md): sign-in sends a trial or raider here until they press Finish, and the
  // account menu brings anyone back to change things. Each step saves as it goes, so leaving early loses nothing.
  const backend = __PREVIEW__ ? previewSetup : hubSetup();
  const me = getMe();

  let setup = $state<SetupState | null>(null);
  let claims = $state<Claim[]>([]);
  let loadError = $state('');
  let busy = $state(false);
  let mainMessage = $state('');
  let altMessage = $state('');
  let finishMessage = $state('');

  const mine = $derived(new Set(claims.filter((c) => c.status !== 'rejected').map((c) => c.character_id)));
  const alts = $derived(setup ? altsOf(claims, setup) : []);
  const firstName = $derived(me().name);

  async function load() {
    try {
      // In turn: reading the setup turns named characters the logs now know into claims, which the claims list shows.
      setup = await backend.state();
      claims = await backend.claims();
      loadError = '';
    } catch (e) {
      loadError = setupError(e);
    }
  }
  onMount(load);

  // Runs one change, reloads, and puts any failure beside the step that made it.
  async function run(
    action: () => Promise<unknown>,
    say: (m: string) => void,
    fail: (e: unknown) => string = setupError
  ): Promise<boolean> {
    busy = true;
    say('');
    try {
      await action();
      return true;
    } catch (e) {
      say(fail(e));
      return false;
    } finally {
      await load();
      busy = false;
    }
  }
  const sayMain = (m: string) => (mainMessage = m);
  const sayAlt = (m: string) => (altMessage = m);

  // The main is claimed first (unless it is already theirs), then named main: a refused claim says why in the claim's
  // own words.
  async function pickMain(c: CharacterMatch) {
    if (mine.has(c.id)) {
      await run(() => backend.setMain(c.id), sayMain);
      return;
    }
    busy = true;
    mainMessage = '';
    try {
      await backend.claim(c.id);
    } catch (e) {
      mainMessage = claimError(e);
      await load();
      busy = false;
      return;
    }
    await run(() => backend.setMain(c.id), sayMain);
  }
  const nameMain = (name: string, wowClass: string) => run(() => backend.declare(name, wowClass, true), sayMain);
  const pickAlt = (c: CharacterMatch) =>
    run(() => backend.claim(c.id), sayAlt, claimError);
  const nameAlt = (name: string, wowClass: string) => run(() => backend.declare(name, wowClass, false), sayAlt);

  function remove(alt: Alt) {
    if (alt.claim) run(() => backend.unclaim(alt.claim!.id), sayAlt, claimError);
    else if (alt.declared) run(() => backend.drop(alt.declared!.id), sayAlt);
  }

  async function finish() {
    busy = true;
    finishMessage = '';
    try {
      await backend.finish();
      await goto(`${base}/hub/`);
    } catch (e) {
      finishMessage = setupError(e);
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head><title>Set up · Toads</title></svelte:head>

<section class="welcome" aria-labelledby="welcome-h">
  <picture>
    <source type="image/webp" srcset="{base}/art/gail-640.webp 640w, {base}/art/gail-960.webp 960w" sizes="(max-width: 40rem) 60vw, 14rem" />
    <img
      src="{base}/art/gail-640.webp"
      width="1312"
      height="1199"
      decoding="async"
      alt="Gail, the guild's bank toad, behind her counter with a quill and a bell."
    />
  </picture>
  <div class="note">
    <h1 id="welcome-h">{WELCOME.heading}{firstName ? `, ${firstName}` : ''}!</h1>
    {#each WELCOME.body as line}<p>{line}</p>{/each}
    <p class="signoff">From {WELCOME.signoff}</p>
  </div>
</section>

{#if loadError}
  <section class="card"><p class="err" role="alert">{loadError}</p><button class="btn" type="button" onclick={load}>Try again</button></section>
{:else if !setup}
  <p class="muted" role="status">Loading…</p>
{:else}
  <ol class="steps">
    <li class="card step" aria-labelledby="main-h">
      <h2 id="main-h">Your main</h2>
      {#if setup.main}
        <p class="picked">
          <strong>{setup.main.name}</strong>
          <span class={setup.main.status === 'approved' ? 'ok' : 'warn'}>{MAIN_STATUS[setup.main.status]}</span>
        </p>
      {/if}
      {#if setup.main_open}
        <p class="muted">
          {setup.main ? 'Picked the wrong one? Pick again.' : 'The character you raid as most. Find it in the guild’s logs, or add it if it hasn’t raided with us yet.'}
          A name that matches your Discord nickname is approved at once; any other waits for an officer of your raid night.
        </p>
        <SetupPicker id="main" action="This is my main" heldAction="Make it my main" {busy} {mine} search={backend.search} onpick={pickMain} onname={nameMain} />
      {:else}
        <p class="muted">To change your main, <a href="{base}/me/">ask for a main swap on Me</a>; your raid night’s officers approve it.</p>
      {/if}
      {#if mainMessage}<p class="err" role="alert">{mainMessage}</p>{/if}
    </li>

    <li class="step specs">
      <SpecsCard />
    </li>

    <li class="card step" aria-labelledby="alts-h">
      <h2 id="alts-h">Your alts</h2>
      <p class="muted">Every other character of yours, so your raids, badges and bank requests follow you whichever one you log.</p>
      {#if alts.length}
        <ul class="alts">
          {#each alts as alt (alt.key)}
            <li>
              <span>
                <strong>{alt.name}</strong>
                {#if alt.declared}<span class="muted"> · {classOf(alt.declared.wow_class)?.name ?? alt.declared.wow_class}</span>{/if}
                <span class="hint">{alt.status}</span>
              </span>
              <button class="btn" type="button" disabled={busy} onclick={() => remove(alt)}>Remove</button>
            </li>
          {/each}
        </ul>
      {/if}
      <SetupPicker id="alt" action="Add as an alt" {busy} {mine} search={backend.search} onpick={pickAlt} onname={nameAlt} />
      {#if altMessage}<p class="err" role="alert">{altMessage}</p>{/if}
    </li>
  </ol>

  <section class="card finish" aria-labelledby="finish-h">
    <h2 id="finish-h">{setup.done ? 'All set' : 'That’s you sorted'}</h2>
    <p class="muted">
      Everything above is saved as you go. You can come back any time from your account menu to change it.
      {#if !setup.done}Until you finish, signing in brings you back here first.{/if}
    </p>
    <div class="actions">
      <button class="btn primary" type="button" disabled={busy} onclick={finish}>{setup.done ? 'Back to the hub' : 'Finish and hop in'}</button>
      {#if !setup.done}<a class="btn" href="{base}/hub/">Finish later</a>{/if}
    </div>
    {#if finishMessage}<p class="err" role="alert">{finishMessage}</p>{/if}
  </section>
{/if}

<style>
  .welcome {
    display: grid;
    grid-template-columns: minmax(8rem, 14rem) 1fr;
    gap: 1.25rem;
    align-items: center;
    margin-bottom: 1.25rem;
  }
  .welcome picture { display: block; }
  .welcome img { width: 100%; height: auto; border-radius: 12px; }
  .note {
    position: relative;
    padding: 1rem 1.25rem;
    border: 1px solid color-mix(in srgb, var(--bronze) 45%, var(--line));
    border-radius: 12px;
    background: var(--surface);
  }
  .note h1 { margin-top: 0; font-family: 'Cinzel', Georgia, serif; }
  .note p { margin: 0 0 0.5rem; max-width: 60ch; }
  .signoff { font-style: italic; color: var(--muted); }
  .steps { list-style: none; margin: 0 0 1rem; padding: 0; display: grid; gap: 1rem; counter-reset: step; }
  .step { counter-increment: step; display: grid; gap: 0.6rem; }
  .step h2 { margin: 0; }
  .step > h2::before, .specs :global(h2)::before { content: counter(step) '. '; color: var(--accent); }
  .step p { margin: 0; }
  .specs { display: block; }
  .specs :global(.specs) { margin-block: 0; }
  .picked { display: flex; flex-wrap: wrap; gap: 0.25rem 0.75rem; align-items: baseline; }
  .alts { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.25rem; }
  .alts li { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; flex-wrap: wrap; padding: 0.25rem 0; border-bottom: 1px solid var(--line); }
  .alts .hint { display: block; }
  .finish { display: grid; gap: 0.6rem; }
  .finish h2, .finish p { margin: 0; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  @media (max-width: 40rem) {
    .welcome { grid-template-columns: 1fr; }
    .welcome picture { max-width: 14rem; }
  }
</style>
