/**
 * A Svelte action for a `.scroll` box: while its table is wider than the box, make the box focusable so keyboard users
 * can scroll it with the arrow keys (axe's scrollable-region-focusable). A box that fits stays out of the tab order.
 */
export function scrollable(node: HTMLElement) {
  const update = () => {
    if (node.scrollWidth > node.clientWidth + 1) node.tabIndex = 0;
    else node.removeAttribute('tabindex');
  };
  update();
  const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(update);
  observer?.observe(node);
  if (node.firstElementChild) observer?.observe(node.firstElementChild);
  return { destroy: () => observer?.disconnect() };
}
