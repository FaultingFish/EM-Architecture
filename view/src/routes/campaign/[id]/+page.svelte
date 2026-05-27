<script lang="ts">
  import { page } from '$app/stores';
  // Live campaign view.
  // TODO: progress bar, Scene3D, current sweep params, LogTail filtered to this campaign.
  $: id = $page.params.id;
</script>

<h2>Campaign: {id}</h2>
<p>TODO: live progress + Scene3D + log.</p>
