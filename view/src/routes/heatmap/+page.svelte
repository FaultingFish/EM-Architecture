<script lang="ts">
  import { onMount } from 'svelte';
  import Heatmap from '$lib/components/Heatmap.svelte';
  import { heatmap as fetchHeatmap } from '$lib/api/control';
  import { toasts } from '$lib/stores/toast';

  // New /heatmap shape: per-cell per-outcome counts (Control [fyi] 2026-05-28).
  type HeatCell = {
    x: number;
    y: number;
    counts: { glitch: number; hang: number; crash: number; nothing: number };
  };

  let cells: HeatCell[] = [];
  let zValue = 0;
  let campaignFilter = '';
  let loading = false;

  onMount(() => { load(); });

  async function load() {
    loading = true;
    try {
      const result = await fetchHeatmap(zValue, campaignFilter || undefined);
      cells = Array.isArray(result) ? result : result?.cells ?? [];
    } catch {
      toasts.warn('Could not load heatmap — is Control running?');
      cells = [];
    } finally {
      loading = false;
    }
  }
</script>

<div class="page">
  <h2>Heatmap</h2>

  <div class="controls">
    <label>
      Z plane (mm)
      <input type="number" bind:value={zValue} step="0.01" on:change={load} />
    </label>
    <label>
      Campaign
      <input type="text" bind:value={campaignFilter} placeholder="all" />
    </label>
    <button on:click={load} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
  </div>

  <Heatmap {cells} width={800} height={500} />

  <p class="summary">{cells.length} cells at Z={zValue}</p>
</div>

<style>
  .page { padding: 1rem 1.5rem; }
  h2 { margin-bottom: 0.75rem; }
  .controls { display: flex; gap: 1rem; align-items: flex-end; margin-bottom: 1rem; }
  .controls label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 11px; }
  .controls input { width: 6rem; }
  .summary { color: var(--muted); font-size: 11px; margin-top: 0.5rem; }
</style>
