<script lang="ts">
  import {
    APPLICATION_LIMITS,
    CLASSES,
    EMPTY_APPLICATION,
    RAID_DAYS,
    ROLES,
    rolesFor,
    specsFor,
    validateApplication,
    type ApplicationErrors,
    type ApplicationField
  } from '$lib/application';
  import NeedsList from '$lib/components/NeedsList.svelte';
  import { needs } from '$lib/mock/community';
  import { tick } from 'svelte';

  let form = $state({ ...EMPTY_APPLICATION, raidDays: [] as string[] });
  let errors = $state<ApplicationErrors>({});
  let submitted = $state(false);
  let sentAs = $state('');

  const specs = $derived(specsFor(form.className));
  const roleHint = $derived(rolesFor(form.className, form.spec));
  const errorList = $derived(Object.entries(errors) as [ApplicationField, string][]);

  const FIELD_LABELS: Record<ApplicationField, string> = {
    characterName: 'Character name',
    className: 'Class',
    spec: 'Spec',
    role: 'Role',
    raidDays: 'Raid days',
    experience: 'Raiding experience',
    availability: 'Availability',
    logsUrl: 'Warcraft Logs link'
  };

  function onClassChange() {
    if (!specs.includes(form.spec)) form.spec = '';
  }
  function onSpecChange() {
    const roles = rolesFor(form.className, form.spec);
    if (roles.length === 1) form.role = roles[0];
  }

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    errors = validateApplication(form);
    if (Object.keys(errors).length) {
      await tick();
      document.getElementById('form-errors')?.focus();
      return;
    }
    // Preview only: nothing is sent. The real form posts to the API after Discord login.
    sentAs = form.characterName.trim();
    submitted = true;
    await tick();
    document.getElementById('apply-done')?.focus();
  }

  function describedBy(field: ApplicationField, hint?: string) {
    return [hint, errors[field] ? `${field}-error` : ''].filter(Boolean).join(' ') || undefined;
  }
</script>

<h1>Raid with the Toads</h1>
<p class="lede">
  We raid Wednesday and Sunday evenings on Spineshatter EU. If you like steady progress with friendly people, we’d love
  to hear from you.
</p>

