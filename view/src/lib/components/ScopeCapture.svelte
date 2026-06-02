<script lang="ts">
  import { logStore } from '$lib/stores/log';
  import { activeCampaign } from '$lib/stores/campaign';

  const windowNs = 500;
  const triggerNs = 120;
  const lanes = [
    { ch: 'CH3', name: 'PULSE', unit: '200 V/div', color: 'var(--red)' },
    { ch: 'CH2', name: 'TRIG', unit: '3.3 V/div', color: 'var(--scope-cyan)' },
    { ch: 'CH1', name: 'CLK', unit: '1.8 V/div', color: 'var(--gold)' },
  ];

  type Instruction = {
    id: string;
    name: string;
    mnemonic: string;
    color: string;
    t0: number;
    t1: number;
  };

  let showConfig = false;
  let targetId = 'target';
  let instructions: Instruction[] = [
    { id: 'trigger', name: 'TRIG', mnemonic: 'str r0,[r1]', color: 'var(--scope-cyan)', t0: 96, t1: 150 },
    { id: 'target', name: 'TARGET', mnemonic: 'cmp r2,#0', color: 'var(--gold)', t0: 250, t1: 320 },
    { id: 'success', name: 'SUCCESS', mnemonic: 'bne .pass', color: 'var(--scope-green)', t0: 336, t1: 392 },
  ];

  function readDelayNs(row: Record<string, unknown> | undefined) {
    if (!row) return 180;
    const raw = Number(row.glitch_delay_us ?? row.delay_us ?? row.delay_ns ?? 180);
    if (!Number.isFinite(raw)) return 180;
    if (raw > 500) return Math.min(360, Math.max(60, raw / 10));
    return Math.min(360, Math.max(60, raw));
  }

  function x(t: number) {
    return (t / windowNs) * 100;
  }

  function pulsePoints(glitchNs: number) {
    const p = [
      [0, 20],
      [x(glitchNs - 26), 20],
      [x(glitchNs - 6), 20],
      [x(glitchNs - 2), 3],
      [x(glitchNs + 2), 37],
      [x(glitchNs + 7), 10],
      [x(glitchNs + 12), 28],
      [x(glitchNs + 18), 16],
      [x(glitchNs + 26), 20],
      [100, 20],
    ];
    return p.map(([px, py]) => `${px},${py}`).join(' ');
  }

  function triggerPoints() {
    return `0,80 ${x(triggerNs)},80 ${x(triggerNs)},64 100,64`;
  }

  function clockPoints() {
    const points: string[] = [];
    let high = false;
    for (let t = 0; t <= windowNs; t += 13) {
      points.push(`${x(t)},${high ? 132 : 152}`);
      high = !high;
      points.push(`${x(t)},${high ? 132 : 152}`);
    }
    points.push('100,152');
    return points.join(' ');
  }

  function colorValue(color: string) {
    if (color.includes('cyan')) return '#2ed3c6';
    if (color.includes('green')) return '#2bd576';
    if (color.includes('gold')) return '#d4a017';
    if (color.includes('red')) return '#e5293a';
    return color;
  }

  function updateInstruction(id: string, field: keyof Instruction, value: string) {
    instructions = instructions.map((item) => item.id === id ? { ...item, [field]: value } : item);
  }

  $: latest = $logStore[$logStore.length - 1] as Record<string, unknown> | undefined;
  $: delayNs = readDelayNs(latest);
  $: glitchNs = triggerNs + delayNs;
  $: running = Boolean($activeCampaign?.active);
  $: outcome = String(latest?.outcome ?? $activeCampaign?.last_outcome ?? 'idle');
</script>

