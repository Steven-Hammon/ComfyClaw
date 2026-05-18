# ComfyClaw

ComfyClaw is a ComfyUI custom node pack and prototype agent harness. It is designed for mapping out agentic workflows inside ComfyUI so you can see the moving parts: heartbeat checks, short-term memory, long-term memory, tool calls, chat handoff, security checks, and the context that moves between each cycle.

The ComfyUI nodes are only one part of the project. The tools and local chat service can also be used by another harness if you want a simpler code-driven agent runner.

## Repository Layout

```text
ComfyClaw/
|-- __init__.py
|-- README.md
|-- requirements.txt
|-- ComfyClaw-Agent/
|   |-- prompts/
|   |-- Workspace/
|   |-- HEARTBEAT.json
|   |-- LAST_RESPONSES.json
|   |-- LTM.json
|   |-- STM.json
|   |-- TOOLS.json
|-- ComfyClaw-Chat/
|   |-- chat_service.py
|   |-- chat_settings.json
|   |-- run_chat_service.bat
|-- ComfyClaw-Nodes/
|   |-- __init__.py
|   |-- web/
|   |-- example_workflow/
|   |-- docs/
|-- ComfyClaw-Tools/
|   |-- run_tool.py
|   |-- setup.bat
|   |-- tools/
```

The repo root has its own `__init__.py` because ComfyUI imports custom node folders from the immediate `custom_nodes` directory. When this repository is cloned as `ComfyUI/custom_nodes/ComfyClaw`, the root entrypoint loads the node registrations from `ComfyClaw-Nodes/` and exposes the web assets from `ComfyClaw-Nodes/web`.

## Install

Clone the repo into ComfyUI custom nodes:

```powershell
cd C:\ComfyUI\ComfyUI\custom_nodes
git clone https://github.com/Steven-Hammon/ComfyClaw.git
cd ComfyClaw
pip install -r requirements.txt
```

Restart ComfyUI after cloning and installing the node requirements.

The tools use their own virtual environment so they do not pollute your ComfyUI Python environment:

```powershell
cd C:\ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Tools
setup.bat
```

ComfyClaw-Agent expects Ollama to be installed and running. Download the model you want to use, for example:

```powershell
ollama run gemma4:e4b
ollama pull qwen3-embedding
```

You can use a smaller context window in Ollama settings if your GPU has less VRAM.

## Paths To Change

The default agent root path is:

```text
C:\ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Agent\
```

If you install ComfyClaw somewhere else, update these six path locations:

1. In the ComfyClaw workflow, set the root directory of your `ComfyClaw-Agent` folder.
2. In the workflow's Get Folder Paths group, update `Path_ALLOWED_DIRECTORY`.
3. In the same workflow group, update `Path_CLI_TOOLS`.
4. In `ComfyClaw-Chat/chat_settings.json`, update `download_dir`.
5. In `ComfyClaw-Chat/chat_settings.json`, update `chat_to_agent_file`.
6. In `ComfyClaw-Chat/chat_settings.json`, update `agent_to_chat_file`.

If you use a different LLM or embedding model, update the model values in the workflow's model setup section.

## Main Pieces

- `ComfyClaw-Nodes` contains the ComfyUI custom nodes.
- `ComfyClaw-Agent` contains the prompt files, memory files, workspace, heartbeat state, and tool descriptions used by the agent workflow.
- `ComfyClaw-Tools` contains the CLI tool runner for browser, fetch, file, search, PDF, RAG, and MCP actions.
- `ComfyClaw-Chat` contains a simple local chat bridge that reads and writes the agent message files.

The example workflow is in `ComfyClaw-Nodes/example_workflow/`.

## Validation

From the node folder:

```powershell
cd C:\ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Nodes
python -m unittest -v test_comfyclaw.py
```

You can also smoke-test the root ComfyUI entrypoint from the repo root:

```powershell
python -c "import importlib.util, pathlib, sys; root=pathlib.Path('.').resolve(); spec=importlib.util.spec_from_file_location('ComfyClaw', root / '__init__.py', submodule_search_locations=[str(root)]); mod=importlib.util.module_from_spec(spec); sys.modules['ComfyClaw']=mod; spec.loader.exec_module(mod); print(len(mod.NODE_CLASS_MAPPINGS), mod.WEB_DIRECTORY)"
```

## More Detail

`ComfyClaw_Explaination.md` contains the longer design explanation, including how the heartbeat, memory flow, subconscious tool suggestion step, tool security checks, and chat loop are intended to work.

## License

Apache License 2.0. See `LICENSE`.
