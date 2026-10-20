<script lang="ts">
  import { base } from '$app/paths';
  import { NIGHTS_IN_WORDS } from '$lib/nights';
  import {
    ROLE_BADGES_CHANGED,
    ROLE_BADGE_GROUPS,
    linksByBadge,
    roleBadge,
    roleBadgeError,
    type RoleBadgeLink,
    type RoleBadgesAdmin,
    type RoleBadgesBackend
  } from '$lib/role-badges';

  // The super admins' badge desk: tie a badge toad to a Discord server role, and every member holding that role wears
  // it beside their name. The API checks the permission (manage_role_badges); this page only shows the desk.
  let { backend }: { backend: RoleBadgesBackend } = $props();

  let data = $state<RoleBadgesAdmin | null>(null);
  let loadError = $state('');
  let roleId = $state('');
  let badgeId = $state('');
  let busy = $state(false);
  let message = $state('');
  let failed = $state(false);

  const groups = $derived(linksByBadge(data?.links ?? []));
  const chosen = $derived(roleBadge(badgeId));
  const alreadyTied = $derived(!!data?.links.some((l) => l.discord_role_id === roleId && l.badge.id === badgeId));

  async function load() {
    try {
      data = await backend.load();
      loadError = '';
    } catch (e) {
      loadError = roleBadgeError(e);
    }
  }
  $effect(() => {
    load();
  });

  async function tie(event: SubmitEvent) {
    event.preventDefault();
    if (!roleId || !chosen) return;
    busy = true;
    try {
      const link = await backend.tie(roleId, chosen.id);
      message = `Everyone with the ${link.role_name} role now wears the ${link.badge.name} badge.`;
      failed = false;
      badgeId = '';
      window.dispatchEvent(new Event(ROLE_BADGES_CHANGED));
      await load();
    } catch (e) {
      message = roleBadgeError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }

  async function untie(link: RoleBadgeLink) {
    busy = true;
    try {
      await backend.untie(link.discord_role_id, link.badge.id);
      message = `The ${link.role_name} role no longer earns the ${link.badge.name} badge.`;
      failed = false;
      window.dispatchEvent(new Event(ROLE_BADGES_CHANGED));
      await load();
    } catch (e) {
      message = roleBadgeError(e);
      failed = true;
    } finally {
      busy = false;
    }
  }
</script>

<section class="card desk" aria-labelledby="role-badges-h">
  <h2 id="role-badges-h">Badges from Discord roles</h2>
  <p class="muted lede">
    Pick a role from the Toads server and the badge it earns. Everyone holding that role wears the badge beside their
    name on the hub, and loses it when the role is taken away in Discord.
  </p>

  {#if loadError}
    <p class="err" role="alert">{loadError}</p>
  {:else if !data}
    <p class="muted" role="status">Loading…</p>
  {:else}
    {#if data.roles === null}
      <p class="warn" role="status">
        Discord is not answering, so the server's roles cannot be listed just now. The badges already tied still work.
      </p>
    {/if}
    <form onsubmit={tie}>
      <div class="field">
        <label for="role-badge-role">Discord role</label>
        <select id="role-badge-role" bind:value={roleId} required disabled={!data.roles?.length}>
          <option value="" disabled>{data.roles?.length ? 'Choose a role' : 'No roles to choose'}</option>
          {#each data.roles ?? [] as r (r.id)}<option value={r.id}>{r.name}</option>{/each}
        </select>
      </div>

      <fieldset>
        <legend>Badge it earns</legend>
        {#each ROLE_BADGE_GROUPS as g (g.label)}
          <div class="group" role="group" aria-labelledby="role-badges-{g.ids[0]}">
            <span class="group-label" id="role-badges-{g.ids[0]}">{g.label}</span>
            <div class="options">
              {#each g.ids as id (id)}
                {@const b = roleBadge(id)}
                {#if b}
                  <label class="option" class:picked={badgeId === b.id}>
                    <input type="radio" name="role-badge" value={b.id} bind:group={badgeId} />
                    <img src="{base}/logos/{b.file}.svg" alt="" width="48" height="42" loading="lazy" />
                    <span>{b.name}</span>
                  </label>
                {/if}
              {/each}
            </div>
          </div>
        {/each}
      </fieldset>

      <div class="submit">
        {#if chosen}
          <img class="preview-badge" src="{base}/logos/{chosen.file}-badge.svg" alt="" width="72" height="86" />
        {/if}
        <button class="btn primary" type="submit" disabled={busy || !roleId || !chosen || alreadyTied}>
          Give the badge to this role
        </button>
        {#if alreadyTied}<span class="hint">That role already earns this badge.</span>{/if}
      </div>
    </form>
    {#if message}<p class={failed ? 'err' : 'ok'} role="status">{message}</p>{/if}

    <h3>Roles that earn a badge</h3>
    {#if groups.length === 0}
      <p class="muted">
        No role earns a badge yet. Start with the {NIGHTS_IN_WORDS} raider roles, then the tank and healer roles.
      </p>
    {:else}
      <ul class="ties">
        {#each groups as g (g.badge.id)}
          <li>
            <img src="{base}/logos/{g.badge.file}-badge.svg" alt="" width="56" height="67" loading="lazy" />
            <div>
              <strong>{g.badge.name}</strong>
              <ul class="roles">
                {#each g.roles as link (link.discord_role_id)}
                  <li>
                    <span class="role">{link.role_name || `Role ${link.discord_role_id}`}</span>
                    <button type="button" class="btn small" disabled={busy} onclick={() => untie(link)}>
                      Remove<span class="sr-only"> {g.badge.name} from {link.role_name}</span>
                    </button>
                  </li>
                {/each}
              </ul>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</section>

<style>
  .desk { display: grid; gap: 0.9rem; }
  .desk h2, .desk h3 { margin: 0; }
  .desk h3 { margin-top: 0.75rem; font-size: 1rem; }
  .lede { margin: 0; max-width: 62ch; }
  form { display: grid; gap: 1rem; }
  .field { max-width: 22rem; }
  fieldset { border: 0; margin: 0; padding: 0; display: grid; gap: 0.75rem; min-width: 0; }
  legend { padding: 0; margin-bottom: 0.4rem; }
  .group { display: grid; gap: 0.35rem; }
  .group-label { font-size: 0.8rem; color: var(--muted); }
  .options { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .option {
    position: relative;
    display: grid;
    justify-items: center;
    gap: 0.2rem;
    width: 5.75rem;
    padding: 0.5rem 0.25rem 0.45rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--bg);
    font-size: 0.8rem;
    text-align: center;
    cursor: pointer;
    transition: border-color 160ms cubic-bezier(0.16, 1, 0.3, 1), background-color 160ms cubic-bezier(0.16, 1, 0.3, 1);
  }
  .option:hover { border-color: var(--muted); }
  .option.picked { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, var(--bg)); }
  .option:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: 2px; }
  .option input { position: absolute; opacity: 0; pointer-events: none; }
  .option img { width: 3rem; height: auto; }
  .submit { display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem; }
  .preview-badge { width: 4.5rem; height: auto; }
  .ties { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.25rem; }
  .ties > li { display: flex; gap: 0.85rem; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--line); }
  .ties > li > img { width: 3.5rem; height: auto; flex: none; }
  .roles { list-style: none; margin: 0.35rem 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .roles li { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.15rem 0.2rem 0.15rem 0.6rem; border-radius: 999px; background: var(--line); }
  .role { font-size: 0.9rem; }
  .btn.small { padding: 0.15rem 0.55rem; font-size: 0.8rem; border-radius: 999px; }
  @media (prefers-reduced-motion: reduce) {
    .option { transition: none; }
  }
</style>
