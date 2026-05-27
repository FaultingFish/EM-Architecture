<script lang="ts">
  import { goto } from '$app/navigation';
  import SweepConfig from '$lib/components/SweepConfig.svelte';
  import GridConfig from '$lib/components/GridConfig.svelte';
  import { listProjects } from '$lib/api/develop';
  import { startCampaign } from '$lib/api/control';
  import { toasts } from '$lib/stores/toast';
  import { onMount } from 'svelte';

  let projects: any[] = [];
  let selectedProject = '';
  let selectedVersion = '';
  let campaignName = '';
  let triggerMode = 'software';
  let shouterVoltage = 250;
  let shouterPulseWidth = 80;
  let verdictTimeout = 500;
  let shouterMute = true;
  let shouterAutoArm = true;
  let loading = false;

  let sweep = {
    delay_us: null as { start: number; stop: number; step: number } | null,
    pulse_width_ns: null as { start: number; stop: number; step: number } | null,
    voltage_v: null as { start: number; stop: number; step: number } | null,
    attempts_per_point: 1
  };

  let grid = {
    origin: [0, 0] as [number, number],
    top_right: [10, 10] as [number, number],
    step_size_mm: 1.0,
    z_min_mm: 0.0,
    z_max_mm: 0.5,
    z_step_mm: 0.1
  };

  onMount(async () => {
    try {
      projects = await listProjects();
    } catch {
      toasts.warn('Could not load projects from Develop');
    }
  });

  $: versions = projects.find((p: any) => p.id === selectedProject)?.versions ?? [];

  async function submit() {
    if (!campaignName) { toasts.warn('Enter a campaign name'); return; }
    loading = true;
    try {
      const body = {
        name: campaignName,
        project_id: selectedProject || undefined,
        project_version: selectedVersion || undefined,
        grid,
        sweep,
        trigger_mode: triggerMode,
        shouter_voltage: shouterVoltage,
        shouter_pulse_width_ns: shouterPulseWidth,
        verdict_timeout_ms: verdictTimeout,
        shouter_mute: shouterMute,
        shouter_auto_arm: shouterAutoArm,
      };
      const result = await startCampaign(body);
      toasts.info('Campaign started');
      if (result?.id) goto(`/campaign/${result.id}`);
    } catch {
      toasts.error('Failed to start campaign');
    } finally {
      loading = false;
    }
  }
</script>

<div class="page">
  <h2>New Campaign</h2>

  <div class="form-grid">
    <div class="col">
      <div class="panel">
        <h3>Campaign</h3>
        <div class="field">
          <label>Name</label>
          <input type="text" bind:value={campaignName} placeholder="my-scan-01" />
        </div>
        <div class="field">
          <label>Project</label>
          <select bind:value={selectedProject}>
            <option value="">— none —</option>
            {#each projects as p}
              <option value={p.id}>{p.name} ({p.language})</option>
            {/each}
          </select>
        </div>
        {#if versions.length > 0}
          <div class="field">
            <label>Version</label>
            <select bind:value={selectedVersion}>
              <option value="">latest</option>
              {#each versions as v}
                <option value={v}>{v}</option>
              {/each}
            </select>
          </div>
        {/if}
      </div>

      <div class="panel">
        <h3>Shouter</h3>
        <div class="field">
          <label>Trigger mode</label>
          <select bind:value={triggerMode}>
            <option value="software">Software</option>
            <option value="one-shot">One-shot</option>
            <option value="free-run">Free-run</option>
            <option value="disabled">Disabled</option>
          </select>
        </div>
        <div class="field">
          <label>Voltage (V)</label>
          <input type="number" bind:value={shouterVoltage} min="0" max="500" />
        </div>
        <div class="field">
          <label>Pulse width (ns)</label>
          <input type="number" bind:value={shouterPulseWidth} min="1" />
        </div>
        <div class="field">
          <label>Verdict timeout (ms)</label>
          <input type="number" bind:value={verdictTimeout} min="10" />
        </div>
        <div class="field row">
          <label><input type="checkbox" bind:checked={shouterMute} /> Mute buzzer</label>
          <label><input type="checkbox" bind:checked={shouterAutoArm} /> Auto-arm</label>
        </div>
      </div>
    </div>

    <div class="col">
      <GridConfig bind:value={grid} />
      <SweepConfig bind:value={sweep} />

      <button class="start-btn" on:click={submit} disabled={loading}>
        {loading ? 'Starting…' : 'Start Campaign'}
      </button>
    </div>
  </div>
</div>

<style>
  .page { padding: 1rem 1.5rem; max-width: 900px; }
  h2 { margin-bottom: 1rem; }
  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  .col { display: flex; flex-direction: column; gap: 0.75rem; }
  .field { display: flex; flex-direction: column; gap: 0.2rem; margin-bottom: 0.4rem; }
  .field input[type="text"], .field select { width: 100%; }
  .field.row { flex-direction: row; gap: 1rem; }
  .start-btn {
    padding: 0.6rem 1.5rem;
    background: var(--accent);
    color: var(--bg);
    border: none;
    font-weight: 700;
    font-size: 14px;
    border-radius: var(--radius);
    cursor: pointer;
    margin-top: 0.5rem;
  }
  .start-btn:hover { filter: brightness(1.1); }
  .start-btn:disabled { opacity: 0.5; }
</style>
