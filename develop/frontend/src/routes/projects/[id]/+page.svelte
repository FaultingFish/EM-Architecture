<script lang="ts">
  import { page } from '$app/stores';
  import { onMount, onDestroy } from 'svelte';
  import ProjectTree from '$lib/components/ProjectTree.svelte';
  import MonacoEditor from '$lib/components/MonacoEditor.svelte';
  import BuildLog from '$lib/components/BuildLog.svelte';
  import {
    getProject, getFileTree, getFile, putFile,
    triggerBuild, gitCommit, gitTag, gitLog, runAgent, flashToTarget, listBuilds
  } from '$lib/api';
  import { ws } from '$lib/ws';
  import { buildLog, buildStatus, agentOutput } from '$lib/stores';
  import type { Project, FileTreeNode, BuildArtifact, WsEvent, GitLogEntry } from '$lib/types';

  let monacoComponent: MonacoEditor;

  $: id = $page.params.id as string;

  let project: Project | null = null;
  let tree: FileTreeNode | null = null;
  let builds: BuildArtifact[] = [];
  let currentFile = '';
  let fileContent = '';
  let fileLang = 'c';
  let dirty = false;
  let saving = false;
  let building = false;
  let error = '';
  let tab: 'build' | 'agent' | 'git' = 'build';

  let commitMsg = '';
  let tagName = '';
  let agentPrompt = '';
  let gitEntries: GitLogEntry[] = [];

  function handleBuildLog(ev: WsEvent) {
    if (ev.payload?.project_id === id) {
      buildLog.update(lines => [...lines, ev.payload?.line as string]);
    }
  }
  function handleBuildStatus(ev: WsEvent) {
    if (ev.payload?.project_id === id) {
      buildStatus.set(ev.payload?.phase as string);
      if (ev.payload?.phase === 'done' || ev.payload?.phase === 'failed') {
        building = false;
        refreshBuilds();
      }
    }
  }
  function handleAgentOutput(ev: WsEvent) {
    if (ev.payload?.project_id === id) {
      agentOutput.update(lines => [...lines, ev.payload?.line as string]);
    }
  }

  onMount(async () => {
    try {
      [project, tree, builds] = await Promise.all([
        getProject(id), getFileTree(id), listBuilds(id)
      ]);
    } catch (e: any) { error = e.message; }

    ws.connect();
    ws.subscribe('build_log', handleBuildLog);
    ws.subscribe('build_status', handleBuildStatus);
    ws.subscribe('agent_output', handleAgentOutput);
  });

  onDestroy(() => {
    ws.unsubscribe('build_log', handleBuildLog);
    ws.unsubscribe('build_status', handleBuildStatus);
    ws.unsubscribe('agent_output', handleAgentOutput);
  });

  async function openFile(ev: CustomEvent<string>) {
    if (dirty && !confirm('Unsaved changes. Discard?')) return;
    currentFile = ev.detail;
    try {
      const res = await getFile(id, currentFile);
      fileContent = res.contents;
      fileLang = monacoComponent?.detectLanguage?.(currentFile) ?? 'plaintext';
      dirty = false;
    } catch (e: any) { error = e.message; }
  }

  async function saveFile(ev: CustomEvent<string>) {
    if (!currentFile) return;
    saving = true;
    try {
      await putFile(id, currentFile, ev.detail);
      dirty = false;
    } catch (e: any) { error = e.message; }
    saving = false;
  }

  function onEditorChange() { dirty = true; }

  async function doBuild() {
    building = true;
    buildLog.set([]);
    buildStatus.set('starting');
    error = '';
    try {
      await triggerBuild(id);
    } catch (e: any) {
      error = e.message;
      building = false;
    }
  }

  async function doCommit() {
    if (!commitMsg.trim()) return;
    try {
      const r = await gitCommit(id, commitMsg);
      commitMsg = '';
      alert(`Committed: ${r.sha.slice(0, 8)}`);
      refreshGitLog();
    } catch (e: any) { error = e.message; }
  }

  async function doTag() {
    if (!tagName.trim()) return;
    try {
      await gitTag(id, tagName);
      tagName = '';
      project = await getProject(id);
    } catch (e: any) { error = e.message; }
  }

  async function doAgent() {
    if (!agentPrompt.trim()) return;
    agentOutput.set([]);
    tab = 'agent';
    try {
      await runAgent(id, agentPrompt);
      agentPrompt = '';
    } catch (e: any) { error = e.message; }
  }

  async function doFlash() {
    if (builds.length === 0) { error = 'No builds available'; return; }
    const latest = builds[0];
    try {
      await flashToTarget(id, latest.sha);
      alert('Flash request sent to Control');
    } catch (e: any) { error = `Flash failed: ${e.message}`; }
  }

  async function refreshGitLog() {
    try { gitEntries = await gitLog(id); } catch {}
  }

  async function refreshBuilds() {
    try { builds = await listBuilds(id); } catch {}
  }

  function switchTab(t: typeof tab) {
    tab = t;
    if (t === 'git' && gitEntries.length === 0) refreshGitLog();
  }
</script>

