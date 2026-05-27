<script lang="ts">
  // 2D canvas heatmap of {x, y, count} cells.
  // TODO:
  //   - Take props: cells, x/y extents, step size, color scale
  //   - Render with a single canvas; redraw on prop changes
  //   - Tooltip on hover showing (x, y, count)
  //   - Z-slider lives in the parent
  export let cells: { x: number; y: number; count: number }[] = [];
</script>

<canvas width="600" height="400">heatmap canvas</canvas>
<p>{cells.length} cells</p>

<style>
  canvas { background: #111; }
</style>
