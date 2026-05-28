<script lang="ts">
  import { goto } from '$app/navigation';
  import { positionStore } from '$lib/stores/position';
  import { armStore } from '$lib/stores/arm';
  import { moveAbs, setOrigin, setTopRight } from '$lib/api/control';
  import { toasts } from '$lib/stores/toast';
  import JogPad from '$lib/components/JogPad.svelte';
  import Scene3D from '$lib/components/Scene3D.svelte';

  type Step = 1 | 2 | 3;
  let step: Step = 1;

  let originX: number | null = null;
  let originY: number | null = null;
  let originZ: number | null = null;
  let topRightX: number | null = null;
  let topRightY: number | null = null;

  let busy = false;

  $: scanBox =
    step >= 2 && originX != null && originY != null
      ? {
          width: Math.max(Math.abs(($positionStore.x ?? 0) - originX), 0.1),
          height: Math.max(Math.abs(($positionStore.y ?? 0) - originY), 0.1),
          depth: 0.5,
        }
      : step === 3 && originX != null && originY != null && topRightX != null && topRightY != null
      ? {
          width: Math.max(Math.abs(topRightX - originX), 0.1),
          height: Math.max(Math.abs(topRightY - originY), 0.1),
          depth: 0.5,
        }
      : null;

  $: width = originX != null && topRightX != null ? Math.abs(topRightX - originX) : null;
  $: height = originY != null && topRightY != null ? Math.abs(topRightY - originY) : null;

  function gotoStep(s: Step) {
    // Allow stepping back; only forward through buttons (which gate on data presence).
    if (s <= step) step = s;
  }

  async function setOriginAndAdvance() {
    busy = true;
    try {
      await setOrigin();
      originX = $positionStore.x ?? 0;
      originY = $positionStore.y ?? 0;
      originZ = $positionStore.z ?? 0;
      toasts.info(`Origin set at (${originX.toFixed(2)}, ${originY.toFixed(2)})`);
      step = 2;
    } catch {
      toasts.error('set_origin failed');
    } finally {
      busy = false;
    }
  }

  async function setTopRightAndAdvance() {
    busy = true;
    try {
      const x = $positionStore.x ?? 0;
      const y = $positionStore.y ?? 0;
      await setTopRight(x, y);
      topRightX = x;
      topRightY = y;
      toasts.info(`Top-right set at (${x.toFixed(2)}, ${y.toFixed(2)})`);
      step = 3;
    } catch {
      toasts.error('set_top_right failed');
    } finally {
      busy = false;
    }
  }

  async function jogToOrigin() {
    if (originX == null || originY == null) return;
    try {
      await moveAbs(originX, originY, originZ ?? $positionStore.z ?? 0);
      toasts.info('Jogging to origin…');
    } catch {
      toasts.error('Jog to origin failed');
    }
  }

  function finish() {
    if (originX == null || originY == null || topRightX == null || topRightY == null) return;
    const qs = new URLSearchParams({
      origin_x: String(originX),
      origin_y: String(originY),
      top_right_x: String(topRightX),
      top_right_y: String(topRightY),
    });
    goto(`/campaign?${qs.toString()}`);
  }
</script>

