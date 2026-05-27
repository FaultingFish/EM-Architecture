<script lang="ts">
  import ArmButton from '$lib/components/ArmButton.svelte';
  import DeviceStatusCard from '$lib/components/DeviceStatusCard.svelte';
  import LogTail from '$lib/components/LogTail.svelte';
  import { countersStore } from '$lib/stores/counters';
  import { devicesStore } from '$lib/stores/devices';
  import { positionStore } from '$lib/stores/position';
</script>

<h2>Mission Control</h2>

<section>
  <ArmButton />
</section>

<section>
  <h3>Position</h3>
  <p>x={$positionStore.x} y={$positionStore.y} z={$positionStore.z}</p>
</section>

<section>
  <h3>Counters</h3>
  <p>
    attempts={$countersStore.attempts}
    glitches={$countersStore.glitches}
    hangs={$countersStore.hangs}
    crashes={$countersStore.crashes}
    nothings={$countersStore.nothings}
  </p>
</section>

<section>
  <h3>Devices</h3>
  {#each [...$devicesStore.values()] as device (device.name)}
    <DeviceStatusCard {device} />
  {/each}
  {#if $devicesStore.size === 0}
    <p>No device status received yet.</p>
  {/if}
</section>

<section>
  <h3>Live Log</h3>
  <LogTail limit={200} />
</section>