<div class="grid">
  <section class="card" aria-labelledby="needs-h">
    <h2 id="needs-h">What we need right now</h2>
    {#each ROLES as role}
      {@const forRole = needs.filter((n) => n.role === role)}
      {#if forRole.length}
        <h3 class="role">{role}</h3>
        <NeedsList needs={forRole} />
      {/if}
    {/each}
    <p class="muted small">Strong players of any class are always welcome to apply.</p>
  </section>

  <section class="card" aria-labelledby="how-h">
    <h2 id="how-h">How the interview room works</h2>
    <ol class="steps">
      <li><strong>Apply here.</strong> Sign in with Discord and fill in the short form below.</li>
      <li>
        <strong>Your private room opens.</strong> Our bot creates a private Discord channel just for you and the officers
        of the night you applied for.
      </li>
      <li><strong>Chat, then a trial raid.</strong> Ask us anything; if it clicks we’ll invite you to a trial raid.</li>
      <li>
        <strong>Decision.</strong> We’ll tell you in your room either way. The room is then locked, never deleted, so
        nothing you said disappears.
      </li>
    </ol>
  </section>
</div>

<section class="card apply" aria-labelledby="apply-h">
  <h2 id="apply-h">Apply</h2>
  <p class="muted">
    Applying needs a Discord login so we can open your interview room. We only ask what we need to plan raids: no age,
    email or real name.
  </p>

  {#if submitted}
    <div id="apply-done" class="done" role="status" tabindex="-1">
      <h3>Application sent</h3>
      <p>
        Thanks, {sentAs}! A private interview room will open for you in our Discord shortly. Officers will say hello
        there.
      </p>
      <p class="muted small">Preview only: nothing was sent.</p>
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

      <div class="fields">
        <div class="field">
          <label for="f-characterName">Character name</label>
          <input
            id="f-characterName"
            autocomplete="off"
            bind:value={form.characterName}
            aria-invalid={errors.characterName ? 'true' : undefined}
            aria-describedby={describedBy('characterName', 'characterName-hint')}
          />
          <span id="characterName-hint" class="hint">Your main, 2 to 12 letters.</span>
          {#if errors.characterName}<span id="characterName-error" class="err">{errors.characterName}</span>{/if}
        </div>

        <div class="field">
          <label for="f-className">Class</label>
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
          {#if errors.className}<span id="className-error" class="err">{errors.className}</span>{/if}
        </div>

        <div class="field">
          <label for="f-spec">Spec</label>
          <select
            id="f-spec"
            bind:value={form.spec}
            onchange={onSpecChange}
            disabled={!form.className}
            aria-invalid={errors.spec ? 'true' : undefined}
            aria-describedby={describedBy('spec')}
          >
            <option value="">{form.className ? 'Choose…' : 'Pick a class first'}</option>
            {#each specs as s}<option>{s}</option>{/each}
          </select>
          {#if errors.spec}<span id="spec-error" class="err">{errors.spec}</span>{/if}
        </div>

        <div class="field">
          <label for="f-role">Role</label>
          <select
            id="f-role"
            bind:value={form.role}
            aria-invalid={errors.role ? 'true' : undefined}
            aria-describedby={describedBy('role', roleHint.length ? 'role-hint' : undefined)}
          >
            <option value="">Choose…</option>
            {#each ROLES as r}<option>{r}</option>{/each}
          </select>
          {#if roleHint.length}<span id="role-hint" class="hint">{form.spec} raids as {roleHint.join(' or ')}.</span>{/if}
          {#if errors.role}<span id="role-error" class="err">{errors.role}</span>{/if}
        </div>
      </div>

      <fieldset class="days" aria-describedby={describedBy('raidDays', 'raidDays-hint')}>
        <legend id="f-raidDays">Raid days</legend>
        {#each RAID_DAYS as d}
          <label class="check"><input type="checkbox" value={d} bind:group={form.raidDays} /> {d}</label>
        {/each}
        <span id="raidDays-hint" class="hint">Leave both unticked if either night works.</span>
        {#if errors.raidDays}<span id="raidDays-error" class="err">{errors.raidDays}</span>{/if}
      </fieldset>

      <div class="field">
        <label for="f-experience">Raiding experience <span class="muted">(optional)</span></label>
        <textarea
          id="f-experience"
          rows="4"
          bind:value={form.experience}
          aria-invalid={errors.experience ? 'true' : undefined}
          aria-describedby={describedBy('experience', 'experience-count')}
        ></textarea>
        <span id="experience-count" class="hint" class:over={form.experience.length > APPLICATION_LIMITS.experience}
          >{form.experience.length}/{APPLICATION_LIMITS.experience} characters</span
        >
        {#if errors.experience}<span id="experience-error" class="err">{errors.experience}</span>{/if}
      </div>

      <div class="field">
        <label for="f-availability">Availability <span class="muted">(optional)</span></label>
        <textarea
          id="f-availability"
          rows="2"
          bind:value={form.availability}
          aria-invalid={errors.availability ? 'true' : undefined}
          aria-describedby={describedBy('availability', 'availability-count')}
        ></textarea>
        <span id="availability-count" class="hint" class:over={form.availability.length > APPLICATION_LIMITS.availability}
          >{form.availability.length}/{APPLICATION_LIMITS.availability} characters</span
        >
        {#if errors.availability}<span id="availability-error" class="err">{errors.availability}</span>{/if}
      </div>

      <div class="field">
        <label for="f-logsUrl">Warcraft Logs link <span class="muted">(optional)</span></label>
        <input
          id="f-logsUrl"
          type="url"
          inputmode="url"
          placeholder="https://classic.warcraftlogs.com/character/…"
          bind:value={form.logsUrl}
          aria-invalid={errors.logsUrl ? 'true' : undefined}
          aria-describedby={describedBy('logsUrl')}
        />
        {#if errors.logsUrl}<span id="logsUrl-error" class="err">{errors.logsUrl}</span>{/if}
      </div>

      <button class="btn primary" type="submit">Send application</button>
    </form>
  {/if}
</section>

<style>
  .lede { max-width: 42rem; font-size: 1.05rem; }
  .role { font-size: 0.9rem; color: var(--muted); margin: 0.75rem 0 0; font-weight: 500; }
  .steps { margin: 0; padding-left: 1.25rem; display: grid; gap: 0.6rem; }
  .apply { margin-top: 1rem; }
  form { display: grid; gap: 1rem; max-width: 42rem; }
  .fields { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr)); }
  .days { border: 1px solid var(--line); border-radius: 6px; padding: 0.5rem 0.75rem 0.75rem; display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem; }
  .days legend { padding: 0 0.25rem; }
  .days .hint, .days .err { flex-basis: 100%; }
  .check { display: inline-flex; gap: 0.4rem; align-items: center; }
  .over { color: var(--bad); }
  .errors { border: 1px solid var(--bad); border-radius: 6px; padding: 0.5rem 0.75rem; }
  .errors p { margin: 0 0 0.25rem; }
  .errors ul { margin: 0; padding-left: 1.2rem; }
  .errors a { color: var(--text); }
  .done { border: 1px solid var(--accent); border-radius: 6px; padding: 0.75rem 1rem; }
  .done h3 { margin: 0 0 0.25rem; }
  .small { font-size: 0.8rem; }
</style>
