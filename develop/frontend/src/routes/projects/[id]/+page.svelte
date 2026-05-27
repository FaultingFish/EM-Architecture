<script lang="ts">
  import { page } from '$app/stores';
  // Project editor: file tree + Monaco editor + build console + git ops.
  // TODO:
  //   - Left: ProjectTree fetching GET /projects/{id}/tree
  //   - Center: MonacoEditor bound to currently open file (GET/PUT /projects/{id}/file)
  //   - Right: BuildLog (WS topic build_log) + Build button
  //   - Header: git commit + tag, agent prompt input
  $: id = $page.params.id;
</script>

<h2>Project: {id}</h2>
<p>TODO: file tree + editor + build console.</p>
