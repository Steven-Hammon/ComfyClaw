# Fresh Clone Test

Use this checklist to test ComfyClaw from a clean clone inside ComfyUI.

## Goal

A successful clone test means:

- ComfyUI imports `custom_nodes/ComfyClaw` without an import error.
- ComfyClaw nodes appear in the node menu under `ComfyClaw/...` categories.
- The example workflow can be loaded from `ComfyClaw-Nodes/example_workflow/ClawAgent1-10.json`.
- Missing third-party workflow nodes can be resolved through ComfyUI Manager.
- The agent workflow can run one manual cycle with **Run**, and repeated cycles with **Instant Queue**.

## Before Testing

If you already have a test copy of ComfyClaw in `custom_nodes`, remove or rename it first so you know the test is using the fresh GitHub clone.

Make sure you install Python packages into the same Python environment that starts ComfyUI. This matters most for ComfyUI portable installs.

## Clone And Install

Standard install:

```powershell
cd C:\ComfyUI\ComfyUI\custom_nodes
git clone https://github.com/Steven-Hammon/ComfyClaw.git
cd ComfyClaw
python -m pip install -r requirements.txt
```

ComfyUI portable install example:

```powershell
cd C:\ComfyUI_windows_portable\ComfyUI\custom_nodes
git clone https://github.com/Steven-Hammon/ComfyClaw.git
cd ComfyClaw
..\..\python_embeded\python.exe -m pip install -r requirements.txt
```

Restart ComfyUI after installing the node requirements.

## Tool Environment

The CLI tools use a separate virtual environment:

```powershell
cd C:\ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Tools
setup.bat
```

For portable ComfyUI, adjust the path to wherever the cloned `ComfyClaw-Tools` folder is.

## Model Environment

For the example agent workflow, Ollama should be installed and running. Pull the model and embedding model you plan to use, for example:

```powershell
ollama run gemma4:e4b
ollama pull qwen3-embedding
```

If you use different models, update the workflow's model setup section.

## Workflow Setup

Load:

```text
ComfyClaw-Nodes/example_workflow/ClawAgent1-10.json
```

Then update the six path locations if your clone is not at the default path:

1. In the workflow, set the root directory of `ComfyClaw-Agent`.
2. In the Get Folder Paths group, set `Path_ALLOWED_DIRECTORY`.
3. In the same group, set `Path_CLI_TOOLS`.
4. In `ComfyClaw-Chat/chat_settings.json`, set `download_dir`.
5. In `ComfyClaw-Chat/chat_settings.json`, set `chat_to_agent_file`.
6. In `ComfyClaw-Chat/chat_settings.json`, set `agent_to_chat_file`.

The default agent root path is:

```text
C:\ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Agent\
```

## Queue Mode

Use ComfyUI's queue mode dropdown:

- **Run** for one manual cycle.
- **Instant Queue** for repeated agent-loop cycles.

Switch back to **Run** when you do not want the workflow to continue cycling.

## Troubleshooting

If ComfyClaw nodes do not appear, restart ComfyUI and check the ComfyUI console for an import error mentioning `ComfyClaw`.

If the workflow opens with missing nodes, use ComfyUI Manager to install the missing node packs, then restart ComfyUI and refresh the browser.

If tool calls fail, check that `Path_CLI_TOOLS` points to the cloned `ComfyClaw-Tools` folder and that `setup.bat` completed.

If file or workspace operations fail, check that `Path_ALLOWED_DIRECTORY` points to the directory you want the agent to access.

If model calls fail, confirm Ollama is running and the workflow model names match models available in Ollama.

If the agent chooses malformed tool calls, that is a known limitation of the prototype. The project is meant to expose and test those issues, not hide them.
