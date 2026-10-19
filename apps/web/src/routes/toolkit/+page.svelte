<script lang="ts">
  import { goto } from '$app/navigation';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';

  // The toolkit became Hub features (/features); old links and bookmarks land there.
  onMount(() => goto(`${base}/features/`, { replaceState: true }));
</script>

<svelte:head>
  <title>Hub features · Toads</title>
  <link rel="canonical" href="{base}/features/" />
  <!-- Redirects without JavaScript too (crawlers, the static preview); goto() above handles the client side. -->
  <meta http-equiv="refresh" content="0; url={base}/features/" />
</svelte:head>

<p>This page moved to <a href="{base}/features/">Hub features</a>.</p>
