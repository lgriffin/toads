<script lang="ts">
  import { base } from '$app/paths';
  import { WELCOME_STEPS, isOutside } from '$lib/welcome';

  // The first sign-in checklist. Each step is a link to the page that does it; nothing here is stored yet.
</script>

<svelte:head><title>Welcome · Toads</title></svelte:head>

<h1>Welcome to the pond</h1>
<p class="lede">Six steps get you set up. Do them in any order; each one opens the page that does it.</p>

<ol class="steps">
  {#each WELCOME_STEPS as step (step.id)}
    <li class="card">
      <h2>{step.title}</h2>
      <p>{step.body}</p>
      {#if isOutside(step.href)}
        <a class="btn" href={step.href} target="_blank" rel="noopener noreferrer">{step.action}</a>
      {:else}
        <a class="btn" href="{base}{step.href}/">{step.action}</a>
      {/if}
    </li>
  {/each}
</ol>

<p><a class="btn primary" href="{base}/hub/">Go to your hub</a></p>

<style>
  .lede { max-width: 44rem; margin: 0 0 1.25rem; }
  .steps { list-style: none; margin: 0 0 1.5rem; padding: 0; display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); counter-reset: step; }
  .steps li { display: grid; gap: 0.5rem; align-content: start; counter-increment: step; }
  .steps h2 { margin: 0; }
  .steps h2::before { content: counter(step) '. '; color: var(--accent); }
  .steps p { margin: 0; }
  .steps .btn { justify-self: start; }
</style>
