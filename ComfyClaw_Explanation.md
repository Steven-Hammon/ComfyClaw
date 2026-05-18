# ComfyClaw Explanation

ComfyClaw is a prototype environment for designing agentic harnesses inside ComfyUI.

The goal is not to make ComfyUI the fastest way to run an agent. It is to make the agent loop visible. Instead of hiding the heartbeat, memory, context construction, tool selection, and safety checks inside a single script, ComfyClaw breaks them into nodes that can be inspected, tested, and rearranged.

Once an agent workflow feels right, the same design can be converted into faster application code.

## What ComfyClaw Is For

ComfyClaw is useful when you want to understand or prototype:

- How an agent heartbeat works.
- How a chat message enters an agent loop.
- How short-term memory and long-term memory can be updated.
- How a planning step can narrow a large tool list.
- How tool calls can be checked before execution.
- How command-line tools can be wrapped for agent use.
- How context is carried from one cycle to the next.

It is also designed to be modular. You can use `ComfyClaw-Tools` without the ComfyUI nodes if you have another harness that can call command-line tools. You can also use the custom nodes on their own for other ComfyUI workflows.

## Current Limitations

ComfyClaw is early prototype software. The nodes, tools, and local chat service work, but the full agent workflow still needs refinement.

The biggest limitation is the LLM's reliability when following strict tool-call instructions. The model can call tools with the wrong format, omit required fields, choose the wrong tool, or produce text that needs to be repaired before it can be executed safely. That makes ComfyClaw a useful environment for testing agent concepts, but not a highly reliable autonomous agent by itself.

The second major limitation is speed. ComfyUI nodes make the workflow visible and editable, but they are much slower than a purpose-built code harness.

That tradeoff is intentional. ComfyClaw is meant to help people explore agentic concepts and test ideas without needing to build the whole agent stack first.

The chat service is intentionally simple for this testing stage. It does not yet include server/client internet access, text-to-speech, or speech-to-text. Those can be added later if there is enough interest.

ComfyClaw is not an exact clone of OpenClaw. It is groundwork for exploring similar ideas in a visual workflow system.

## Model Requirements

The example workflow was built around a local Ollama model such as `gemma4:e4b` and an embedding model such as `qwen3-embedding`.

With a 128k context window, the model may need around 12 GB of VRAM. You can reduce VRAM use by lowering the context window in Ollama settings. The workflow may still be usable with a smaller context window, such as 32k, depending on the model and task.

To prepare Ollama, run commands like:

```powershell
ollama run gemma4:e4b
ollama pull qwen3-embedding
```

You can chat with the model in the terminal first to make sure it is installed and responding correctly.

## Installation Shape

Clone ComfyClaw into ComfyUI custom nodes:

```powershell
cd C:\ComfyUI\ComfyUI\custom_nodes
git clone https://github.com/Steven-Hammon/ComfyClaw.git
```

The repository root includes a ComfyUI `__init__.py` file. When ComfyUI imports `custom_nodes/ComfyClaw`, that file loads the node package from `ComfyClaw-Nodes`.

The tools use their own virtual environment:

```powershell
cd C:\ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Tools
setup.bat
```

If your workflow reports missing third-party node packs, use ComfyUI Manager to install the missing nodes, then restart the ComfyUI server and refresh the browser.

When you want the agent workflow to keep cycling, use ComfyUI's queue mode dropdown and select **Instant Queue**. When you want normal one-shot/manual execution, switch the dropdown back to **Run**.

## Default Paths

The default agent root path is:

```text
C:\ComfyUI\ComfyUI\custom_nodes\ComfyClaw\ComfyClaw-Agent\
```

The agent, tools, and chat folders can live somewhere else, but the workflow and chat settings must point to the correct locations. Only the ComfyUI node package needs to be importable by ComfyUI.

If you use a different folder, update these six locations:

1. In the ComfyClaw workflow, set the root directory of your `ComfyClaw-Agent` folder.
2. In the workflow's Get Folder Paths group, set `Path_ALLOWED_DIRECTORY`.
3. In the same group, set `Path_CLI_TOOLS`.
4. In `ComfyClaw-Chat/chat_settings.json`, set `download_dir`.
5. In `ComfyClaw-Chat/chat_settings.json`, set `chat_to_agent_file`.
6. In `ComfyClaw-Chat/chat_settings.json`, set `agent_to_chat_file`.