<div class="page">
  <h2>Calibration</h2>

  {#if $armStore.armed}
    <div class="arm-warning">
      ⚠ ARM is engaged. Calibration normally runs disarmed — disengage ARM unless you know why you need it hot.
    </div>
  {/if}

  <div class="tabs">
    <button class="tab" class:active={step === 1} on:click={() => gotoStep(1)}>
      1. Origin {#if originX != null}<span class="check">✓</span>{/if}
    </button>
    <button class="tab" class:active={step === 2} on:click={() => gotoStep(2)} disabled={originX == null}>
      2. Top-right {#if topRightX != null}<span class="check">✓</span>{/if}
    </button>
    <button class="tab" class:active={step === 3} on:click={() => gotoStep(3)} disabled={topRightX == null}>
      3. Confirm
    </button>
  </div>

  <div class="layout">
    <div class="instructions">
      {#if step === 1}
        <h3>Set origin</h3>
        <p>
          Use the jog pad to position the ChipSHOUTER tip over the
          <strong>bottom-left corner</strong> of the area you want to scan.
        </p>
        <p class="hint">Tip: jog Z up first to avoid crashing into the bed.</p>

        <div class="panel">
          <h4>Current position</h4>
          <div class="pos-readout">
            <span>X <b>{$positionStore.x?.toFixed(2) ?? '—'}</b></span>
            <span>Y <b>{$positionStore.y?.toFixed(2) ?? '—'}</b></span>
            <span>Z <b>{$positionStore.z?.toFixed(2) ?? '—'}</b></span>
          </div>
        </div>

        <div class="panel">
          <h4>Jog</h4>
          <JogPad />
        </div>

        <button class="primary" on:click={setOriginAndAdvance} disabled={busy}>
          {busy ? 'Setting…' : 'Set as origin'}
        </button>
      {:else if step === 2}
        <h3>Set top-right</h3>
        <p>
          Now jog to the <strong>top-right corner</strong> of the scan area.
          The grid below shows the area you're outlining.
        </p>

        <div class="panel">
          <h4>Current position</h4>
          <div class="pos-readout">
            <span>X <b>{$positionStore.x?.toFixed(2) ?? '—'}</b></span>
            <span>Y <b>{$positionStore.y?.toFixed(2) ?? '—'}</b></span>
            <span>Z <b>{$positionStore.z?.toFixed(2) ?? '—'}</b></span>
          </div>
          <div class="pos-readout sub">
            <span>Origin: ({originX?.toFixed(2)}, {originY?.toFixed(2)})</span>
          </div>
        </div>

        <div class="panel">
          <h4>Jog</h4>
          <JogPad />
        </div>

        <button class="primary" on:click={setTopRightAndAdvance} disabled={busy}>
          {busy ? 'Setting…' : 'Set as top-right'}
        </button>
      {:else}
        <h3>Confirm</h3>
        <p>Calibration complete. Review the values below, optionally test the origin, then continue to campaign config.</p>

        <div class="panel">
          <h4>Summary</h4>
          <table class="summary">
            <tr><th>Origin</th><td>({originX?.toFixed(2)}, {originY?.toFixed(2)})</td></tr>
            <tr><th>Top-right</th><td>({topRightX?.toFixed(2)}, {topRightY?.toFixed(2)})</td></tr>
            <tr>
              <th>Grid size</th>
              <td>
                {width?.toFixed(2)} mm × {height?.toFixed(2)} mm
                {#if width != null && height != null}
                  <span class="area">= {(width * height).toFixed(2)} mm²</span>
                {/if}
              </td>
            </tr>
          </table>
        </div>

        <div class="actions">
          <button on:click={jogToOrigin}>Jog to origin (test)</button>
          <button class="primary" on:click={finish}>Done → Campaign</button>
        </div>
      {/if}
    </div>

    <div class="scene-wrap">
      <Scene3D {scanBox} />
    </div>
  </div>
</div>

<style>
  .page { padding: 1rem 1.5rem; height: 100%; display: flex; flex-direction: column; }
  h2 { margin-bottom: 0.5rem; }
  h3 { margin: 0 0 0.5rem; color: var(--accent); }
  h4 {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    margin-bottom: 0.4rem;
    font-weight: 500;
  }

  .arm-warning {
    background: rgba(249, 168, 37, 0.12);
    border: 1px solid var(--warn);
    color: var(--warn);
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius);
    margin-bottom: 0.5rem;
    font-size: 12px;
  }

  .tabs {
    display: flex;
    gap: 0.25rem;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid var(--border);
  }
  .tab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 0.5rem 1rem;
    color: var(--muted);
    font-size: 12px;
  }
  .tab:hover:not(:disabled) { color: var(--fg); background: var(--panel-2); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab .check { color: var(--ok); margin-left: 0.3rem; }

  .layout {
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 1rem;
    flex: 1;
    min-height: 0;
  }

  .instructions {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    overflow-y: auto;
  }
  .instructions p { color: var(--fg); font-size: 13px; line-height: 1.5; }
  .instructions p.hint { color: var(--muted); font-size: 11px; font-style: italic; }
  .instructions strong { color: var(--accent); }

  .pos-readout {
    display: flex;
    gap: 1rem;
    font-family: var(--mono);
    font-size: 14px;
  }
  .pos-readout b { color: var(--accent); }
  .pos-readout.sub {
    font-size: 11px;
    color: var(--muted);
    margin-top: 0.3rem;
  }

  .scene-wrap {
    min-height: 400px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }

  .summary { font-family: var(--mono); font-size: 12px; width: 100%; }
  .summary th {
    text-align: left;
    color: var(--muted);
    font-weight: 400;
    padding: 0.25rem 0.75rem 0.25rem 0;
    font-size: 11px;
    text-transform: uppercase;
  }
  .summary td { padding: 0.25rem 0; color: var(--fg); }
  .summary .area { color: var(--muted); font-size: 11px; margin-left: 0.4rem; }

  .actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }

  button.primary {
    background: var(--accent);
    color: var(--bg);
    border-color: var(--accent);
    font-weight: 700;
    padding: 0.5rem 1rem;
  }
  button.primary:hover:not(:disabled) { filter: brightness(1.1); }
  button.primary:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
