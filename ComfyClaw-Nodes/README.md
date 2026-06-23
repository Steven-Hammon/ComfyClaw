# ComfyClaw Nodes

ComfyClaw is a ComfyUI custom node pack for building OpenClaw-style agents from small, composable workflow primitives.

The design goal is simple: each node does one job, returns predictable outputs, and exposes a plain-English `error_string` instead of crashing the workflow.

## Included Nodes

This folder contains the node package used by the full ComfyClaw repository.

- Core: `Prompt_Combine`, `Text_Gate`, `Route`, `String_Find_Replace`, `File_Read`, `File_Write`, `Text_Cleaner`, `Random_from_List`
- JSON/YAML: `JSON_Cleaner`, `JSON_Count_keys`, `JSON_Read`, `YAML_Read`, `YAML_To_JSON`, `JSON_To_YAML`, `JSON_TO_Markdown`, `Markdown_TO_JSON`, `String_To_Escaped_JSON`, `Escaped_JSON_To_String`, `JSON_Append`, `JSON_Edit`, `JSON_Find_First_Last`, `JSON_insert_key`, `JSON_Mass_Math`, `JSON_Mass_Math_Keys`, `JSON_Mass_Remove`, `JSON_Remove_Entry`, `JSON_Tally_Found_Keys`, `JSON_to_outputs`, `Embedding_Bundle_To_JSON`, `Embedding_Query_To_JSON`
- Embedding: `Load_Embedding_Model`, `Load_Embedding_API`, `Embedding`, `Embedding_Query`, `Chunk_Splitter`
- LLM: `LLM_API_Loader`, `LLM_Model_Loader`, `LLMCall`
- Utility: `Boolean_Output_Switch`, `Or_And`, `Any_To_Something`, `Save_Media_As`, `Token_Estimator`, `Timestamp`, `Timer_Node`, `Trigger`, `Has_Changed`, `Preview_Any_As_Text`
- MCP: `MCP_Server_Loader`, `MCP_List_Tools`, `MCP_Call`
- System: `Exec`, `Tool_Caller`, `PyAutoGUI_Simple_OCR`

## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Steven-Hammon/ComfyClaw.git
cd ComfyClaw
pip install -r requirements.txt
```

Restart ComfyUI after installation.

When the full repository is cloned into `custom_nodes`, ComfyUI imports the root `__init__.py`, which delegates to this `ComfyClaw-Nodes` package.

## Runtime Notes

- YAML nodes use `PyYAML`; install `requirements.txt` before starting ComfyUI.
- Local LLM and embedding nodes assume an Ollama server is available.
- Remote LLM and embedding nodes expect OpenAI-compatible HTTP APIs.
- MCP nodes target HTTP-accessible MCP servers.
- Variable-slot nodes support up to 20 inputs/rules/branches.
- `Prompt_Combine`, `Text_Gate`, `Route`, `Random_from_List`, and `Or_And` expose add/remove controls through `web/comfyclaw_dynamic_inputs.js`.
- `JSON_to_outputs` adds output mode dropdowns through `web/json_to_outputs.js`.
- `Chunk_Splitter` uses fixed `main_chunk`, `chunk_limit`, and `chunk_overlap` sections, each with its own split type and up to 5 custom markers.
- `Exec` keeps a per-node shell session alive across runs until you send `exit`, and it can return either the current command output or the full session transcript in `terminal_text`.
- `PyAutoGUI_Simple_OCR` runs one PyAutoGUI-style desktop command, captures a fresh desktop state, composites optional background/screenshot/overlay/cursor image layers, and returns normalized OCR JSON plus an `error_string`. `wait` and `wait(seconds)` are handled as polling commands. Tesseract can use `tesseract_exe_path`, or auto-detects common Windows install paths. PaddleOCR uses a conservative CPU profile with MKLDNN/oneDNN disabled to avoid common Windows Paddle runtime failures.
- `LLMCall` accepts optional `IMAGE` and `AUDIO` inputs plus `image_file_path` and `sound_file_path`. `media_conversion` is explicit: `base64` sends media bytes in the request where supported, while `path_only` appends stable media path lines to the prompt.
- `Save_Media_As` saves a ComfyUI image, audio, or text input as `png`, `jpg`, `wav`, `mp3`, or `txt`. WAV is built in; MP3 encoding requires optional `pydub` plus ffmpeg.

## Validation

Local smoke checks included in `test_comfyclaw.py` currently pass with:

```bash
python -m unittest -v test_comfyclaw.py
```

## Repository Files

- Repository entrypoint: `../__init__.py`
- Node package entrypoint: `__init__.py`
- Root registry metadata: `../pyproject.toml`
- License: Apache License 2.0

## Publishing Checklist

1. Confirm `tool.comfy.PublisherId` in `pyproject.toml` matches your real Comfy Registry publisher id.
2. Add the GitHub Actions secret `REGISTRY_ACCESS_TOKEN`.
3. Commit and push to the GitHub repository.
4. Bump the version in `pyproject.toml` for each registry release.
