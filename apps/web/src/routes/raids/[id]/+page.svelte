<script lang="ts">
  import { base } from '$app/paths';
  import { mmss, shortDate } from '$lib/format';
  import type { Role } from '$lib/mock/data';

  let { data } = $props();
  let raid = $derived(data.raid);
  const roles: Role[] = ['Tank', 'Healer', 'Melee', 'Ranged'];
</script>

<p><a href="{base}/raids/">Raids &amp; Logs</a></p>
<h1>{raid.zone}</h1>
<p class="muted">
  {shortDate(raid.date)} · {raid.raidDay} team · {raid.size}-man · {raid.durationMin} min · {raid.deaths} deaths ·
  <span class="pill">WCL {raid.code}</span>
</p>

<div class="grid">
  <section class="card">
    <h2>Bosses</h2>
    <table>
      <thead><tr><th>Boss</th><th class="num">Wipes</th><th class="num">Kill</th></tr></thead>
      <tbody>
        {#each raid.bosses as b}
          <tr>
            <td>{b.name}</td>
            <td class="num">{b.wipes}</td>
            <td class="num" class:ok={b.killed} class:bad={!b.killed}>{b.killed ? mmss(b.seconds) : 'No kill'}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>Role breakdown</h2>
    <div class="roles">
      {#each roles as role}
        <div><span class="n">{raid.roles[role]}</span><span class="muted">{role}</span></div>
      {/each}
    </div>
  </section>

  <section class="card">
    <h2>Consumable coverage</h2>
    <table>
      <thead><tr><th>Consumable</th><th class="num">Boss</th><th class="num">Trash</th></tr></thead>
      <tbody>
        {#each raid.consumes as c}
          <tr>
            <td>{c.name}</td>
            <td class="num" class:warn={c.boss < 80}>{c.boss}%</td>
            <td class="num" class:warn={c.trash < 50}>{c.trash}%</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>Interrupts and cancelled casts</h2>
    <div class="two">
      <table>
        <thead><tr><th>Interrupts</th><th class="num"></th></tr></thead>
        <tbody>
          {#each raid.interrupts as p}<tr><td>{p.player}</td><td class="num">{p.count}</td></tr>{/each}
        </tbody>
      </table>
      <table>
        <thead><tr><th>Cancelled</th><th class="num"></th></tr></thead>
        <tbody>
          {#each raid.cancelledCasts as p}<tr><td>{p.player}</td><td class="num">{p.count}</td></tr>{/each}
        </tbody>
      </table>
    </div>
  </section>
</div>

<style>
  .roles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; text-align: center; }
  .roles div { display: flex; flex-direction: column; }
  .n { font-size: 1.6rem; }
  .two { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
</style>
