<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import SweepConfig from '$lib/components/SweepConfig.svelte';
  import GridConfig from '$lib/components/GridConfig.svelte';
  import { listProjects } from '$lib/api/develop';
  import { startCampaign, ApiError } from '$lib/api/control';
  import { toasts } from '$lib/stores/toast';
  import { onMount } from 'svelte';

  let projects: any[] = [];
  let selectedProject = '';
  let selectedVersion = '';
  let campaignName = '';
  let loading = false;
  let showAdvanced = false;
  let showPreview = false;

  let triggerMode = 'software';
  let shouterVoltage = 250;
  let shouterPulseWidth = 80;
  let verdictTimeout = 500;
  let shouterMute = true;
  let shouterAutoArm = true;

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
    // Pre-populate grid from calibration wizard query params, if present.
    const qp = $page.url.searchParams;
    const ox = qp.get('origin_x');
    const oy = qp.get('origin_y');
    const tx = qp.get('top_right_x');
    const ty = qp.get('top_right_y');
    if (ox != null && oy != null && tx != null && ty != null) {
      grid = {
        ...grid,
        origin: [parseFloat(ox), parseFloat(oy)],
        top_right: [parseFloat(tx), parseFloat(ty)],
      };
      toasts.info('Grid pre-populated from calibration');
    }

    try {
      const result = await listProjects();
      projects = Array.isArray(result) ? result : result?.projects ?? [];
    } catch {
      toasts.warn('Could not load projects from Develop');
    }
  });

  $: versions = projects.find((p: any) => p.id === selectedProject)?.versions ?? [];

  // ── Pre-flight estimate (read-only, computed before submit) ──
  let gridAck = false;

  function spanSteps(a: number, b: number, step: number): number {
    const span = b - a;
    if (!Number.isFinite(span) || !Number.isFinite(step) || step <= 0) return 1;
    return Math.max(1, Math.round(span / step) + 1);
  }

  function rangeLen(r: { start: number; stop: number; step: number } | null): number {
    if (!r || !Number.isFinite(r.step) || r.step <= 0) return 1;
    return Math.max(1, Math.floor((r.stop - r.start) / r.step) + 1);
  }

  $: xSteps = spanSteps(grid.origin[0], grid.top_right[0], grid.step_size_mm);
  $: ySteps = spanSteps(grid.origin[1], grid.top_right[1], grid.step_size_mm);
  $: zSteps = spanSteps(grid.z_min_mm, grid.z_max_mm, grid.z_step_mm);
  $: gridPts = xSteps * ySteps * zSteps;
  $: sweepCount =
    rangeLen(sweep.delay_us) * rangeLen(sweep.pulse_width_ns) * rangeLen(sweep.voltage_v);
  $: attempts = Math.max(1, sweep.attempts_per_point || 1);
  $: totalAttempts = gridPts * sweepCount * attempts;
  $: estSeconds = Math.round(totalAttempts / 2);

  // Re-prompt for tiny grids: clear the acknowledgement once the grid grows back to ≥4 pts,
  // so a later edit that shrinks it again surfaces the warning afresh.
  $: if (gridPts >= 4) gridAck = false;
  $: smallGridBlocked = gridPts < 4 && !gridAck;

  $: formComplete = campaignName.trim() !== '' && selectedProject !== '';
  $: canSubmit = formComplete && !smallGridBlocked;

  function buildBody(): Record<string, unknown> {
    const body: Record<string, unknown> = {
      name: campaignName.trim(),
      project_id: selectedProject,
      grid: {
        origin: grid.origin,
        top_right: grid.top_right,
        step_size_mm: grid.step_size_mm,
        z_min_mm: grid.z_min_mm,
        z_max_mm: grid.z_max_mm,
        z_step_mm: grid.z_step_mm,
      },
      sweep: {
        delay_us: sweep.delay_us,
        pulse_width_ns: sweep.pulse_width_ns,
        voltage_v: sweep.voltage_v,
        attempts_per_point: sweep.attempts_per_point,
      },
      trigger_mode: triggerMode,
      shouter_voltage: shouterVoltage,
      shouter_pulse_width_ns: shouterPulseWidth,
      verdict_timeout_ms: verdictTimeout,
      shouter_mute: shouterMute,
      shouter_auto_arm: shouterAutoArm,
    };
    if (selectedVersion) body.project_version = selectedVersion;
    return body;
  }

  $: previewJson = canSubmit ? JSON.stringify(buildBody(), null, 2) : '{}';

  async function submit() {
    if (!canSubmit) return;
    loading = true;
    try {
      const result = await startCampaign(buildBody());
      toasts.info('Campaign started');
      if (result?.id) goto(`/campaign/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.body?.detail) {
        if (Array.isArray(err.body.detail)) {
          for (const e of err.body.detail) {
            const loc = Array.isArray(e.loc)
              ? e.loc.filter((s: unknown) => s !== 'body').join('.')
              : '?';
            toasts.error(`${loc}: ${e.msg}`, { where: 'validation' });
          }
        } else {
          toasts.error(String(err.body.detail));
        }
      } else {
        toasts.error('Failed to start campaign');
      }
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
          <label for="camp-name">Name</label>
          <input id="camp-name" type="text" bind:value={campaignName} placeholder="my-scan-01" />
        </div>
        <div class="field">
          <label for="camp-project">Project</label>
          <select id="camp-project" bind:value={selectedProject}>
            <option value="">Select a project</option>
            {#each projects as p}
              <option value={p.id}>{p.name} ({p.language})</option>
            {/each}
          </select>
        </div>
        {#if versions.length > 0}
          <div class="field">
            <label for="camp-version">Version</label>
            <select id="camp-version" bind:value={selectedVersion}>
              <option value="">latest (HEAD)</option>
              {#each versions as v}
                <option value={v}>{v}</option>
              {/each}
            </select>
          </div>
        {/if}
      </div>

      <GridConfig bind:value={grid} />

      <div class="panel preflight" class:warn={smallGridBlocked}>
        <h3>Pre-flight</h3>
        <div class="preflight-lines">
          <div>Grid: {xSteps} × {ySteps} × {zSteps} = <b>{gridPts}</b></div>
          <div>Sweep: {sweepCount} combos × {attempts} attempts</div>
          <div>Total: <b>{totalAttempts}</b> attempts (~{estSeconds}s)</div>
        </div>
        {#if smallGridBlocked}
          <div class="preflight-warn">
            <p>Grid will only produce {gridPts} point{gridPts === 1 ? '' : 's'}. Did you mean this?</p>
            <div class="preflight-actions">
              <button type="button" class="ack" on:click={() => (gridAck = true)}>I meant it</button>
              <button type="button" on:click={() => goto('/calibrate')}>Recalibrate</button>
            </div>
          </div>
        {/if}
      </div>

      <SweepConfig bind:value={sweep} />
    </div>

    <div class="col">
      <details class="panel" bind:open={showAdvanced}>
        <summary><h3>Advanced</h3></summary>
        <div class="field">
          <label for="camp-trigger">Trigger mode</label>
          <select id="camp-trigger" bind:value={triggerMode}>
            <option value="software">Software</option>
            <option value="one-shot">One-shot</option>
            <option value="free-run">Free-run</option>
            <option value="disabled">Disabled</option>
          </select>
        </div>
        <div class="field">
          <label for="camp-voltage">Voltage (V)</label>
          <input id="camp-voltage" type="number" bind:value={shouterVoltage} min="0" max="500" />
        </div>
        <div class="field">
          <label for="camp-pulse">Pulse width (ns)</label>
          <input id="camp-pulse" type="number" bind:value={shouterPulseWidth} min="1" />
        </div>
        <div class="field">
          <label for="camp-timeout">Verdict timeout (ms)</label>
          <input id="camp-timeout" type="number" bind:value={verdictTimeout} min="10" />
        </div>
        <div class="field row">
          <label><input type="checkbox" bind:checked={shouterMute} /> Mute buzzer</label>
          <label><input type="checkbox" bind:checked={shouterAutoArm} /> Auto-arm</label>
        </div>
      </details>

      <details class="panel" bind:open={showPreview}>
        <summary><h3>Request preview</h3></summary>
        <pre class="preview">{previewJson}</pre>
      </details>

      <button class="start-btn" on:click={submit} disabled={!canSubmit || loading}>
        {loading ? 'Starting…' : 'Start Campaign'}
      </button>
      {#if !formComplete}
        <p class="hint">Fill in name and select a project to enable submit.</p>
      {:else if smallGridBlocked}
        <p class="hint">Resolve the small-grid warning above to enable submit.</p>
      {/if}
    </div>
  </div>
</div>

<style>
  .page { padding: 1rem 1.5rem; max-width: 960px; }
  h2 { margin-bottom: 1rem; }
  .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; align-items: start; }
  .col { display: flex; flex-direction: column; gap: 0.75rem; }
  .field { display: flex; flex-direction: column; gap: 0.2rem; margin-bottom: 0.4rem; }
  .field input[type="text"], .field input[type="number"], .field select { width: 100%; }
  .field.row { flex-direction: row; gap: 1rem; }

  details.panel { cursor: default; }
  details.panel summary {
    cursor: pointer;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  details.panel summary::before {
    content: '▶';
    font-size: 9px;
    color: var(--muted);
    transition: transform 0.15s;
  }
  details[open].panel summary::before { transform: rotate(90deg); }
  details.panel summary h3 { margin: 0; }
  details.panel > :not(summary) { margin-top: 0.5rem; }

  .preview {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    background: var(--panel-2);
    border-radius: var(--radius);
    padding: 0.5rem;
    max-height: 300px;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }

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
  .start-btn:hover:not(:disabled) { filter: brightness(1.1); }
  .start-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .hint { color: var(--muted); font-size: 11px; margin-top: 0.25rem; }

  .preflight.warn { border: 1px solid var(--warn); }
  .preflight-lines {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--fg);
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .preflight-lines b { color: var(--accent); }
  .preflight-warn {
    margin-top: 0.6rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--border);
  }
  .preflight-warn p { color: var(--warn); font-size: 12px; margin: 0 0 0.4rem; }
  .preflight-actions { display: flex; gap: 0.5rem; }
  .preflight-actions .ack {
    background: var(--warn);
    color: var(--bg);
    border-color: var(--warn);
    font-weight: 600;
  }
</style>