<div class="editor-layout">
  <!-- Left: file tree -->
  <div class="panel tree-panel">
    <div class="panel-header">Files</div>
    <div class="panel-body">
      <ProjectTree node={tree} on:select={openFile} />
    </div>
  </div>

  <!-- Center: editor -->
  <div class="panel editor-panel">
    <div class="panel-header">
      {#if currentFile}
        <span class="filepath">{currentFile}</span>
        {#if dirty}<span class="dot">●</span>{/if}
        {#if saving}<span class="saving">Saving…</span>{/if}
      {:else}
        <span class="muted">Select a file</span>
      {/if}
    </div>
    <div class="panel-body">
      {#if currentFile}
        <MonacoEditor
          bind:this={monacoComponent}
          bind:value={fileContent}
          language={fileLang}
          on:save={saveFile}
          on:change={onEditorChange}
        />
      {:else}
        <div class="placeholder">
          <p>Open a file from the tree to start editing.</p>
        </div>
      {/if}
    </div>
  </div>

  <!-- Right: toolbar + console -->
  <div class="panel console-panel">
    <div class="toolbar">
      <button class="btn small" on:click={doBuild} disabled={building}>
        {building ? '⏳ Building…' : '▶ Build'}
      </button>
      <button class="btn small" on:click={doFlash} disabled={builds.length === 0}>Flash</button>
      <a class="btn small link" href="/projects/{id}/asm">ASM</a>
    </div>

    {#if error}
      <div class="error">{error} <button class="btn-icon" on:click={() => error = ''}>✕</button></div>
    {/if}

    <!-- Git controls -->
    <div class="git-row">
      <input type="text" bind:value={commitMsg} placeholder="Commit message" on:keydown={e => e.key === 'Enter' && doCommit()} />
      <button class="btn small" on:click={doCommit} disabled={!commitMsg.trim()}>Commit</button>
      <input type="text" bind:value={tagName} placeholder="Tag" class="short" />
      <button class="btn small" on:click={doTag} disabled={!tagName.trim()}>Tag</button>
    </div>

    <!-- Agent prompt -->
    <div class="git-row">
      <input type="text" bind:value={agentPrompt} placeholder="Ask Claude…" on:keydown={e => e.key === 'Enter' && doAgent()} />
      <button class="btn small" on:click={doAgent} disabled={!agentPrompt.trim()}>Ask</button>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button class:active={tab === 'build'} on:click={() => switchTab('build')}>Build</button>
      <button class:active={tab === 'agent'} on:click={() => switchTab('agent')}>Agent</button>
      <button class:active={tab === 'git'} on:click={() => switchTab('git')}>Git Log</button>
    </div>

    <div class="console-body">
      {#if tab === 'build'}
        <BuildLog lines={$buildLog} />
      {:else if tab === 'agent'}
        <BuildLog lines={$agentOutput} />
      {:else}
        <div class="git-log">
          {#each gitEntries as entry}
            <div class="log-entry">
              <code>{entry.sha.slice(0, 8)}</code>
              <span>{entry.message}</span>
              <span class="date">{entry.date}</span>
            </div>
          {/each}
          {#if gitEntries.length === 0}
            <p class="muted">No commits yet.</p>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .editor-layout {
    display: grid;
    grid-template-columns: 220px 1fr 360px;
    height: 100%;
    gap: 1px;
    background: #ddd;
  }
  .panel { display: flex; flex-direction: column; background: #fff; overflow: hidden; }
  .panel-header {
    padding: 6px 10px;
    font-size: 0.8rem;
    font-weight: 600;
    background: #f5f5f5;
    border-bottom: 1px solid #ddd;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .panel-body { flex: 1; overflow: auto; }
  .tree-panel .panel-body { padding: 6px; }

  .filepath { font-family: monospace; font-weight: 400; }
  .dot { color: #e8a; font-size: 1.2em; }
  .saving { color: #888; font-style: italic; font-weight: 400; }
  .muted { color: #999; }
  .placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: #aaa; }

  .toolbar {
    display: flex; gap: 6px; padding: 6px 10px;
    background: #f5f5f5; border-bottom: 1px solid #ddd;
  }
  .git-row {
    display: flex; gap: 4px; padding: 4px 10px;
    border-bottom: 1px solid #eee;
  }
  .git-row input {
    flex: 1; padding: 4px 8px; border: 1px solid #ccc; border-radius: 3px; font-size: 0.8rem;
  }
  .git-row input.short { max-width: 80px; }

  .tabs {
    display: flex; border-bottom: 1px solid #ddd;
  }
  .tabs button {
    all: unset; cursor: pointer; padding: 6px 12px;
    font-size: 0.8rem; color: #666;
    border-bottom: 2px solid transparent;
  }
  .tabs button.active { color: #222; border-bottom-color: #2563eb; }
  .tabs button:hover { color: #222; }

  .console-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; }

  .error {
    background: #fee; color: #c00; padding: 4px 10px; font-size: 0.8rem;
    display: flex; justify-content: space-between; align-items: center;
  }

  .btn {
    padding: 4px 10px; border: 1px solid #ccc; border-radius: 3px;
    background: #fff; cursor: pointer; font-size: 0.8rem; white-space: nowrap;
  }
  .btn:hover { background: #f0f0f0; }
  .btn:disabled { opacity: 0.4; cursor: default; }
  .btn.small { padding: 3px 8px; font-size: 0.78rem; }
  .btn.link { text-decoration: none; display: inline-flex; align-items: center; }
  .btn-icon { all: unset; cursor: pointer; padding: 0 4px; }

  .git-log { padding: 8px; overflow-y: auto; font-size: 0.8rem; }
  .log-entry { display: flex; gap: 0.75rem; padding: 3px 0; border-bottom: 1px solid #eee; }
  .log-entry code { color: #666; font-size: 0.78rem; flex-shrink: 0; }
  .log-entry .date { color: #999; font-size: 0.72rem; margin-left: auto; flex-shrink: 0; }
</style>
