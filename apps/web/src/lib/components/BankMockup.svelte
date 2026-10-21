<script lang="ts">
  // A mockup of the guild bank at work, for the officers' Forever launch notice: what it holds, requests arriving from
  // Discord and the site, the ledger of who got what and when, and the fairness view built from it. Sample data only;
  // the real bank page replaces it at launch.
  const STOCK = [
    { item: 'Flask of Supreme Power', have: 14, want: 20 },
    { item: 'Flask of Distilled Wisdom', have: 9, want: 15 },
    { item: 'Major Mana Potion', have: 62, want: 60 },
    { item: 'Greater Fire Protection Potion', have: 6, want: 40 },
    { item: 'Elixir of the Mongoose', have: 31, want: 30 },
    { item: 'Dense Dynamite', have: 88, want: 60 }
  ];
  const QUEUE = [
    { who: 'Croakley', what: '2 × Greater Fire Protection Potion', from: 'Discord', how: '/bank request', status: 'Waiting' },
    { who: 'Lilypadma', what: '1 × Flask of Distilled Wisdom', from: 'Site', how: 'Bank page', status: 'Waiting' },
    { who: 'Hopscotch', what: '5 × Elixir of the Mongoose', from: 'Discord', how: '/bank request', status: 'Mailed' }
  ];
  const LEDGER = [
    { when: 'Wed 21:04', who: 'Croakwell', what: '1 × Flask of Supreme Power', banker: 'Tadpolly' },
    { when: 'Wed 20:51', who: 'Hopscotch', what: '10 × Dense Dynamite', banker: 'Tadpolly' },
    { when: 'Sun 19:40', who: 'Lilypadma', what: '4 × Major Mana Potion', banker: 'Bogsworth' },
    { when: 'Sun 19:32', who: 'Croakley', what: '1 × Flask of Supreme Power', banker: 'Bogsworth' }
  ];
  // Items received over the last four weeks against raids attended in them.
  const FAIRNESS = [
    { who: 'Hopscotch', got: 7, raids: 8 },
    { who: 'Lilypadma', got: 6, raids: 8 },
    { who: 'Croakley', got: 5, raids: 6 },
    { who: 'Croakwell', got: 1, raids: 7 }
  ];
  const most = Math.max(...FAIRNESS.map((f) => f.raids));
</script>