<section class="scope-shell">
  <div class="scope-head">
    <div class="title">
      <span class="section-label">// capture</span>
      <h2>Instruction timing window</h2>
    </div>
    <div class="scope-meta">
      <span>50 ns/div</span>
      <span class="cyan">trig +{triggerNs} ns</span>
      <span class="red">delay {Math.round(delayNs)} ns</span>
      <span class:running>{running ? 'ACQUIRING' : 'STOPPED'}</span>
    </div>
  </div>

  <div class="scope-body">
    <svg viewBox="0 0 100 180" preserveAspectRatio="none" aria-label="Oscilloscope style timing capture">
      <defs>
        <linearGradient id="pulse-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#e5293a" stop-opacity="0.35" />
          <stop offset="100%" stop-color="#e5293a" stop-opacity="0" />
        </linearGradient>
      </defs>

      {#each Array.from({ length: 11 }) as _, i}
        <line class="grid" x1={i * 10} y1="8" x2={i * 10} y2="162" />
      {/each}
      {#each [8, 34, 60, 86, 112, 138, 162] as y}
        <line class="grid" x1="0" y1={y} x2="100" y2={y} />
      {/each}

      {#each lanes as lane, i}
        <text x="1.5" y={18 + i * 58} fill={lane.color}>{lane.ch}</text>
        <text x="1.5" y={28 + i * 58} class="lane-name">{lane.name}</text>
        <text x="1.5" y={38 + i * 58} class="lane-unit">{lane.unit}</text>
      {/each}

      {#each instructions as ins}
        <rect
          class="instr-band"
          class:target={ins.id === targetId}
          x={x(ins.t0)}
          y="8"
          width={Math.max(1, x(ins.t1) - x(ins.t0))}
          height="154"
          fill={ins.color}
        />
        <line
          class="instr-line"
          class:target={ins.id === targetId}
          x1={x(ins.t0)}
          y1="8"
          x2={x(ins.t0)}
          y2="162"
          stroke={ins.color}
        />
        <rect x={x(ins.t0)} y="10" width={Math.max(5, ins.name.length * 1.35)} height="7" rx="0.8" fill={ins.color} />
      {/each}

      <polygon points={`${pulsePoints(glitchNs)} 100,20 0,20`} fill="url(#pulse-fill)" />
      <polyline class="trace pulse" points={pulsePoints(glitchNs)} />
      <polyline class="trace trigger" points={triggerPoints()} />
      <polyline class="trace clock" points={clockPoints()} />

      <line class="trigger-marker" x1={x(triggerNs)} y1="8" x2={x(triggerNs)} y2="162" />
      <line class="glitch-marker" x1={x(glitchNs)} y1="8" x2={x(glitchNs)} y2="162" />

      <line class="delay-bracket" x1={x(triggerNs)} y1="170" x2={x(glitchNs)} y2="170" />
      <line class="delay-bracket" x1={x(triggerNs)} y1="167" x2={x(triggerNs)} y2="173" />
      <line class="delay-bracket" x1={x(glitchNs)} y1="167" x2={x(glitchNs)} y2="173" />
    </svg>

    {#if running}
      <div class="scope-scan"></div>
    {/if}

    <button class="legend-card" on:click={() => (showConfig = true)}>
      <span class="legend-title">TARGET INSTRUCTIONS</span>
      {#each instructions as ins}
        <span class="legend-row">
          <i style:background={ins.color}></i>
          <b>{ins.name}</b>
          <code>{ins.mnemonic}</code>
          {#if ins.id === targetId}<em>◎</em>{/if}
        </span>
      {/each}
      <small>click to configure</small>
    </button>
  </div>

  <div class="scope-foot">
    <span>outcome <b class={outcome}>{outcome}</b></span>
    <span>trigger source scaffold D0</span>
    <span>pulse source ChipSHOUTER</span>
    <span>window {windowNs} ns</span>
  </div>
</section>

{#if showConfig}
  <div class="modal-backdrop">
    <button class="backdrop-hit" aria-label="Close instruction configuration" on:click={() => (showConfig = false)}></button>
    <div class="modal" role="dialog" aria-modal="true" aria-label="Configure target instructions">
      <div class="modal-head">
        <div>
          <div class="section-label">// instruction windows</div>
          <h3>Configure target bars</h3>
        </div>
        <button on:click={() => (showConfig = false)} aria-label="Close instruction configuration">×</button>
      </div>
      <div class="modal-body">
        {#each instructions as ins}
          <div class="config-row">
            <input aria-label={`${ins.name} color`} type="color" value={colorValue(ins.color)} on:input={(e) => updateInstruction(ins.id, 'color', e.currentTarget.value)} />
            <input aria-label={`${ins.name} label`} value={ins.name} on:input={(e) => updateInstruction(ins.id, 'name', e.currentTarget.value)} />
            <input aria-label={`${ins.name} mnemonic`} value={ins.mnemonic} on:input={(e) => updateInstruction(ins.id, 'mnemonic', e.currentTarget.value)} />
            <button class:active={targetId === ins.id} on:click={() => (targetId = ins.id)}>Target</button>
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}

<style>
  .scope-shell {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--ink-0);
    border: 1px solid var(--line);
    border-radius: 6px;
  }

  .scope-head,
  .scope-foot {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.65rem 0.9rem;
    background: var(--ink-1);
    border-bottom: 1px solid var(--line);
  }

  .scope-foot {
    justify-content: space-between;
    border-top: 1px solid var(--line);
    border-bottom: 0;
    color: var(--fg-3);
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.04em;
  }

  .title {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  h2,
  h3 {
    margin: 0;
    font-size: 14px;
  }

  .scope-meta {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 0.85rem;
    color: var(--fg-3);
    font-family: var(--mono);
    font-size: 10.5px;
  }

  .scope-meta .cyan { color: var(--scope-cyan); }
  .scope-meta .red { color: var(--red-bright); }
  .scope-meta .running { color: var(--scope-green); }

  .scope-body {
    position: relative;
    flex: 1;
    min-height: 340px;
  }

  svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }

  text {
    font-family: var(--mono);
    font-size: 3.5px;
    font-weight: 700;
  }

  .lane-name,
  .lane-unit {
    fill: var(--fg-3);
    font-size: 2.8px;
    font-weight: 400;
  }

  .lane-unit {
    fill: var(--fg-4);
    font-size: 2.3px;
  }

  .grid {
    stroke: var(--line-faint);
    stroke-width: 0.22;
  }

  .instr-band {
    opacity: 0.08;
  }

  .instr-band.target {
    opacity: 0.16;
  }

  .instr-line {
    opacity: 0.6;
    stroke-width: 0.28;
  }

  .instr-line.target {
    opacity: 1;
    stroke-width: 0.48;
  }

  .trace {
    fill: none;
    stroke-width: 0.52;
    stroke-linejoin: round;
  }

  .pulse { stroke: var(--red); }
  .trigger { stroke: var(--scope-cyan); }
  .clock { stroke: var(--gold); }

  .trigger-marker {
    stroke: var(--scope-cyan);
    stroke-width: 0.25;
    stroke-dasharray: 0.8 1.2;
    opacity: 0.8;
  }

  .glitch-marker {
    stroke: var(--red-bright);
    stroke-width: 0.35;
  }

  .delay-bracket {
    stroke: var(--fg-3);
    stroke-width: 0.24;
  }

  .scope-scan {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 7%;
    width: 28%;
    background: linear-gradient(90deg, transparent, rgba(46, 211, 198, 0.1), transparent);
    pointer-events: none;
    animation: ff-scan 2.4s linear infinite;
  }

  .legend-card {
    position: absolute;
    top: 0.8rem;
    right: 0.8rem;
    min-width: 220px;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    text-align: left;
    background: rgba(16, 19, 23, 0.94);
    border-color: var(--line-strong);
    box-shadow: var(--shadow-2);
  }

  .legend-card:hover {
    border-color: var(--gold);
  }

  .legend-title,
  .legend-card small {
    color: var(--fg-3);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: 0.13em;
  }

  .legend-card small {
    margin-top: 0.25rem;
    padding-top: 0.45rem;
    border-top: 1px solid var(--line-faint);
    color: var(--fg-4);
  }

  .legend-row {
    display: grid;
    grid-template-columns: 10px 56px 1fr auto;
    align-items: center;
    gap: 0.5rem;
  }

  .legend-row i {
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }

  .legend-row b,
  .legend-row code,
  .legend-row em {
    font-family: var(--mono);
    font-size: 10.5px;
  }

  .legend-row code {
    color: var(--fg-1);
  }

  .legend-row em {
    color: var(--gold);
    font-style: normal;
  }

  .glitch,
  .success { color: var(--scope-green); }
  .crash { color: var(--red-bright); }
  .hang { color: var(--gold); }
  .nothing,
  .idle { color: var(--fg-3); }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 80;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(6, 7, 8, 0.76);
    backdrop-filter: blur(4px);
  }

  .backdrop-hit {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    padding: 0;
    background: transparent;
    border: 0;
    border-radius: 0;
  }

  .modal {
    position: relative;
    width: min(720px, calc(100vw - 2rem));
    background: var(--ink-2);
    border: 1px solid var(--line-strong);
    border-radius: 8px;
    box-shadow: var(--shadow-2);
  }

  .modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem;
    border-bottom: 1px solid var(--line);
  }

  .modal-head button {
    width: 32px;
    height: 32px;
    padding: 0;
    font-size: 20px;
  }

  .modal-body {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    padding: 1rem;
  }

  .config-row {
    display: grid;
    grid-template-columns: 44px 120px 1fr 90px;
    gap: 0.5rem;
    align-items: center;
  }

  .config-row input[type='color'] {
    width: 44px;
    height: 32px;
    padding: 0.15rem;
  }

  .config-row input:not([type='color']) {
    width: 100%;
  }

  .config-row button.active {
    color: var(--gold);
    border-color: var(--gold);
    background: var(--gold-12);
  }

  @media (max-width: 980px) {
    .scope-meta {
      display: none;
    }

    .scope-body {
      min-height: 360px;
    }

    .legend-card {
      min-width: 190px;
      max-width: calc(100% - 1.6rem);
    }
  }
</style>
