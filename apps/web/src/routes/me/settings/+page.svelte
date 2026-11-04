<script lang="ts">
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import {
    chooseName,
    getAccountSettings,
    removeWclKey,
    saveWclKey,
    settingsError,
    wclKeyLabel,
    type AccountSettings,
    type NameOption
  } from '$lib/api';

  // Preview builds have no API: show a sample member whose changes stay in the page.
  const SAMPLE: AccountSettings = {
    shown_name: 'Hops',
    name_source: 'discord',
    name_character_id: null,
    name_options: [
      { source: 'discord', name: 'Hops', character_id: null },
      { source: 'character', name: 'Ribbit', character_id: 2 }
    ],
    wcl_key: null,
    wcl_key_in_use: 'guild'
  };

  let settings = $state<AccountSettings | null>(__PREVIEW__ ? structuredClone(SAMPLE) : null);
  let message = $state(__PREVIEW__ ? 'Preview: settings here are not saved.' : '');
  let busy = $state(false);
  let clientId = $state('');
  let clientSecret = $state('');

  const optionKey = (o: Pick<NameOption, 'source' | 'character_id'>) => `${o.source}:${o.character_id ?? ''}`;
  let chosen = $derived(settings ? optionKey({ source: settings.name_source, character_id: settings.name_character_id }) : '');

  async function run(action: () => Promise<AccountSettings>) {
    busy = true;
    message = '';
    try {
      settings = await action();
    } catch (e) {
      message = settingsError(e);
    } finally {
      busy = false;
    }
  }

  function pick(option: NameOption) {
    if (__PREVIEW__ && settings) {
      settings = { ...settings, shown_name: option.name, name_source: option.source, name_character_id: option.character_id };
      return;
    }
    run(() => chooseName(option));
  }

  function save(event: SubmitEvent) {
    event.preventDefault();
    const id = clientId.trim();
    const secret = clientSecret.trim();
    // Clear the fields straight away: the secret should not sit in the page once sent.
    clientId = '';
    clientSecret = '';
    if (__PREVIEW__ && settings) {
      const hint = id.slice(-4);
      settings = { ...settings, wcl_key: { client_id_hint: hint, status: 'unverified', updated_at: '', checked_at: null }, wcl_key_in_use: 'own' };
      return;
    }
    run(() => saveWclKey(id, secret));
  }

  function remove() {
    if (__PREVIEW__ && settings) {
      settings = { ...settings, wcl_key: null, wcl_key_in_use: 'guild' };
      return;
    }
    run(() => removeWclKey());
  }

  onMount(() => {
    if (!__PREVIEW__) run(() => getAccountSettings());
  });
</script>

<svelte:head><title>Your settings · toads</title></svelte:head>

<h1>Your settings</h1>

{#if message}<p class="warn" role="status">{message}</p>{/if}

{#if settings}
  <div class="grid">
    <section class="card">
      <h2>Your name on the hub</h2>
      <p class="muted">Other members see you as <strong>{settings.shown_name}</strong>.</p>
      <fieldset disabled={busy}>
        <legend>Show me as</legend>
        {#each settings.name_options as option (optionKey(option))}
          <label>
            <input
              type="radio"
              name="shown-name"
              checked={optionKey(option) === chosen}
              onchange={() => pick(option)}
            />
            {option.name}
            <span class="muted">{option.source === 'discord' ? '(Discord nickname)' : '(character)'}</span>
          </label>
        {/each}
      </fieldset>
      {#if settings.name_options.length === 1}
        <p class="muted">Claim a character on the <a href="{base}/me/claim">claim page</a> to go by its name.</p>
      {/if}
    </section>

    <section class="card">
      <h2>Your Warcraft Logs key</h2>
      <p class="muted">
        With your own key, analyses you ask for use your Warcraft Logs allowance instead of the guild's. Create a
        client at warcraftlogs.com/api/clients and paste its id and secret. The hub stores them encrypted and never
        shows them again.
      </p>
      <p role="status">{wclKeyLabel(settings)}</p>
      <form class="key" onsubmit={save}>
        <label>
          Client id
          <input autocomplete="off" spellcheck="false" required bind:value={clientId} disabled={busy} />
        </label>
        <label>
          Client secret
          <input type="password" autocomplete="off" required bind:value={clientSecret} disabled={busy} />
        </label>
        <div class="actions">
          <button class="btn primary" type="submit" disabled={busy}>{settings.wcl_key ? 'Replace key' : 'Save key'}</button>
          {#if settings.wcl_key}
            <button class="btn danger" type="button" onclick={remove} disabled={busy}>Remove key</button>
          {/if}
        </div>
      </form>
    </section>
  </div>
{/if}

<style>
  /* Each label sits above its field, full width, so the key form reads the same on a phone and a wide screen. */
  .key { display: grid; gap: 0.75rem; }
  .key label { display: grid; gap: 0.25rem; color: var(--muted); font-size: 0.9rem; }
  .key input {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.5rem;
    font: inherit;
  }
  .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  fieldset label { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; padding: 0.2rem 0; }
</style>
