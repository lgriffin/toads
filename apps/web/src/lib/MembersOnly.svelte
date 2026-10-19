<script lang="ts">
  import { base } from '$app/paths';
  import { DISCORD_INVITE } from '$lib/application';
</script>

<section class="card members-only">
  <h1>Members only</h1>
  <p>
    You signed in with Discord, but that account is not in the Toads server, so the hub has not signed you in.
  </p>
  <p class="muted">
    Join the Toads Discord at <a href={DISCORD_INVITE} target="_blank" rel="noopener noreferrer">{DISCORD_INVITE.replace('https://', '')}</a>
    and then
    {#if __PREVIEW__}<a href="{base}/login/">sign in again</a>{:else}<a href="/auth/login" data-sveltekit-reload>sign in again</a>{/if}.
    Switched Discord accounts? Sign out of Discord first.
  </p>
  <p>Applying to raid with us? Once you are in the Discord, <a href="{base}/recruit/">go back to the application</a>.</p>
  <p><a href="{base}/">Back to the home page</a></p>
</section>

<style>
  .members-only { max-width: 36rem; margin: 2rem auto; }
</style>
