<script lang="ts">
  import { base } from '$app/paths';
  import { dateTime, shortDate } from '$lib/format';
  import { announcements, nextRaid, raids, type Role } from '$lib/mock/data';

  const roles: Role[] = ['Tank', 'Healer', 'Melee', 'Ranged'];
  const latest = raids.slice(0, 3);
</script>

<h1>Toads Hub</h1>

<div class="grid">
  <section class="card">
    <h2>Next raid</h2>
    <p class="big">{nextRaid.zone}</p>
    <p class="muted">{nextRaid.raidDay} team · {dateTime(nextRaid.start)} server time</p>
    <table>
      <thead><tr><th>Role</th><th class="num">Signed</th><th class="num">Needed</th></tr></thead>
      <tbody>
        {#each roles as role}
          {@const short = nextRaid.signups[role] < nextRaid.needed[role]}
          <tr>
            <td>{role}</td>
            <td class="num" class:warn={short}>{nextRaid.signups[role]}</td>
            <td class="num">{nextRaid.needed[role]}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </section>

  <section class="card">
    <h2>Latest logs</h2>
    <ul class="list">
      {#each latest as raid}
        {@const kills = raid.bosses.filter((b) => b.killed).length}
        <li>
          <a href="{base}/raids/{raid.id}/">{raid.zone}</a>
          <span class="muted">{shortDate(raid.date)} · {raid.raidDay} · {kills}/{raid.bosses.length} bosses</span>
        </li>
      {/each}
    </ul>
    <a href="{base}/raids/">All raids</a>
  </section>
</div>

<section class="card news">
  <h2>Announcements</h2>
  {#each announcements as a}
    <article>
      <h3>{a.title}</h3>
      <p>{a.body}</p>
      <p class="muted small">{a.author} · {shortDate(a.posted)}</p>
    </article>
  {/each}
</section>

<style>
  .big { font-size: 1.3rem; margin: 0; }
  .list { list-style: none; padding: 0; margin: 0 0 0.75rem; }
  .list li { display: flex; flex-direction: column; padding: 0.5rem 0; border-bottom: 1px solid var(--line); }
  .news { margin-top: 1rem; }
  h3 { font-size: 1rem; margin: 0 0 0.25rem; }
  article + article { border-top: 1px solid var(--line); padding-top: 0.75rem; }
  .small { font-size: 0.8rem; }
</style>
