<script lang="ts">
  // An official game logo, supplied by the guild under static/brand/ (see landing.ts). Until the file is there it draws
  // nothing and reports `failed`, so the page never shows a broken image and the parent can close the gap.
  let {
    src,
    alt,
    height = 96,
    failed = $bindable(false)
  }: { src: string; alt: string; height?: number; failed?: boolean } = $props();
  // Drawn only once mounted, so the error handler is attached before the browser tries the file.
  let mounted = $state(false);
  $effect(() => {
    mounted = true;
  });
</script>

{#if mounted && !failed}
  <img {src} {alt} style="height:{height}px" onerror={() => (failed = true)} />
{/if}

<style>
  img { display: block; width: auto; max-width: 100%; object-fit: contain; }
</style>
