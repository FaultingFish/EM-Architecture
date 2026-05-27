<script lang="ts">
  import { page } from '$app/stores';
  // Assembly view + target picker.
  // TODO:
  //   - Pick a build SHA (default: latest)
  //   - Fetch GET /projects/{id}/builds/{sha}/disassembly
  //   - Render via AssemblyView component (virtualized list)
  //   - Click an instruction → opens "add target" dialog (name, expected_delay_cycles, notes)
  //   - POST /projects/{id}/targets to persist
  $: id = $page.params.id;
</script>

<h2>Assembly: {id}</h2>
<p>TODO: render AssemblyListing and let user pick target instructions.</p>
