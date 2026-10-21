<script lang="ts">
  import { characterQuery, MIN_CHARACTER_QUERY, statusLabel, type CharacterMatch, type Claim } from '$lib/api';

  // Claim flow (REQ-HUB-CLAIM-001/003/004, REQ-HUB-PRIV-003). Who is claiming comes from the Discord sign-in; the
  // member only picks the character, by name, from those seen in the guild's logs.
  let {
    claims,
    signedInAs = null,
    message = '',
    busy = false,
    search,
    onclaim,
    onunclaim
  }: {
    claims: Claim[];
    /** The signed-in member's name in the Toads Discord, so it is plain who the claim is for. */
    signedInAs?: string | null;
    message?: string;
    busy?: boolean;
    search: (query: string) => Promise<CharacterMatch[]>;
    onclaim: (character: CharacterMatch) => void;
    onunclaim: (claim: Claim) => void;
  } = $props();

  let query = $state('');
  let matches = $state<CharacterMatch[]>([]);
  let searched = $state('');
  let searchFailed = $state(false);
  let timer: ReturnType<typeof setTimeout> | undefined;
  /** The claim whose Unclaim is waiting for a second press. */
  let unclaiming = $state<Claim['id'] | null>(null);

  // A rejected claim can be made again, so only live claims hide the Claim button.
  const mine = $derived(new Set(claims.filter((c) => c.status !== 'rejected').map((c) => c.character_id)));

  function oninput() {
    clearTimeout(timer);
    const q = characterQuery(query);
    if (q === searched && !searchFailed) return; // only whitespace changed
    // Results for an older query never stay claimable while the new one runs.
    matches = [];
    searched = '';
    searchFailed = false;
    if (q.length < MIN_CHARACTER_QUERY) return;
    timer = setTimeout(async () => {
      let found: CharacterMatch[] = [];
      let failed = false;
      try {
        found = await search(q);
      } catch {
        failed = true;
      }
      if (characterQuery(query) !== q) return; // a later keystroke owns the list now
      matches = found;
      searchFailed = failed;
      searched = q;
    }, 250);
  }
</script>

<h1>Claim your characters</h1>
<p class="muted">
  {#if signedInAs}You're signed in with Discord as <strong>{signedInAs}</strong>, so the hub already knows who you are.{/if}
  Find your character by its in-game name. One whose name matches your nickname in the Toads Discord is approved at
  once; anything else waits for an officer of your raid day. Unclaiming detaches you straight away; the raid history
  stays.
</p>

<div class="grid">
  <section class="card">
    <h2>Claim a character</h2>
    <label>
      Character name
      <input type="search" autocomplete="off" placeholder="e.g. Hopscotch" bind:value={query} {oninput} disabled={busy} />
    </label>
    {#if searchFailed}
      <p class="warn" role="status">Search isn't answering; try again.</p>
    {:else if query.trim().length > 0 && query.trim().length < MIN_CHARACTER_QUERY}
      <p class="muted">Keep typing: at least {MIN_CHARACTER_QUERY} letters.</p>
    {:else if searched && matches.length === 0}
      <p class="muted" role="status">
        No character called “{searched}” has appeared in the guild's logs yet. Characters show up after their first
        logged raid with the guild.
      </p>
    {:else if matches.length > 0}
      <ul class="matches">
        {#each matches as m (m.id)}
          <li>
            <span>{m.name}{#if m.player_class}<span class="muted"> · {m.player_class}</span>{/if}</span>
            {#if mine.has(m.id)}
              <span class="muted">Yours</span>
            {:else}
              <button type="button" class="claim" disabled={busy} onclick={() => onclaim(m)}>Claim</button>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
    {#if message}<p class="warn" role="status">{message}</p>{/if}
  </section>

  <section class="card">
    <h2>Your claims</h2>
    {#if claims.length === 0}
      <p class="muted">No claims yet.</p>
    {:else}
      <table>
        <thead><tr><th>Character</th><th>Raid day</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {#each claims as c (c.id)}
            <tr>
              <td>{c.character_name}</td>
              <td>{c.raid_day_id ?? 'Guild'}</td>
              <td class={c.status === 'approved' ? 'ok' : c.status === 'rejected' ? 'bad' : 'warn'}>{statusLabel(c)}</td>
              <td>
                {#if unclaiming === c.id}
                  <span class="confirm" role="group" aria-label="Confirm unclaiming {c.character_name}">
                    <span class="muted small">{c.status === 'approved' ? 'Claiming it again may wait for an officer.' : 'Your claim is withdrawn.'}</span>
                    <button type="button" class="danger" disabled={busy} onclick={() => ((unclaiming = null), onunclaim(c))}>
                      Unclaim {c.character_name}
                    </button>
                    <button type="button" disabled={busy} onclick={() => (unclaiming = null)}>Keep it</button>
                  </span>
                {:else}
                  <button type="button" disabled={busy} onclick={() => (unclaiming = c.id)}>
                    Unclaim<span class="sr-only"> {c.character_name}</span>
                  </button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>
</div>

<style>
  label { display: grid; gap: 0.25rem; color: var(--muted); font-size: 0.9rem; }
  input { background: var(--bg); color: var(--text); border: 1px solid var(--line); border-radius: 6px; padding: 0.4rem; }
  .matches { list-style: none; margin: 0.75rem 0 0; padding: 0; display: grid; gap: 0.25rem; }
  .matches li { display: flex; justify-content: space-between; align-items: center; gap: 0.5rem; padding: 0.25rem 0; }
  button {
    background: var(--line);
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
    cursor: pointer;
  }
  button.claim { background: var(--accent); color: var(--on-accent); }
  button.danger { border-color: var(--bad); color: var(--bad-text); background: none; }
  .confirm { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; }
  .small { font-size: 0.85rem; }
</style>
