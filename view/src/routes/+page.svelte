<script lang="ts">
  import Scene3D from '$lib/components/Scene3D.svelte';
  import JogPad from '$lib/components/JogPad.svelte';
  import CounterPanel from '$lib/components/CounterPanel.svelte';
  import LogTail from '$lib/components/LogTail.svelte';
  import ProgressBar from '$lib/components/ProgressBar.svelte';
  import ScaffoldPowerCard from '$lib/components/ScaffoldPowerCard.svelte';
  import { positionStore } from '$lib/stores/position';
  import { activeCampaign } from '$lib/stores/campaign';
  import type { AttemptEntry } from '$lib/stores/log';

  let scene3d: Scene3D;

  function onLogSelect(ev: CustomEvent<AttemptEntry>) {
    const e = ev.detail;
    scene3d?.highlightPoint(e.x, e.y, e.z);
  }
</script>

<div class="mission">
  <aside class="left">
    <div class="panel">
      <h3>Position</h3>
      <div class="pos-readout">
        <span>X <b>{$positionStore.x.toFixed(2)}</b></span>
        <span>Y <b>{$positionStore.y.toFixed(2)}</b></span>
        <span>Z <b>{$positionStore.z.toFixed(2)}</b></span>
      </div>
    </div>

    <div class="panel">
      <h3>Manual Control</h3>
      <JogPad />
    </div>

    <div class="panel">
      <h3>Scaffold Power</h3>
      <ScaffoldPowerCard />
    </div>

    {#if $activeCampaign}
      <div class="panel">
        <h3>Campaign Progress</h3>
        <ProgressBar
          value={$activeCampaign.completed_attempts}
          max={$activeCampaign.total_attempts}
        />
        {#if $activeCampaign.last_outcome}
          <p class="last-outcome">Last: <span class={$activeCampaign.last_outcome}>{$activeCampaign.last_outcome}</span></p>
        {/if}
      </div>
    {/if}
  </aside>

  <section class="center">
    <Scene3D bind:this={scene3d} bedSize={100} />
  </section>

  <aside class="right">
    <div class="panel">
      <h3>Counters</h3>
      <CounterPanel />
    </div>

    <div class="panel log-panel">
      <h3>Logbook</h3>
      <LogTail limit={200} on:select={onLogSelect} />
    </div>
  </aside>
</div>

<style>
  .mission {
    display: grid;
    grid-template-columns: 280px 1fr 320px;
    gap: 0;
    height: 100%;
    overflow: hidden;
  }

  .left, .right {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.5rem;
    overflow-y: auto;
    border-right: 1px solid var(--border);
  }
  .right { border-right: none; border-left: 1px solid var(--border); }

  .center {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .pos-readout {
    display: flex;
    gap: 1rem;
    font-family: var(--mono);
    font-size: 14px;
  }
  .pos-readout b { color: var(--accent); }

  .log-panel { flex: 1; min-height: 0; display: flex; flex-direction: column; }

  .last-outcome { font-size: 11px; color: var(--muted); margin-top: 0.3rem; }
  .last-outcome .glitch { color: var(--ok); }
  .last-outcome .hang { color: var(--err); }
  .last-outcome .crash { color: var(--warn); }
  .last-outcome .nothing { color: var(--muted); }
</style>
