<script lang="ts">
  import { onMount } from 'svelte';
  import { listRuns, replay } from '$lib/api/control';
  import { toasts } from '$lib/stores/toast';

  let runs: any[] = [];
  let loading = false;
  let filterOutcome = '';
  let filterCampaign = '';
  let selectedRun: any = null;

  onMount(() => { fetchRuns(); });

  async function fetchRuns() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (filterOutcome) params.outcome = filterOutcome;
      if (filterCampaign) params.campaign = filterCampaign;
      const result = await listRuns(params);
      runs = Array.isArray(result) ? result : result?.entries ?? result?.runs ?? [];
    } catch {
      toasts.warn('Could not load runs — is Control running?');
      runs = [];
    } finally {
      loading = false;
    }
  }

  async function doReplay(runId: string) {
    try {
      await replay(runId);
      toasts.info('Replay started');
    } catch {
      toasts.error('Replay failed');
    }
  }

  function formatTime(ts: string): string {
    try {
      return new Date(ts).toLocaleString('en-GB', { hour12: false });
    } catch { return ts; }
  }
</script>

<div class="page">
  <h2>Runs</h2>

  <div class="filters">
    <select bind:value={filterOutcome} on:change={fetchRuns}>
      <option value="">All outcomes</option>
      <option value="glitch">Glitch</option>
      <option value="hang">Hang</option>
      <option value="crash">Crash</option>
      <option value="nothing">Nothing</option>
    </select>
    <input type="text" bind:value={filterCampaign} placeholder="Campaign ID" />
    <button on:click={fetchRuns}>Filter</button>
    {#if loading}<span class="loading">Loading…</span>{/if}
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Time</th>
          <th>Outcome</th>
          <th>X</th>
          <th>Y</th>
          <th>Z</th>
          <th>Delay (us)</th>
          <th>Width (ns)</th>
          <th>Voltage</th>
          <th>ms</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each runs as r}
          <tr
            class={r.outcome}
            class:selected={selectedRun?.id === r.id}
            on:click={() => (selectedRun = r)}
          >
            <td>{formatTime(r.ts)}</td>
            <td class="outcome">{r.outcome}</td>
            <td>{r.x?.toFixed(2) ?? '—'}</td>
            <td>{r.y?.toFixed(2) ?? '—'}</td>
            <td>{r.z?.toFixed(2) ?? '—'}</td>
            <td>{r.glitch_delay_us ?? '—'}</td>
            <td>{r.pulse_width_ns ?? '—'}</td>
            <td>{r.shouter_voltage ?? '—'}</td>
            <td>{r.elapsed_ms ?? '—'}</td>
            <td><button class="replay-btn" on:click|stopPropagation={() => doReplay(r.id)}>Replay</button></td>
          </tr>
        {/each}
        {#if runs.length === 0 && !loading}
          <tr><td colspan="10" class="empty">No runs found</td></tr>
        {/if}
      </tbody>
    </table>
  </div>

  {#if selectedRun}
    <div class="panel detail">
      <h3>Details</h3>
      <pre>{JSON.stringify(selectedRun, null, 2)}</pre>
    </div>
  {/if}
</div>

<style>
  .page { padding: 1rem 1.5rem; height: 100%; display: flex; flex-direction: column; }
  h2 { margin-bottom: 0.75rem; }
  .filters { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem; }
  .filters select, .filters input { font-size: 12px; }
  .loading { color: var(--muted); font-size: 11px; }
  .table-wrap { flex: 1; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius); }
  table { width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: 11px; }
  thead { position: sticky; top: 0; background: var(--panel-2); z-index: 1; }
  th {
    text-align: left;
    padding: 0.35rem 0.5rem;
    font-size: 10px;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
  }
  td { padding: 0.25rem 0.5rem; border-bottom: 1px solid var(--border); white-space: nowrap; }
  tr { cursor: pointer; transition: background 0.1s; }
  tr:hover { background: var(--panel-2); }
  tr.selected { background: var(--panel-2); outline: 1px solid var(--accent); }
  tr.glitch .outcome { color: var(--ok); }
  tr.hang .outcome { color: var(--err); }
  tr.crash .outcome { color: var(--warn); }
  tr.nothing .outcome { color: var(--muted); }
  .empty { text-align: center; color: var(--muted); padding: 2rem; }
  .replay-btn {
    font-size: 10px;
    padding: 0.15rem 0.5rem;
    border-color: var(--accent);
    color: var(--accent);
  }
  .detail { margin-top: 0.75rem; max-height: 200px; overflow: auto; }
  .detail pre { font-size: 11px; color: var(--muted); white-space: pre-wrap; }
</style>
