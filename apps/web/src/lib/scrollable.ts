/**
 * A Svelte action for a `.scroll` box: while its content is wider than the box, make the box focusable so keyboard
 * users can scroll it with the arrow keys (axe's scrollable-region-focusable). A box that fits stays out of the tab
 * order. It rechecks when the box or any child resizes, when children come and go, and when a `<details>` inside opens.
 */
export function scrollable(node: HTMLElement) {
  const update = () => {
    if (node.scrollWidth > node.clientWidth + 1) node.tabIndex = 0;
    else node.removeAttribute('tabindex');
  };
  const resized = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(update);
  const watch = () => {
    resized?.disconnect();
    resized?.observe(node);
    for (const child of Array.from(node.children)) resized?.observe(child);
  };
  const changed = typeof MutationObserver === 'undefined' ? null : new MutationObserver(() => (watch(), update()));
  changed?.observe(node, { childList: true, subtree: true });
  // `toggle` does not bubble, so listen in the capture phase for any <details> inside.
  node.addEventListener('toggle', update, true);
  watch();
  update();
  return {
    destroy: () => {
      resized?.disconnect();
      changed?.disconnect();
      node.removeEventListener('toggle', update, true);
    }
  };
}
