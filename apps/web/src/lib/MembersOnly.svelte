<script lang="ts">
  import { base } from '$app/paths';
</script>

<section class="card members-only">
  <h1>Members only</h1>
  <p>
    You signed in with Discord, but that account is not in the Toads server, so the hub has not signed you in.
  </p>
  <p class="muted">
    If you are in the guild, join the Toads Discord (ask any officer for an invite) and then
    {#if __PREVIEW__}sign in again{:else}<a href="/auth/login" data-sveltekit-reload>sign in again</a>{/if}.
    Switched Discord accounts? Sign out of Discord first.
  </p>
  <p><a href="{base}/">Back to the home page</a></p>
</section>

<style>
  .members-only { max-width: 36rem; margin: 2rem auto; }
</style>
