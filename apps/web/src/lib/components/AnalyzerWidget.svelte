<script lang="ts">
  import { base } from '$app/paths';
  import { barPercent, linkHref, type PayloadWidget } from '$lib/home-payload';

  // One widget of the analyzer's home page. Payload text (names, zones) comes from logs, so it is only ever
  // interpolated as text, never with {@html}. `title` is used while the page has no payload for this widget yet.
  let { widget, title, missing }: { widget: PayloadWidget | null; title: string; missing: string } = $props();

  const hid = $derived(`aw-${widget?.id ?? title.toLowerCase().replace(/[^a-z]+/g, '-')}`);
  // The static preview prerenders with trailing slashes.
  const href = (link: Parameters<typeof linkHref>[0]) => {
    const to = linkHref(link, base);
    return to && __PREVIEW__ ? `${to}/` : to;
  };
  const open = $derived(href(widget?.link));
</script>

<section class="card aw" aria-labelledby="{hid}-h">
  <div class="top">
    <h2 id="{hid}-h">{widget?.title ?? title}</h2>
    {#if open}<a href={open}>Open</a>{/if}
  </div>
  {#if widget?.subtitle}<p class="muted sub">{widget.subtitle}</p>{/if}

  {#if !widget}
    <p class="muted">{missing}</p>
  {:else if widget.error}
    <p class="err">{widget.error}</p>
  {:else if widget.empty}
    <p class="muted">{widget.empty}</p>
  {:else if widget.kind === 'stats'}
    <dl class="tiles">
      {#each widget.tiles as t (t.label)}
        <div class="tile" title={t.hint || undefined}>
          <dt class="muted">{t.label}</dt>
          <dd>{t.display}</dd>
        </div>
      {/each}
    </dl>
  {:else if widget.kind === 'table'}
    <div class="scroll">
      <table aria-labelledby="{hid}-h">
        <thead>
          <tr>
            {#each widget.columns as c (c.key)}<th class:num={c.align === 'right'} scope="col">{c.label}</th>{/each}
          </tr>
        </thead>
        <tbody>
          {#each widget.rows as row, i (i)}
            {@const to = href(row.link)}
            <tr>
              {#each widget.columns as c, j (c.key)}
                <td class:num={c.align === 'right'}>
                  {#if to && j === 0}<a href={to}>{row.cells[c.key] ?? ''}</a>{:else}{row.cells[c.key] ?? ''}{/if}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else if widget.kind === 'list'}
    <ul class="items">
      {#each widget.items as item, i (i)}
        {@const to = href(item.link)}
        <li>
          {#if to}<a href={to}>{item.label}</a>{:else}<span>{item.label}</span>{/if}
          {#if item.detail}<span class="muted">{item.detail}</span>{/if}
        </li>
      {/each}
    </ul>
  {:else if widget.kind === 'bars'}
    {@const bars = widget.bars}
    <ul class="bars">
      {#each bars as b, i (i)}
        <li>
          <span class="label"><span>{b.label}</span><span class="muted">{b.display}</span></span>
          <span class="bar" aria-hidden="true"><span style="width: {barPercent(bars, b.value)}%"></span></span>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .top { display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }
  .sub { margin: -0.5rem 0 0.75rem; font-size: 0.9rem; }
  .tiles { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr)); margin: 0; }
  .tile { background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 0.6rem 0.75rem; }
  .tile dt { font-size: 0.8rem; }
  .tile dd { margin: 0.2rem 0 0; font-size: 1.25rem; font-variant-numeric: tabular-nums; }
  .items { list-style: none; margin: 0; padding: 0; }
  .items li { display: flex; flex-direction: column; padding: 0.45rem 0; border-bottom: 1px solid var(--line); }
  .bars { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.6rem; }
  .label { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.9rem; }
  .bar { display: block; height: 0.5rem; margin-top: 0.25rem; border-radius: 999px; background: var(--line); overflow: hidden; }
  .bar span { display: block; height: 100%; background: var(--accent); }
</style>
