<script lang="ts">
  // Three.js stage view. Renders gantry, DUT plane, current shover position.
  // TODO:
  //   - Dynamic import of three (browser only)
  //   - Subscribe to positionStore, update mesh transform
  //   - Click-to-jog: raycast onto the bed plane → call /motion/move_abs
  //   - Optional: overlay sweep path during a campaign
  import { onMount } from 'svelte';
  import { positionStore } from '$lib/stores/position';

  let container: HTMLDivElement;

  onMount(() => {
    // TODO: init Three.js scene here
  });
</script>

<div bind:this={container} class="scene"></div>
<p>Current: ({$positionStore.x}, {$positionStore.y}, {$positionStore.z})</p>

<style>
  .scene { width: 100%; height: 50vh; background: #222; }
</style>
