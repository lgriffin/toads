<script lang="ts">
  import { dateTime } from '$lib/format';
  import {
    JOB_KIND_LABELS,
    JOB_STATUS_LABELS,
    comparisonKey,
    isPending,
    loginLabel,
    raidDay,
    raidLabel,
    reportCode,
    type ComparisonResponse,
    type ReferenceActions,
    type ReferenceOverview,
    type StoredRaid
  } from '$lib/reference';
  import { reportUrl } from '$lib/sheets';
  import ComparisonView from './ComparisonView.svelte';

  interface Props {
    overview: ReferenceOverview;
    /** The comparison being shown, once loaded. */
    comparison: ComparisonResponse | null;
    /** `comparisonKey` of the pairing the officer opened or asked for. */
    openKey: string | null;
    busy: boolean;
    /** The last action's outcome, announced politely. */
    message: string;
    error: string;
    actions: ReferenceActions;
  }

  let { overview, comparison, openKey, busy, message, error, actions }: Props = $props();

  let login = $derived(overview.login);
  let canImport = $derived(login.configured && login.connected && login.status !== 'expired');
  let pending = $derived(overview.jobs.some(isPending));

  // --- Import
  let report = $state('');
  let label = $state('');
  let reportErr = $state('');
  async function submitImport(e: SubmitEvent) {
    e.preventDefault();
    if (!reportCode(report)) {
      reportErr = 'Paste a 16-character report code or a Warcraft Logs report link.';
      return;
    }
    reportErr = '';
    if (await actions.importReport(report.trim(), label.trim() || null)) {
      report = '';
      label = '';
    }
  }

  // --- Labels and deletes
  let editing = $state<string | null>(null);
  let draft = $state('');
  function edit(r: StoredRaid) {
    editing = r.report_id;
    draft = r.label ?? '';
  }
  async function saveLabel(e: SubmitEvent, r: StoredRaid) {
    e.preventDefault();
    if (await actions.relabel(r.report_id, draft.trim() || null)) editing = null;
  }
  function remove(r: StoredRaid) {
    if (confirm(`Delete the reference “${r.title}” (${raidDay(r.raid_date)}) and its comparisons?`)) actions.remove(r.report_id);
  }
  function disconnect() {
    if (confirm('Disconnect the guild’s Warcraft Logs login? No officer can import references until someone reconnects.')) {
      actions.disconnect();
    }
  }

  // --- Compare
  let guildPick = $state('');
  let refPick = $state('');
  $effect(() => {
    if (!overview.guild_raids.some((r) => r.report_id === guildPick)) guildPick = overview.guild_raids[0]?.report_id ?? '';
    if (!overview.references.some((r) => r.report_id === refPick)) refPick = overview.references[0]?.report_id ?? '';
  });
  let built = $derived(new Set(overview.comparisons.map((c) => comparisonKey(c.guild_report, c.reference_report))));
  function submitCompare(e: SubmitEvent) {
    e.preventDefault();
    if (guildPick && refPick) actions.compare(guildPick, refPick);
  }
</script>

