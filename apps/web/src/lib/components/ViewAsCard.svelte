<script lang="ts">
  import { ApiError } from '$lib/api';
  import { VIEW_AS_ROLES, viewAsLabel, type ViewAsRole } from '$lib/view-as';

  // The super admins' "View as" (docs/admin.md "View as"): see the hub as one raid night's raider or officer, launch
  // hold included, to check what they see. Read only until "Back to super admin" in the bar at the top. The API checks
  // the permission (view_as); this card only shows itself.
  let {
    nights,
    onview
  }: { nights: { id: string; name: string }[]; onview: (role: ViewAsRole, day: string) => Promise<void> } = $props();

  let role = $state<ViewAsRole>('raider');
  let night = $state('');
  let busy = $state(false);
  let error = $state('');
  // Sunday first when it is there, as the night most often checked; otherwise the first night.
  $effect(() => {
    if (!night && nights.length) night = (nights.find((n) => n.id === 'sun') ?? nights[0]).id;
  });
  const chosen = $derived(nights.find((n) => n.id === night));

  async function view(event: SubmitEvent) {
    event.preventDefault();
    if (!night) return;
    busy = true;
    error = '';
    try {
      await onview(role, night);
    } catch (e) {
      error = e instanceof ApiError ? e.message : 'The hub did not answer. Try again.';
      busy = false;
    }
  }
</script>

<section class="card desk" aria-labelledby="view-as-h">
  <h2 id="view-as-h">View as</h2>
  <p class="lede">
    See the hub as one raid night's raider or officer: their menus, their pages and the launch hold as they get it. It
    is read only, so nothing can be changed in their name, and the bar at the top takes you back.
  </p>
  <form class="pick" onsubmit={view}>
    <fieldset>
      <legend>Role</legend>
      {#each VIEW_AS_ROLES as r (r)}
        <label><input type="radio" name="view-as-role" value={r} bind:group={role} /> {r === 'raider' ? 'Raider' : 'Officer'}</label>
      {/each}
    </fieldset>
    <div class="field">
      <label for="view-as-night">Raid night</label>
      <select id="view-as-night" bind:value={night}>
        {#each nights as n (n.id)}
          <option value={n.id}>{n.name}</option>
        {/each}
      </select>
    </div>
    <button class="btn primary" type="submit" disabled={busy || !chosen}>
      {chosen ? `View as a ${viewAsLabel({ role, name: chosen.name })}` : 'View as'}
    </button>
  </form>
  {#if error}<p class="err" role="alert">{error}</p>{/if}
</section>

<style>
  .desk { display: grid; gap: 0.75rem; align-content: start; }
  .desk h2, .desk p { margin: 0; }
  .lede { max-width: 62ch; }
  .pick { display: flex; flex-wrap: wrap; gap: 0.5rem 1rem; align-items: flex-end; }
  fieldset { display: flex; flex-wrap: wrap; gap: 0.25rem 1rem; border: 0; margin: 0; padding: 0; }
  legend { padding: 0; margin-bottom: 0.3rem; }
  fieldset label { display: inline-flex; align-items: center; gap: 0.35rem; min-height: 2.75rem; }
  .field { flex: 0 1 12rem; }
</style>