<figure class="mockup" aria-labelledby="mock-h">
  <figcaption>
    <h3 id="mock-h">How the bank could work</h3>
    <p><span class="tag">Mockup</span> Sample names and numbers, to show the idea. Nothing here is real stock.</p>
  </figcaption>

  <div class="top">
    <section aria-labelledby="stock-h">
      <h4 id="stock-h">In the bank</h4>
      <ul class="stock">
        {#each STOCK as s (s.item)}
          {@const low = s.have < s.want * 0.5}
          <li class:low>
            <span class="name">{s.item}</span>
            <span class="count">{s.have}<span class="of"> / {s.want}</span></span>
            <span class="bar" aria-hidden="true"><span style="width: {Math.min(100, (s.have / s.want) * 100)}%"></span></span>
            {#if low}<span class="flag">Low before raid</span>{/if}
          </li>
        {/each}
      </ul>
    </section>

    <section aria-labelledby="queue-h">
      <h4 id="queue-h">Requests</h4>
      <ol class="queue">
        {#each QUEUE as q (q.who + q.what)}
          <li>
            <p class="what"><strong>{q.who}</strong> asked for {q.what}</p>
            <p class="meta">
              <span class="src" data-src={q.from}>{q.from}</span> {q.how} · <span class="status">{q.status}</span>
            </p>
          </li>
        {/each}
      </ol>
      <p class="hint">A request typed in Discord lands here beside one made on the site; the banker marks it handed over in game.</p>
    </section>
  </div>

  <section aria-labelledby="ledger-h">
    <h4 id="ledger-h">Ledger: who got what, and when</h4>
    <div class="scroll">
      <table>
        <thead><tr><th scope="col">When</th><th scope="col">Raider</th><th scope="col">Received</th><th scope="col">Banker</th></tr></thead>
        <tbody>
          {#each LEDGER as l (l.when + l.who)}
            <tr><td>{l.when}</td><td>{l.who}</td><td>{l.what}</td><td>{l.banker}</td></tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <section aria-labelledby="fair-h">
    <h4 id="fair-h">Fairness: received against raids attended, last four weeks</h4>
    <ul class="fair">
      {#each FAIRNESS as f (f.who)}
        <li>
          <span class="name">{f.who}</span>
          <span class="pair" aria-hidden="true">
            <span class="raids" style="width: {(f.raids / most) * 100}%"></span>
            <span class="got" style="width: {(f.got / most) * 100}%"></span>
          </span>
          <span class="nums">{f.got} {f.got === 1 ? 'item' : 'items'} · {f.raids} raids</span>
        </li>
      {/each}
    </ul>
    <p class="hint">Croakwell raids most weeks but has taken little: worth a word before the next raid night.</p>
  </section>
</figure>

<style>
  .mockup {
    margin: 0;
    display: grid;
    gap: 1.6rem;
    padding: 1.4rem;
    border: 1px dashed var(--bronze);
    border-radius: 12px;
    background: color-mix(in srgb, var(--ink) 55%, transparent);
  }
  figcaption p { margin: 0.3rem 0 0; color: var(--muted); }
  .tag {
    display: inline-block;
    padding: 0.05rem 0.55rem;
    margin-right: 0.35rem;
    border-radius: 999px;
    background: var(--bronze);
    color: var(--on-bronze);
    font-weight: 700;
    font-size: 0.85rem;
  }
  h4 { margin: 0 0 0.6rem; font-family: 'Cinzel', Georgia, serif; font-weight: 600; font-size: 1rem; color: var(--bronze-hi); }
  .mockup > *, .top > * { min-width: 0; }
  .top { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 19rem), 1fr)); gap: 1.6rem; }
  ul, ol { list-style: none; margin: 0; padding: 0; }

  .stock { display: grid; gap: 0.55rem; }
  .stock li { display: grid; grid-template-columns: 1fr auto; gap: 0.15rem 0.75rem; }
  .stock .count { font-variant-numeric: tabular-nums; color: var(--cream); }
  .of { color: var(--muted); }
  .bar { grid-column: 1 / -1; height: 0.4rem; border-radius: 999px; background: color-mix(in srgb, var(--muted) 15%, transparent); overflow: hidden; }
  .bar span { display: block; height: 100%; background: var(--teal); }
  .low .bar span { background: var(--warn); }
  .flag { grid-column: 1 / -1; font-size: 0.85rem; color: var(--warn); }

  .queue { display: grid; gap: 0.7rem; }
  .queue li { padding-bottom: 0.7rem; border-bottom: 1px solid var(--line); }
  .queue p { margin: 0; }
  .meta { font-size: 0.9rem; color: var(--muted); }
  .src { font-weight: 700; color: var(--teal); }
  .src[data-src='Site'] { color: var(--bronze-hi); }
  .status { color: var(--cream); }
  .hint { margin: 0.6rem 0 0; font-size: 0.92rem; color: var(--muted); max-width: 60ch; }

  .scroll { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.98rem; }
  th, td { text-align: left; padding: 0.4rem 0.75rem 0.4rem 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
  th { color: var(--muted); font-weight: 700; }
  td:first-child { font-variant-numeric: tabular-nums; color: var(--muted); }

  .fair { display: grid; gap: 0.5rem; }
  .fair li { display: grid; grid-template-columns: 7rem 1fr auto; gap: 0.75rem; align-items: center; }
  .pair { position: relative; height: 0.9rem; }
  .pair span { position: absolute; left: 0; border-radius: 999px; }
  .raids { top: 0; height: 100%; background: color-mix(in srgb, var(--muted) 18%, transparent); }
  .got { top: 0.2rem; height: 0.5rem; background: var(--bronze); }
  .nums { font-size: 0.9rem; color: var(--muted); font-variant-numeric: tabular-nums; }
  @media (max-width: 34rem) {
    .fair li { grid-template-columns: 1fr; gap: 0.2rem; }
  }
</style>
