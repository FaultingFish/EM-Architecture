<script lang="ts">
  import { onMount } from 'svelte';
  import { armStore } from '$lib/stores/arm';
  import StopButton from '$lib/components/StopButton.svelte';
  import { stopCampaign } from '$lib/api/control';
  import { connect } from '$lib/ws/control_ws';

  let ws: WebSocket | null = null;

  onMount(() => {
    ws = connect();
    return () => ws?.close();
  });

  function handleGlobalStop() {
    // TODO: track active campaign ID in a store; pass it here
    stopCampaign('current');
  }
</script>

<header>
  <h1><a href="/">EMFI View</a></h1>
  <nav>
    <a href="/">Mission</a>
    <a href="/campaign">New campaign</a>
    <a href="/runs">Runs</a>
    <a href="/heatmap">Heatmap</a>
    <a href="/assembly">Assembly</a>
  </nav>
  <span class="arm-indicator" class:armed={$armStore.armed}>
    {#if $armStore.armed}
      ARMED
      {#if $armStore.seconds_until_auto_disarm != null}
        ({Math.ceil($armStore.seconds_until_auto_disarm)}s)
      {/if}
    {:else}
      safe
    {/if}
  </span>
</header>

<main>
  <slot />
</main>

<div class="floating-stop">
  <StopButton onStop={handleGlobalStop} />
</div>

<style>
  header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid #ddd;
    background: #fafafa;
  }
  h1 { font-size: 1.1rem; margin: 0; }
  h1 a { color: inherit; text-decoration: none; }
  nav { display: flex; gap: 0.75rem; flex: 1; }
  .arm-indicator { padding: 0.2rem 0.6rem; border-radius: 0.25rem; background: #ddd; }
  .arm-indicator.armed { background: #c00; color: #fff; font-weight: 700; }
  main { padding: 1rem; }
  .floating-stop {
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 9999;
  }
</style>