<p class="muted status" role="status">{message}</p>
{#if error}<p class="err" role="alert">{error}</p>{/if}

<div class="grid">
  <section class="card" aria-labelledby="login-h">
    <h2 id="login-h">Warcraft Logs login</h2>
    <p class:warn={login.configured && login.status === 'expired'} class:ok={canImport}>{loginLabel(login)}</p>
    {#if login.connected && login.connected_by}
      <p class="muted small">
        Connected by {login.connected_by}{#if login.connected_at}, {dateTime(login.connected_at)}{/if}.
      </p>
    {/if}
    {#if login.configured}
      <p class="hint">
        One dedicated Warcraft Logs account, shared by the guild, reads other guilds' reports. Any officer can connect it.
      </p>
      <div class="actions">
        <button type="button" class="btn primary" disabled={busy} onclick={() => actions.connect()}>
          {login.connected ? 'Reconnect' : 'Connect Warcraft Logs'}
        </button>
        {#if login.connected}
          <button type="button" class="btn danger" disabled={busy} onclick={disconnect}>Disconnect</button>
        {/if}
      </div>
    {/if}
  </section>

  <section class="card" aria-labelledby="import-h">
    <h2 id="import-h">Import a reference</h2>
    <form class="stack" novalidate onsubmit={submitImport}>
      <fieldset disabled={!canImport || busy}>
        <legend class="sr-only">Reference report</legend>
        <div class="field">
          <label for="ref-report">Report code or link</label>
          <input
            id="ref-report"
            autocomplete="off"
            spellcheck="false"
            placeholder="https://classic.warcraftlogs.com/reports/…"
            bind:value={report}
            aria-invalid={reportErr ? 'true' : undefined}
            aria-describedby={reportErr ? 'ref-report-err' : 'ref-import-hint'}
          />
          {#if reportErr}<span id="ref-report-err" class="err">{reportErr}</span>{/if}
        </div>
        <div class="field">
          <label for="ref-label">Label <span class="muted">(optional)</span></label>
          <input id="ref-label" maxlength="80" bind:value={label} placeholder="e.g. EU speed clear" />
        </div>
        <div><button type="submit" class="btn primary">Import</button></div>
      </fieldset>
      <p id="ref-import-hint" class="hint">
        {#if canImport}
          The worker fetches the report in the background; it shows under References when done.
        {:else if !login.configured}
          Imports need a Warcraft Logs app configured on the hub.
        {:else}
          Connect the Warcraft Logs login first.
        {/if}
      </p>
    </form>
  </section>
</div>

<section class="card" aria-labelledby="refs-h">
  <h2 id="refs-h">References</h2>
  {#if overview.references.length}
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Raid</th>
            <th scope="col">Zone</th>
            <th scope="col" class="num">Size</th>
            <th scope="col">Label</th>
            <th scope="col"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          {#each overview.references as r (r.report_id)}
            {@const link = reportUrl(r.report_id)}
            <tr>
              <td class="nowrap">{raidDay(r.raid_date)}</td>
              <th scope="row">
                {#if link}<a href={link} target="_blank" rel="noopener noreferrer">{r.title}</a>{:else}{r.title}{/if}
                {#if r.owner}<span class="muted small"> · {r.owner}</span>{/if}
              </th>
              <td>{r.zone ?? '—'}</td>
              <td class="num">{r.raid_size ?? '—'}</td>
              <td>
                {#if editing === r.report_id}
                  <form class="inline" onsubmit={(e) => saveLabel(e, r)}>
                    <label class="sr-only" for="label-{r.report_id}">Label for {r.title}</label>
                    <input id="label-{r.report_id}" maxlength="80" bind:value={draft} disabled={busy} />
                    <button type="submit" class="btn" disabled={busy}>Save</button>
                    <button type="button" class="btn" onclick={() => (editing = null)}>Cancel</button>
                  </form>
                {:else}
                  {r.label ?? ''}
                  <button type="button" class="link" onclick={() => edit(r)} aria-label="{r.label ? 'Edit label' : 'Add label'}: {r.title}"
                    >{r.label ? 'Edit label' : 'Add label'}</button
                  >
                {/if}
              </td>
              <td>
                <button
                  type="button"
                  class="btn danger"
                  disabled={busy}
                  onclick={() => remove(r)}
                  aria-label="Delete {r.title}, {raidDay(r.raid_date)}">Delete</button
                >
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <p class="muted">No references yet. Import another guild's report to compare against.</p>
  {/if}
  {#if overview.generated_at}
    <p class="hint">Stored raids listed {dateTime(overview.generated_at)}.</p>
  {:else}
    <p class="hint">The worker has not listed the stored raids yet.</p>
  {/if}
</section>

<section class="card" aria-labelledby="compare-h">
  <h2 id="compare-h">Compare</h2>
  {#if overview.guild_raids.length && overview.references.length}
    <form class="row" onsubmit={submitCompare}>
      <div class="field">
        <label for="cmp-guild">Our raid</label>
        <select id="cmp-guild" bind:value={guildPick}>
          {#each overview.guild_raids as r (r.report_id)}<option value={r.report_id}>{raidLabel(r)}</option>{/each}
        </select>
      </div>
      <div class="field">
        <label for="cmp-ref">Reference raid</label>
        <select id="cmp-ref" bind:value={refPick}>
          {#each overview.references as r (r.report_id)}<option value={r.report_id}>{raidLabel(r)}</option>{/each}
        </select>
      </div>
      <div class="go">
        <button type="submit" class="btn primary" disabled={busy || !guildPick || !refPick}>
          {built.has(comparisonKey(guildPick, refPick)) ? 'Rebuild' : 'Compare'}
        </button>
      </div>
    </form>
  {:else}
    <p class="muted">
      {overview.guild_raids.length ? 'Import a reference first.' : 'None of our raids are stored yet.'}
    </p>
  {/if}

  <h3>Built comparisons</h3>
  {#if overview.comparisons.length}
    <ul class="built">
      {#each overview.comparisons as c (comparisonKey(c.guild_report, c.reference_report))}
        {@const key = comparisonKey(c.guild_report, c.reference_report)}
        <li>
          <button
            type="button"
            class="link"
            aria-current={openKey === key ? 'true' : undefined}
            onclick={() => actions.open(c.guild_report, c.reference_report)}>{c.guild_title} vs {c.reference_title}</button
          >
          <span class="muted small">built {dateTime(c.generated_at)}</span>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="muted">None yet.</p>
  {/if}
</section>

{#if comparison}
  <ComparisonView data={comparison} />
{/if}

<section class="card" aria-labelledby="jobs-h">
  <h2 id="jobs-h">Recent jobs</h2>
  {#if pending}<p class="muted small">Checking for updates every few seconds while jobs run.</p>{/if}
  {#if overview.jobs.length}
    <ul class="jobs">
      {#each overview.jobs as j (j.id)}
        <li>
          <span class="pill status-{j.status}">{JOB_STATUS_LABELS[j.status]}</span>
          <span>{JOB_KIND_LABELS[j.kind]} <code>{j.report}</code></span>
          <span class="muted small">{dateTime(j.updated_at)}</span>
          {#if j.message}<span class="msg" class:err={j.status === 'failed'}>{j.message}</span>{/if}
        </li>
      {/each}
    </ul>
  {:else}
    <p class="muted">No jobs yet.</p>
  {/if}
</section>

<style>
  section { margin-bottom: 1rem; }
  .status:empty { margin: 0; }
  .grid { margin-bottom: 1rem; }
  .grid section { margin-bottom: 0; }
  .small { font-size: 0.85rem; }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .stack, fieldset { display: grid; gap: 0.75rem; }
  fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
  .row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end; }
  .row .field { flex: 1 1 16rem; }
  .row select { width: 100%; }
  .go { flex: 0 0 auto; }
  .inline { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
  .inline input { width: 12rem; }
  .nowrap { white-space: nowrap; }
  /* Keeps screen-reader-only text in wide tables inside the scroll box, so it cannot widen the page. */
  .scroll { position: relative; }
  tbody th { color: var(--text); font-weight: 400; }
  h3 { font-size: 1rem; margin: 1.25rem 0 0.5rem; }
  .link {
    background: none;
    border: 0;
    padding: 0;
    color: var(--accent);
    font: inherit;
    cursor: pointer;
    text-align: left;
  }
  .link:hover { text-decoration: underline; }
  .link[aria-current='true'] { color: var(--text); font-weight: 600; }
  td .link { font-size: 0.85rem; margin-left: 0.25rem; }
  .built, .jobs { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
  .jobs li { display: flex; flex-wrap: wrap; gap: 0.25rem 0.6rem; align-items: baseline; border-bottom: 1px solid var(--line); padding-bottom: 0.5rem; }
  .jobs .msg { flex-basis: 100%; font-size: 0.9rem; }
  code { font-size: 0.85rem; overflow-wrap: anywhere; }
  .status-queued, .status-running { background: #3b3320; color: var(--warn); }
  .status-done { background: #24402c; color: var(--accent); }
  .status-failed { background: #402624; color: #f0a39c; }
</style>