If you use a different LLM or embedding model, update the model names in the workflow's model setup section.

## Workflow Overview

The agent workflow has two broad regions.

The top region prepares the context for each cycle. It loads chat history, memory state, heartbeat state, paths, model settings, prompts, and any other information the model needs to respond correctly.

The lower region decides what to do with that context. It routes the cycle through heartbeat checks, memory maintenance, planning, main model response, tool execution, safety checks, and memory updates.

## Starting A Cycle

At the start of each cycle, the agent decides what kind of work is needed.

If there is a user message or a heartbeat task request, the agent skips background maintenance and responds directly. If there is nothing urgent, it checks the heartbeat and performs long-term memory maintenance.

This gives the workflow two modes:

- **Reactive mode:** respond to the user or a scheduled task.
- **Maintenance mode:** update heartbeat state and clean long-term memory.

For repeated cycle testing, ComfyUI's **Instant Queue** mode is useful because it immediately queues the next run. For one manual cycle at a time, switch back to **Run**.

## Planning And Tool Choice

The workflow uses a planning step before the main model response.

The reason is simple: putting dozens of tool descriptions in front of the main model can be distracting. The planning step acts like a lightweight subconscious process. It suggests a small set of useful tools, usually around two to five, so the main model has a narrower and cleaner decision space.

The main model then chooses what to do next.

Common actions include:

- `SEND_MESSAGE`: send a message directly to the user.
- `SEARCH_LTM`: query long-term memory through retrieval.
- `SLEEP`: wait when no action is needed.
- `CMD`: run a command through the persistent Exec node after checks.
- Tool keys such as `FETCH-GET`, `FILE_READ-FULL`, or `MCP-CALL`: call `ComfyClaw-Tools`.

## Safety Checks

Before tool output is trusted, and before external actions are executed, the workflow performs safety checks.

The first check looks for prompt-injection behavior. The idea is to ask the model to return a known safe response. If the safe response is preserved, the attempted injection has not taken control of the model's instruction-following path.

The second check validates tool calls. It checks whether the requested action stays inside the allowed directory and avoids unauthorized commands.

If a command is allowed, the workflow sends it to the Exec node. Exec keeps a persistent terminal state, so the workflow can navigate directories and continue work across cycles.

If the action is a ComfyClaw tool call, the workflow sends it to `ComfyClaw-Tools/run_tool.py`. The tool response is checked again before being used, because external content such as a web page can also contain prompt-injection attempts.

## Memory Flow

After each cycle, the workflow prepares information for the next cycle.

The newest interaction is appended to `LAST_RESPONSES`. Only a small number of full responses are kept there so the active context stays fresh without becoming too large.

When `LAST_RESPONSES` grows too long, the oldest full response is compressed into short-term memory (`STM`). Tool calls and tool responses are summarized so the useful information remains without carrying unnecessary detail.

When short-term memory grows too long, the oldest short-term memory is converted into long-term memory (`LTM`). During that step, the workflow can add:

- A concise memory summary.
- Importance scoring.
- Keyword associations.
- Relationship notes.
- Embeddings for retrieval.

This creates a rough memory web rather than a flat log.

## Long-Term Memory Recall

`SEARCH_LTM` retrieves long-term memories with embeddings and keyword associations. Memories that are recalled more recently or more often can become more important.

During long-term memory sleep or maintenance, memories can be re-scored. If the memory store grows beyond its limit, the least important older memories can be removed until the store is back under the target size.

## Future Direction

One possible future direction is a "dreaming" process during long-term memory sleep. Memories could be streamed back into short-term memory, re-evaluated, connected to related memories, and updated when new meaning or stronger relationships are found.

Another longer-term idea is a much faster low-latency agent loop. A small model with vision and audio could choose from a compact set of human-like tools such as click, type, think, and wait. Instead of relying on a huge context window, it could operate on tiny, fast chunks of memory and action.

That is beyond the current prototype, but it is part of the broader design direction: smaller cycles, clearer state, visible decisions, and tool use that can be inspected.
