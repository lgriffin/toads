<script lang="ts">
  import '@fontsource/cinzel/600.css';
  import { base } from '$app/paths';
  import { onMount, tick } from 'svelte';
  import {
    APPLICATION_LIMITS,
    CLASSES,
    DISCORD_INVITE,
    EMPTY_APPLICATION,
    RECRUIT_DRAFT_KEY as DRAFT_KEY,
    ROLES,
    rolesForClass,
    validateApplication,
    type ApplicationErrors,
    type ApplicationField,
    type ApplicationInput
  } from '$lib/application';
  import NeedsList from '$lib/components/NeedsList.svelte';
  import type { RecruitmentNeed } from '$lib/community';
  import { classToad, roleToad, toadSrc } from '$lib/toads';

  // The application page, for the real site and the preview alike. The host says whether someone is signed in and
  // how an application is sent; the API checks again that the applicant is in the Toads Discord before it opens their
  // interview room there.
  let {
    signedIn,
    loginHref,
    needs = [],
    send
  }: {
    /** null while the page is still asking who is here. */
    signedIn: boolean | null;
    loginHref: string;
    needs?: RecruitmentNeed[];
    /** Resolves with the new application's status; rejects with what to tell the applicant. */
    send: (input: ApplicationInput) => Promise<{ status: string }>;
  } = $props();

  let form = $state<ApplicationInput>({ ...EMPTY_APPLICATION });
  let errors = $state<ApplicationErrors>({});
  let sending = $state(false);
  let failure = $state<{ message: string; joinDiscord: boolean; signIn?: boolean } | null>(null);
  let sent = $state<{ name: string; roomOpen: boolean } | null>(null);

  const classRoles = $derived(rolesForClass(form.className));
  const errorList = $derived(Object.entries(errors) as [ApplicationField, string][]);
  const why = $derived(form.whyToads.trim().length);
  const pickedClass = $derived(classToad(form.className));

  const FIELD_LABELS: Record<ApplicationField, string> = {
    characterName: 'Character name',
    className: 'Class',
    primaryRole: 'Primary role',
    secondaryRole: 'Secondary role',
    whyToads: 'Why Toads?'
  };

  let restored = $state(false);
  onMount(() => {
    try {
      const saved = sessionStorage.getItem(DRAFT_KEY);
      if (saved) form = { ...EMPTY_APPLICATION, ...JSON.parse(saved) };
    } catch {
      // storage blocked or the draft is unreadable: start empty
    }
    restored = true;
  });

  // Keep the draft as they type, so any way out to sign in (the step link or the send button) comes back to it.
  $effect(() => {
    const draft = JSON.stringify(form);
    if (!restored || sent) return;
    try {
      sessionStorage.setItem(DRAFT_KEY, draft);
    } catch {
      // no storage: they will fill it in again after signing in
    }
  });

  function onClassChange() {
    if (form.primaryRole && !classRoles.includes(form.primaryRole as (typeof ROLES)[number])) form.primaryRole = '';
    if (form.secondaryRole && !classRoles.includes(form.secondaryRole as (typeof ROLES)[number])) form.secondaryRole = '';
    if (classRoles.length === 1) form.primaryRole = classRoles[0];
  }

  function canPlay(role: string) {
    return !form.className || classRoles.includes(role as (typeof ROLES)[number]);
  }

  async function showErrors() {
    await tick();
    document.getElementById('form-errors')?.focus();
  }

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    failure = null;
    errors = validateApplication(form);
    if (Object.keys(errors).length) return showErrors();
    if (!signedIn) {
      window.location.assign(loginHref);
      return;
    }
    sending = true;
    try {
      const app = await send(form);
      try {
        sessionStorage.removeItem(DRAFT_KEY);
      } catch {
        // nothing to clear
      }
      sent = { name: form.characterName.trim(), roomOpen: app.status === 'interviewing' };
      await tick();
      document.getElementById('apply-done')?.focus();
    } catch (err) {
      failure = err as { message: string; joinDiscord: boolean; signIn?: boolean };
      await tick();
      document.getElementById('send-failed')?.focus();
    } finally {
      sending = false;
    }
  }

  function describedBy(field: ApplicationField, hint?: string) {
    return [hint, errors[field] ? `${field}-error` : ''].filter(Boolean).join(' ') || undefined;
  }

  const roomName = (name: string) =>
    `interview-${name.normalize('NFKD').replace(/[^\x00-\x7f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'applicant'}`;
