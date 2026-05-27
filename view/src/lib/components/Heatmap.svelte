<script lang="ts">
  import { onMount } from 'svelte';

  export let cells: { x: number; y: number; count: number }[] = [];
  export let width = 600;
  export let height = 400;

  let canvas: HTMLCanvasElement;

  $: if (canvas && cells) draw(cells);

  function draw(data: typeof cells) {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = '#111';
    ctx.fillRect(0, 0, width, height);
    if (data.length === 0) {
      ctx.fillStyle = '#8b91a3';
      ctx.font = '13px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No heatmap data', width / 2, height / 2);
      return;
    }

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, maxC = 0;
    for (const c of data) {
      if (c.x < minX) minX = c.x;
      if (c.x > maxX) maxX = c.x;
      if (c.y < minY) minY = c.y;
      if (c.y > maxY) maxY = c.y;
      if (c.count > maxC) maxC = c.count;
    }
    if (maxC === 0) return;

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const pad = 30;
    const drawW = width - pad * 2;
    const drawH = height - pad * 2;

    const xSteps = new Set(data.map((c) => c.x)).size;
    const ySteps = new Set(data.map((c) => c.y)).size;
    const cellW = Math.max(2, drawW / xSteps);
    const cellH = Math.max(2, drawH / ySteps);

    for (const c of data) {
      const px = pad + ((c.x - minX) / rangeX) * drawW;
      const py = pad + ((c.y - minY) / rangeY) * drawH;
      const intensity = c.count / maxC;
      ctx.fillStyle = heatColor(intensity);
      ctx.fillRect(px - cellW / 2, py - cellH / 2, cellW, cellH);
    }

    ctx.fillStyle = '#8b91a3';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(minX.toFixed(1), pad, height - 8);
    ctx.fillText(maxX.toFixed(1), width - pad, height - 8);
    ctx.textAlign = 'right';
    ctx.fillText(minY.toFixed(1), pad - 4, pad + 4);
    ctx.fillText(maxY.toFixed(1), pad - 4, height - pad + 4);
  }

  function heatColor(t: number): string {
    if (t < 0.25) return `rgb(0, ${Math.round(t * 4 * 200)}, ${Math.round(80 + t * 4 * 175)})`;
    if (t < 0.5) return `rgb(0, ${Math.round(200 + (t - 0.25) * 4 * 55)}, ${Math.round(255 - (t - 0.25) * 4 * 255)})`;
    if (t < 0.75) return `rgb(${Math.round((t - 0.5) * 4 * 249)}, ${Math.round(255 - (t - 0.5) * 4 * 96)}, 0)`;
    return `rgb(255, ${Math.round(159 - (t - 0.75) * 4 * 159)}, 0)`;
  }

  let tooltipText = '';
  let tooltipX = 0;
  let tooltipY = 0;
  let showTooltip = false;

  function onMouseMove(ev: MouseEvent) {
    if (cells.length === 0) { showTooltip = false; return; }
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const my = ev.clientY - rect.top;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const c of cells) {
      if (c.x < minX) minX = c.x;
      if (c.x > maxX) maxX = c.x;
      if (c.y < minY) minY = c.y;
      if (c.y > maxY) maxY = c.y;
    }
    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const pad = 30;
    const drawW = width - pad * 2;
    const drawH = height - pad * 2;

    let closest: (typeof cells)[0] | null = null;
    let bestDist = 20;
    for (const c of cells) {
      const px = pad + ((c.x - minX) / rangeX) * drawW;
      const py = pad + ((c.y - minY) / rangeY) * drawH;
      const d = Math.hypot(mx - px, my - py);
      if (d < bestDist) { bestDist = d; closest = c; }
    }
    if (closest) {
      tooltipText = `(${closest.x}, ${closest.y}) = ${closest.count}`;
      tooltipX = ev.clientX;
      tooltipY = ev.clientY;
      showTooltip = true;
    } else {
      showTooltip = false;
    }
  }

  onMount(() => { draw(cells); });
</script>

<div class="heatmap-wrap">
  <canvas
    bind:this={canvas}
    {width}
    {height}
    on:mousemove={onMouseMove}
    on:mouseleave={() => (showTooltip = false)}
  ></canvas>
  {#if showTooltip}
    <div class="tooltip" style="left: {tooltipX + 12}px; top: {tooltipY - 10}px;">
      {tooltipText}
    </div>
  {/if}
</div>

<style>
  .heatmap-wrap { position: relative; display: inline-block; }
  canvas { background: #111; border-radius: var(--radius); }
  .tooltip {
    position: fixed;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.2rem 0.5rem;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--fg);
    pointer-events: none;
    z-index: 100;
    white-space: nowrap;
  }
</style>
