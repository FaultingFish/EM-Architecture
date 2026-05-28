<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { armStore } from '$lib/stores/arm';
  import { devicesStore, KNOWN_DEVICES, placeholderStatus } from '$lib/stores/devices';
  import { activeCampaign } from '$lib/stores/campaign';
  import ArmButton from '$lib/components/ArmButton.svelte';
  import StopButton from '$lib/components/StopButton.svelte';
  import DevicePill from '$lib/components/DevicePill.svelte';
  import Toast from '$lib/components/Toast.svelte';
  import { stopCampaign, disarm } from '$lib/api/control';
  import { connect } from '$lib/ws/control_ws';
  import { toasts } from '$lib/stores/toast';

  // Always render a pill for every known device, falling back to a placeholder
  // (unavailable) until Control emits a device_status event for it.
  $: pillDevices = KNOWN_DEVICES.map((n) => $devicesStore.get(n) ?? placeholderStatus(n));

  onMount(() => {
    connect();
  });

  async function handleGlobalStop() {
    try {
      const camp = $activeCampaign;
      if (camp?.active) await stopCampaign(camp.campaign_id);
      await disarm();
      toasts.warn('STOPPED');
    } catch {
      toasts.error('Stop failed');
    }
  }

  $: currentPath = $page.url.pathname;
</script>

<div class="app">
  <header class="topbar">
    <a href="/" class="brand">EMFI</a>

    <nav>
      <a href="/" class:active={currentPath === '/'}>Mission</a>
      <a href="/campaign" class:active={currentPath.startsWith('/campaign')}>Campaign</a>
      <a href="/runs" class:active={currentPath === '/runs'}>Runs</a>
      <a href="/heatmap" class:active={currentPath === '/heatmap'}>Heatmap</a>
      <a href="/assembly" class:active={currentPath === '/assembly'}>Assembly</a>
    </nav>

    <div class="device-strip">
      {#each pillDevices as dev (dev.name)}
        <DevicePill device={dev} />
      {/each}
    </div>

    <div class="topbar-right">
      <ArmButton />

      <span class="arm-indicator" class:armed={$armStore.armed}>
        {#if $armStore.armed}
          ARMED
          {#if $armStore.seconds_until_auto_disarm != null}
            <span class="countdown">{Math.ceil($armStore.seconds_until_auto_disarm)}s</span>
          {/if}
        {:else}
          SAFE
        {/if}
      </span>

      <StopButton onStop={handleGlobalStop} />
    </div>
  </header>

  <main>
    <slot />
  </main>
</div>

<Toast />

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .topbar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0 1rem;
    height: 48px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .brand {
    font-size: 16px;
    font-weight: 700;
    color: var(--accent);
    text-decoration: none;
    letter-spacing: 0.05em;
  }

  nav {
    display: flex;
    gap: 0.1rem;
    flex: 1;
  }
  nav a {
    padding: 0.3rem 0.6rem;
    border-radius: var(--radius);
    font-size: 12px;
    color: var(--muted);
    text-decoration: none;
    transition: background 0.15s, color 0.15s;
  }
  nav a:hover { color: var(--fg); background: var(--panel-2); }
  nav a.active { color: var(--accent); background: var(--panel-2); }

  .topbar-right {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .device-strip {
    display: flex;
    gap: 0.35rem;
    margin-left: auto;
  }

  .arm-indicator {
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    background: var(--panel-2);
    color: var(--muted);
  }
  .arm-indicator.armed {
    background: var(--err);
    color: #fff;
    animation: blink 1s steps(1) infinite;
  }
  .countdown { font-family: var(--mono); font-weight: 400; }

  main {
    flex: 1;
    overflow: auto;
    padding: 0;
  }

  @keyframes blink {
    50% { opacity: 0.7; }
  }
</style>
