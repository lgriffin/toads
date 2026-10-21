<script lang="ts">
  import { altNamed, mainError, sameName, type MainBackend, type MyMain } from '$lib/main-swap';

  // Under Me's character picker: the member's main, and a way to ask an officer to make the alt they are looking at
  // their main instead (the ask waits on their raid night's claims panel). Alts with no guild raids are not in the
  // picker, so they get their own buttons. Every failure lands here as a message.
  let { backend, viewing, shown = [] }: { backend: MainBackend; viewing: string | null; shown?: readonly string[] } =
    $props();

  let mine = $state<MyMain | null>(null);
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  async function load() {
    try {
      mine = await backend.mine();
    } catch {
      mine = null;
    }
  }
  $effect(() => {
    load();
  });

  const pending = $derived(mine?.request?.status === 'pending' ? mine.request : null);
  const turnedDown = $derived(mine?.request?.status === 'rejected' ? mine.request : null);
  const viewedAlt = $derived(mine ? altNamed(mine, viewing) : undefined);
  const unraided = $derived(mine ? mine.alts.filter((a) => !shown.some((s) => sameName(s, a.character_name))) : []);

  async function act(action: () => Promise<unknown>, done: string) {
    busy = true;
    try {
      await action();
      [message, failed] = [done, false];
    } catch (e) {
      [message, failed] = [mainError(e), true];
    } finally {
      await load();
      busy = false;
    }
  }

  const ask = (id: number, name: string) =>
    act(() => backend.ask(id), `Asked to make ${name} your main. Your raid night’s officers decide it.`);
  const withdraw = () => act(() => backend.withdraw(), 'Withdrew your main swap.');
</script>

{#if mine?.main}
  <div class="main-swap">
    {#if pending}
      <p>
        Waiting for an officer to make <strong>{pending.character_name}</strong> your main instead of
        {mine.main.character_name}.
        <button type="button" class="btn" disabled={busy} onclick={withdraw}>Withdraw</button>
      </p>
    {:else if turnedDown}
      <p class="muted">
        An officer kept {mine.main.character_name} as your main instead of {turnedDown.character_name}{#if turnedDown.reason}:
          “{turnedDown.reason}”{/if}.
      </p>
    {/if}
    {#if viewedAlt && !sameName(pending?.character_name, viewedAlt.character_name)}
      <p>
        <button
          type="button"
          class="btn"
          disabled={busy}
          onclick={() => ask(viewedAlt.character_id, viewedAlt.character_name)}
        >
          Make {viewedAlt.character_name} my main{pending ? ' instead' : ''}
        </button>
        <span class="muted small">An officer of your raid night approves the swap.</span>
      </p>
    {/if}
    {#if unraided.length}
      <p class="muted small">
        No guild raids yet:
        {#each unraided as a (a.character_id)}
          {#if sameName(pending?.character_name, a.character_name)}
            <span class="alt">{a.character_name} (asked for main)</span>
          {:else}
            <button type="button" class="link" disabled={busy} onclick={() => ask(a.character_id, a.character_name)}>
              Make {a.character_name} my main
            </button>
          {/if}
        {/each}
      </p>
    {/if}
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}
  </div>
{/if}

<style>
  .main-swap { display: grid; gap: 0.4rem; margin-bottom: 0.75rem; }
  .main-swap p { margin: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem 0.6rem; }
  .small { font-size: 0.85rem; }
  .link {
    background: none; border: 0; padding: 0; font: inherit; color: var(--accent); text-decoration: underline;
    cursor: pointer;
  }
</style>
