import { tick } from 'svelte';

/** A Svelte action: focus the element when it appears, so a confirming step takes over from the button that opened it. */
export function focusOnMount(node: HTMLElement) {
  node.focus();
}

/** Focus the element with this id once Svelte has redrawn, e.g. the button a cancelled confirming step replaced. */
export async function focusById(id: string) {
  await tick();
  document.getElementById(id)?.focus();
}
