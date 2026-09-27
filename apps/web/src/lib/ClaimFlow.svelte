<script lang="ts">
  import { statusLabel, type Claim } from '$lib/api';

  // Placeholder claim flow (REQ-HUB-CLAIM-001/003, REQ-HUB-PRIV-003). A picker of characters seen in the
  // guild's logs replaces the id box once the API reads wcl-store's characters.
  let {
    claims,
    message = '',
    busy = false,
    onclaim,
    onunclaim
  }: {
    claims: Claim[];
    message?: string;
    busy?: boolean;
    onclaim: (characterId: number) => void;
    onunclaim: (claim: Claim) => void;
  } = $props();

  let characterId = $state('');

  function submit(event: SubmitEvent) {
    event.preventDefault();
    const id = Number(characterId);
    if (Number.isInteger(id) && id > 0) onclaim(id);
  }
</script>

<h1>Claim your characters</h1>
<p class="muted">
  A character whose name matches your nickname in the Toads Discord is approved at once. Anything else waits for an
  officer of your raid day. Unclaiming detaches you straight away; the raid history stays.
</p>

<div class="grid">
  <section class="card">
    <h2>Claim a character</h2>
    <form onsubmit={submit}>
      <label>
        Character id
        <input type="number" min="1" step="1" required bind:value={characterId} disabled={busy} />
      </label>
      <button type="submit" disabled={busy}>Claim</button>
    </form>
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
              <td><button type="button" disabled={busy} onclick={() => onunclaim(c)}>Unclaim</button></td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>
</div>

<style>
  form { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: end; }
  label { display: grid; gap: 0.25rem; color: var(--muted); font-size: 0.9rem; }
  input { background: var(--bg); color: var(--text); border: 1px solid var(--line); border-radius: 6px; padding: 0.4rem; }
  button {
    background: var(--line);
    color: var(--text);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
    cursor: pointer;
  }
  button[type='submit'] { background: var(--accent); color: #0f1411; }
</style>
