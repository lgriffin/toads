<script lang="ts">
  import ReferenceView from '$lib/components/ReferenceView.svelte';
  import { MOCK_NOW, referenceComparison, referenceOverview } from '$lib/mock/data';
  import {
    comparisonKey,
    reportCode,
    type ComparisonResponse,
    type JobKind,
    type ReferenceActions,
    type ReferenceJob,
    type ReferenceOverview
  } from '$lib/reference';

  // Preview: every action changes this page's copy of the sample data only; nothing reaches Warcraft Logs.
  let overview = $state<ReferenceOverview>(structuredClone(referenceOverview));
  const sampleKey = comparisonKey(
    referenceComparison.comparison.guild.report_id,
    referenceComparison.comparison.reference.report_id
  );
  let openKey = $state<string | null>(sampleKey);
  let comparison = $state<ComparisonResponse | null>(referenceComparison);
  let message = $state('');

  let tick = 0;
  function now(): string {
    tick += 1;
    return new Date(MOCK_NOW.getTime() + tick * 60_000).toISOString();
  }

  function job(kind: JobKind, report: string, ok: boolean, text: string) {
    const at = now();
    const entry: ReferenceJob = {
      id: `job-local-${tick}`,
      kind,
      status: ok ? 'done' : 'failed',
      message: text,
      report,
      created_at: at,
      updated_at: at
    };
    overview.jobs = [entry, ...overview.jobs].slice(0, 10);
    message = text;
    return true;
  }

  const titleOf = (report: string) => overview.references.find((r) => r.report_id === report)?.title ?? report;

  const actions: ReferenceActions = {
    async connect() {
      overview.login = { ...overview.login, connected: true, status: 'working', connected_by: 'Hopscotch', connected_at: now() };
      message = 'Preview: the login is pretend; nothing opened Warcraft Logs.';
      return true;
    },
    async disconnect() {
      overview.login = { ...overview.login, connected: false, status: null, connected_by: null, connected_at: null };
      message = 'Disconnected the Warcraft Logs login.';
      return true;
    },
    async importReport(report) {
      return job('import', reportCode(report) ?? report, false, 'Preview: nothing is fetched from Warcraft Logs here.');
    },
    async relabel(report, label) {
      overview.references = overview.references.map((r) => (r.report_id === report ? { ...r, label } : r));
      return job('label', report, true, `Relabelled ${titleOf(report)}.`);
    },
    async remove(report) {
      const title = titleOf(report);
      overview.references = overview.references.filter((r) => r.report_id !== report);
      overview.comparisons = overview.comparisons.filter((c) => c.reference_report !== report);
      if (openKey?.endsWith(`/${report}`)) {
        openKey = null;
        comparison = null;
      }
      return job('delete', report, true, `Deleted ${title}.`);
    },
    async compare(guildReport, referenceReport) {
      const key = comparisonKey(guildReport, referenceReport);
      if (key !== sampleKey) {
        return job('compare', guildReport, false, 'Preview: only the Gruul pairing has sample data.');
      }
      openKey = key;
      comparison = referenceComparison;
      return job('compare', guildReport, true, `Compared with ${titleOf(referenceReport)}.`);
    },
    async open(guildReport, referenceReport) {
      openKey = comparisonKey(guildReport, referenceReport);
      comparison = openKey === sampleKey ? referenceComparison : null;
      message = comparison ? '' : 'Preview: only the Gruul pairing has sample data.';
      return comparison !== null;
    }
  };
</script>

<h1>Reference comparison</h1>
<p class="muted">
  Compare one of our raids with another guild's. Wednesday officers see Wednesday's raids.
</p>
<ReferenceView {overview} {comparison} {openKey} busy={false} {message} error="" {actions} />