</script>

<header class="intro">
  <h1>Raid with the Toads</h1>
  <p class="lede">
    We raid Wednesday and Sunday evenings. Tell us who you play and why you want in, and you will be talking to our
    officers in a private Discord room within a minute.
  </p>
</header>

<ol class="path" aria-label="How to apply">
  <li class="step">
    <span class="num" aria-hidden="true">1</span>
    <div>
      <h2>Join our Discord</h2>
      <p>The interview happens there, so you need to be in the server before you apply.</p>
      <a class="btn" href={DISCORD_INVITE} target="_blank" rel="noopener noreferrer">
        Join the Toads Discord<span class="sr-only"> (opens in a new tab)</span>
      </a>
    </div>
  </li>
  <li class="step" class:complete={signedIn}>
    <span class="num" aria-hidden="true">2</span>
    <div>
      <h2>Sign in with Discord</h2>
      {#if signedIn}
        <p class="ok">You are signed in. We will check you are in the server when you send your application.</p>
      {:else}
        <p>We use your Discord account to find you in the server. We never see your email or password.</p>
        <a class="btn" href={loginHref} data-sveltekit-reload>Sign in with Discord</a>
      {/if}
    </div>
  </li>
  <li class="step">
    <span class="num" aria-hidden="true">3</span>
    <div>
      <h2>Answer five questions</h2>
      <p>
        Send them and the Toad Bot opens a private channel just for you and our recruitment officers. Nobody else in the
        server can see it.
      </p>
    </div>
  </li>
</ol>

<div class="layout">
  <section class="card apply" aria-labelledby="apply-h">
    <h2 id="apply-h">Your application</h2>

    {#if sent}
      <div id="apply-done" class="done" role="status" tabindex="-1">
        <h3>{sent.roomOpen ? 'Your interview room is opening' : 'Application sent'}</h3>
        {#if sent.roomOpen}
          <p>
            Thanks, {sent.name}! Look in Discord for <strong>#{roomName(sent.name)}</strong>. The Toad Bot will mention you
            there once it is ready, and our officers will say hello.
          </p>
        {:else}
          <p>Thanks, {sent.name}! An officer will open your private interview room in our Discord shortly.</p>
        {/if}
        <a class="btn" href={DISCORD_INVITE} target="_blank" rel="noopener noreferrer">
          Open Discord<span class="sr-only"> (opens in a new tab)</span>
        </a>
      </div>
    {:else}
      <form novalidate onsubmit={submit}>
        {#if errorList.length}
          <div id="form-errors" class="errors" role="alert" tabindex="-1">
            <p><strong>Please fix {errorList.length === 1 ? 'this' : 'these'}:</strong></p>
            <ul>
              {#each errorList as [field, msg]}<li><a href="#f-{field}">{FIELD_LABELS[field]}: {msg}</a></li>{/each}
            </ul>
          </div>
        {/if}

        <div class="pair">
          <div class="field">
            <label for="f-characterName">Character name</label>
            <input
              id="f-characterName"
              autocomplete="off"
              spellcheck="false"
              bind:value={form.characterName}
              aria-invalid={errors.characterName ? 'true' : undefined}
              aria-describedby={describedBy('characterName', 'characterName-hint')}
            />
            <span id="characterName-hint" class="hint">Your main, as it appears in game.</span>
            {#if errors.characterName}<span id="characterName-error" class="err">{errors.characterName}</span>{/if}
          </div>

          <div class="field">
            <label for="f-className">Class</label>
            <div class="with-toad">
              <select
                id="f-className"
                bind:value={form.className}
                onchange={onClassChange}
                aria-invalid={errors.className ? 'true' : undefined}
                aria-describedby={describedBy('className')}
              >
                <option value="">Choose…</option>
                {#each CLASSES as c}<option>{c}</option>{/each}
              </select>
              {#if pickedClass}<img src={toadSrc(base, pickedClass)} alt="" width="40" height="35" />{/if}
            </div>
            {#if errors.className}<span id="className-error" class="err">{errors.className}</span>{/if}
          </div>
        </div>

        <fieldset class="roles" aria-describedby={describedBy('primaryRole', 'primaryRole-hint')}>
          <legend id="f-primaryRole">Primary role</legend>
          <span id="primaryRole-hint" class="hint">What you most want to raid as.</span>
          <div class="chips">
            {#each ROLES as r}
              {@const toad = roleToad(r)}
              <label class="chip" class:off={!canPlay(r)}>
                <input type="radio" name="primaryRole" value={r} bind:group={form.primaryRole} disabled={!canPlay(r)} />
                {#if toad}<img src={toadSrc(base, toad)} alt="" width="28" height="25" />{/if}
                <span>{r}</span>
              </label>
            {/each}
          </div>
          {#if errors.primaryRole}<span id="primaryRole-error" class="err">{errors.primaryRole}</span>{/if}
        </fieldset>

        <fieldset class="roles" aria-describedby={describedBy('secondaryRole', 'secondaryRole-hint')}>
          <legend id="f-secondaryRole">Secondary role</legend>
          <span id="secondaryRole-hint" class="hint">What you would happily switch to if the raid needs it.</span>
          <div class="chips">
            {#each ROLES as r}
              {@const toad = roleToad(r)}
              <label class="chip" class:off={!canPlay(r) || r === form.primaryRole}>
                <input
                  type="radio"
                  name="secondaryRole"
                  value={r}
                  bind:group={form.secondaryRole}
                  disabled={!canPlay(r) || r === form.primaryRole}
                />
                {#if toad}<img src={toadSrc(base, toad)} alt="" width="28" height="25" />{/if}
                <span>{r}</span>
              </label>
            {/each}
            <label class="chip">
              <input type="radio" name="secondaryRole" value="" bind:group={form.secondaryRole} />
              <span>No second role</span>
            </label>
          </div>
          {#if errors.secondaryRole}<span id="secondaryRole-error" class="err">{errors.secondaryRole}</span>{/if}
        </fieldset>

        <div class="field">
          <label for="f-whyToads">Why Toads?</label>
          <textarea
            id="f-whyToads"
            rows="5"
            bind:value={form.whyToads}
            aria-invalid={errors.whyToads ? 'true' : undefined}
            aria-describedby={describedBy('whyToads', 'whyToads-hint whyToads-count')}
          ></textarea>
          <span id="whyToads-hint" class="hint">What drew you to us, and what you want from a raiding guild.</span>
          <span id="whyToads-count" class="hint count" class:over={why > APPLICATION_LIMITS.whyToads}
            >{why}/{APPLICATION_LIMITS.whyToads}</span
          >
          {#if errors.whyToads}<span id="whyToads-error" class="err">{errors.whyToads}</span>{/if}
        </div>

        {#if failure}
          <div id="send-failed" class="errors" role="alert" tabindex="-1">
            <p>{failure.message}</p>
            {#if failure.joinDiscord}
              <a class="btn" href={DISCORD_INVITE} target="_blank" rel="noopener noreferrer">
                Join the Toads Discord<span class="sr-only"> (opens in a new tab)</span>
              </a>
            {:else if failure.signIn}
              <a class="btn" href={loginHref} data-sveltekit-reload>Sign in with Discord again</a>
            {/if}
          </div>
        {/if}

        <div class="send">
          {#if signedIn === false}
            <button class="btn primary" type="submit">Sign in with Discord to apply</button>
            <span class="hint">Your answers are kept in this tab while you sign in.</span>
          {:else}
            <button class="btn primary" type="submit" disabled={sending || signedIn === null} aria-busy={sending}>
              {sending ? 'Checking Discord…' : 'Send application'}
            </button>
            <span class="hint">We check you are in the Toads Discord, then open your interview room.</span>
          {/if}
        </div>
      </form>
    {/if}
  </section>

  <aside class="card needs" aria-labelledby="needs-h">
    <h2 id="needs-h">What we need right now</h2>
    {#each ROLES as role}
      {@const forRole = needs.filter((n) => n.role === role)}
      {#if forRole.length}
        <h3 class="role">{role}</h3>
        <NeedsList needs={forRole} />
      {/if}
    {/each}
    <p class="muted small">Strong players of any class are always welcome to apply.</p>
    <p class="small">We ask for no age, email or real name. Only the officers in your room read your answers.</p>
  </aside>
</div>

<style>
  .intro h1 { font-family: 'Cinzel', serif; font-weight: 600; font-size: clamp(1.9rem, 4vw, 2.6rem); letter-spacing: 0.01em; margin: 0 0 0.5rem; text-wrap: balance; }
  .lede { max-width: 60ch; font-size: 1.05rem; margin: 0 0 1.5rem; }

  .path { list-style: none; margin: 0 0 2rem; padding: 0; display: grid; gap: 1.25rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr)); }
  .step { display: grid; grid-template-columns: auto 1fr; gap: 0.75rem; align-items: start; }
  .step h2 { font-size: 1.05rem; margin: 0.2rem 0 0.25rem; }
  .step p { margin: 0 0 0.6rem; max-width: 40ch; }
  .num {
    font-family: 'Cinzel', serif; font-weight: 600; font-size: 1.1rem; display: grid; place-items: center;
    width: 2.25rem; height: 2.25rem; border-radius: 50%; border: 1px solid var(--accent); color: var(--accent);
  }
  .step.complete .num { background: var(--accent); color: var(--bg); }

  .layout { display: grid; gap: 1rem; grid-template-columns: minmax(0, 2fr) minmax(min(100%, 16rem), 1fr); align-items: start; }
  @media (max-width: 760px) { .layout { grid-template-columns: 1fr; } }
  .apply h2, .needs h2 { margin-top: 0; }
  form { display: grid; gap: 1.25rem; }
  .pair { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr)); }
  .with-toad { display: flex; gap: 0.5rem; align-items: center; }
  .with-toad select { flex: 1; }

  .roles { border: 0; margin: 0; padding: 0; display: grid; gap: 0.4rem; }
  .roles legend { padding: 0; margin-bottom: 0.15rem; font-weight: 500; }
  .chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .chip {
    display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.75rem 0.3rem 0.45rem; min-height: 2.5rem;
    border: 1px solid var(--line); border-radius: 999px; background: var(--bg); cursor: pointer;
    transition: border-color 160ms cubic-bezier(0.16, 1, 0.3, 1), background-color 160ms cubic-bezier(0.16, 1, 0.3, 1);
  }
  .chip:hover { border-color: var(--muted); }
  .chip input { position: absolute; opacity: 0; width: 1px; height: 1px; }
  .chip:has(input:checked) { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 16%, var(--bg)); }
  .chip:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: 2px; }
  .chip.off { opacity: 0.45; cursor: not-allowed; }
  .chip.off:hover { border-color: var(--line); }

  .count { justify-self: end; font-variant-numeric: tabular-nums; }
  .over { color: var(--bad); }
  .send { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; align-items: center; }
  .errors { border: 1px solid var(--bad); border-radius: 6px; padding: 0.5rem 0.75rem; }
  .errors p { margin: 0 0 0.25rem; }
  .errors ul { margin: 0; padding-left: 1.2rem; }
  .errors a:not(.btn) { color: var(--text); }
  .done { border: 1px solid var(--accent); border-radius: 6px; padding: 0.75rem 1rem; }
  .done h3 { margin: 0 0 0.25rem; }
  .role { font-size: 0.9rem; color: var(--muted); margin: 0.75rem 0 0; font-weight: 500; }
  .small { font-size: 0.85rem; }
</style>
