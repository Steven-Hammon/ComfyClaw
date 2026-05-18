# ComfyClaw Workflow Patterns RAG Reference

Purpose:
This document gives retrieval-friendly assembly patterns for ComfyClaw agentic workflows. Use it alongside `docs/ComfyClaw_Node_RAG.md`. The node reference explains individual nodes; this file explains useful combinations and design habits.

Core principle:
Prefer small, readable chains. ComfyClaw workflows are easier for an agent and a human to improve when text construction, model calls, JSON cleanup, routing, persistence, and tool execution are separate visible nodes.

---CHUNK_BREAK---

## Prompted LLM Call Pattern

Pattern Name:
Prompted LLM Call

Goal:
Build a deterministic prompt from fixed instructions and variable context, then call an LLM.

Typical Node Chain:
PrimitiveString or File_Read -> Prompt_Combine -> LLMCall (with associated LLM loader) -> PreviewAny or JSON_Cleaner or File_Write.

How it works:
Use `PrimitiveString` for short constants and `File_Read` for long instructions or examples. Use `Prompt_Combine` to join system instructions, retrieved context, the user's request, and explicit output requirements. Feed the combined prompt into `LLMCall.user_prompt`. Send the response to `PreviewAny` while developing, to `JSON_Cleaner` when the response should be structured, or to `File_Write` when the response should be persisted.

When to use:
Use this as the default shape for planning, critique, brainstorming, workflow improvement, summarization, and JSON generation.

Agent hints:
When a design says "ask the model", "generate a plan", "improve the workflow", "summarize", or "produce JSON", retrieve `Prompt_Combine`, an LLM loader, and `LLMCall`.

---CHUNK_BREAK---

## Local Document RAG Pattern

Pattern Name:
Local Document RAG

Goal:
Retrieve relevant information from local documents and use it as LLM context.

Typical Node Chain:
File_Read -> Chunk_Splitter -> Load_Embedding_Model or Load_Embedding_API -> Embedding -> File_Write.
Then later:
File_Read -> Load_Embedding_Model or Load_Embedding_API -> Embedding_Query -> Prompt_Combine -> LLMCall.

How it works:
Read the source document with `File_Read`. Split it with `Chunk_Splitter`. Use `Embedding` to create an embedding bundle. Save that bundle with `File_Write` if it should be reused. At query time, read the saved bundle, search it with `Embedding_Query`, and feed `best_chunk_text` or `results_json_string` into `Prompt_Combine`.

When to use:
Use when the agent needs node docs, workflow examples, design notes, memory files, logs, or any local text corpus as context.

Agent hints:
For "RAG", "retrieve docs", "look up relevant node", "semantic search", or "use the documentation", retrieve `File_Read`, `Chunk_Splitter`, embedding loader nodes, `Embedding`, and `Embedding_Query`.

---CHUNK_BREAK---

## Structured LLM Output Pattern

Pattern Name:
Structured LLM Output

Goal:
Ask an LLM for JSON, clean it, then read or edit fields deterministically.

Typical Node Chain:
Prompt_Combine -> LLMCall -> JSON_Cleaner -> JSON_Read / JSON_Edit / JSON_Append / JSON_insert_key / JSON_Remove_Entry -> File_Write.

How it works:
The prompt should explicitly request a JSON object. `LLMCall` returns text that may contain markdown fences or prose. `JSON_Cleaner` extracts and repairs the JSON object. Use `JSON_Read` to extract action fields, `JSON_Edit` to update existing state, `JSON_Append` to add history entries, `JSON_insert_key` to add ordered root sections, and `JSON_Remove_Entry` to prune stale entries.

When to use:
Use for action plans, tool-call plans, memory state, workflow change proposals, structured critiques, and machine-readable self-improvement outputs.

Agent hints:
When a design says "LLM should output an action", "parse response", "structured result", "JSON plan", or "update state", retrieve `JSON_Cleaner` and the relevant JSON operation nodes.

---CHUNK_BREAK---

## Tool Planning And MCP Execution Pattern

Pattern Name:
Tool Planning And MCP Execution

Goal:
Let the model choose an MCP tool, validate the call shape, execute it, and feed the result back into the workflow.

Typical Node Chain:
MCP_Server_Loader -> MCP_List_Tools -> Prompt_Combine -> LLMCall -> JSON_Cleaner -> JSON_Read or Text_Gate -> MCP_Call -> Prompt_Combine -> LLMCall.

How it works:
`MCP_Server_Loader` creates the provider. `MCP_List_Tools` gets available tool schemas. Put tool schemas, task context, and strict output instructions into `Prompt_Combine`. Ask `LLMCall` to return a JSON object like `{"tool":"name","arguments":{...}}`. Use `JSON_Cleaner` and optionally `JSON_Read` or `Text_Gate` to validate the call before `MCP_Call`. Feed `tool_result_text` back into another prompt for interpretation or next-step planning.

When to use:
Use when a workflow should call external tools, search services, project APIs, local services, or custom MCP endpoints.

Agent hints:
For "use a tool", "call MCP", "list available tools", "tool schema", "execute external action", retrieve MCP nodes plus `JSON_Cleaner`.

---CHUNK_BREAK---

## Shell Command Pattern

Pattern Name:
Shell Command Execution

Goal:
Run local shell commands in a controlled, inspectable way.

Typical Node Chain:
Prompt_Combine or PrimitiveString -> Text_Gate / StringCompare / easy blocker -> Exec -> PreviewAny -> File_Write or Prompt_Combine.

How it works:
Use `Prompt_Combine` or `PrimitiveString` to define the command. If an LLM generated the command, gate it before execution. `Text_Gate` can deny dangerous substrings. `StringCompare` or `easy compare` can produce boolean checks. `easy blocker` can act as a manual continue switch. `Exec` runs the command and returns terminal output. Use `PreviewAny` while debugging and `File_Write` for logs.

When to use:
Use for tests, file inspection, CLI tooling, environment checks, and controlled automation.

Agent hints:
For "run command", "terminal", "execute tests", "list files", or "inspect environment", retrieve `Exec`, `Text_Gate`, `easy blocker`, and `PreviewAny`.

---CHUNK_BREAK---

## Safety Gate Pattern

Pattern Name:
Safety Gate

Goal:
Prevent unsafe, empty, malformed, or unwanted outputs from reaching expensive or state-changing nodes.

Typical Node Chain:
LLMCall or Prompt_Combine -> Text_Gate / StringCompare / easy compare / easy blocker -> Exec or MCP_Call or File_Write.

How it works:
Use `Text_Gate` for text content rules such as blocking `rm`, requiring a prefix, or allowing only strings containing a marker. Use `StringCompare` for a direct string boolean. Use `easy compare` for value comparisons such as token count less than a threshold. Use `easy blocker` for a manual or boolean pass-through checkpoint before actions. For Exec (Shell Command Execution), it's best to block \n to ensure a safe command with args can run but without any subsequent dangerous commands afterwards. 

When to use:
Use before `Exec`, `MCP_Call`, `File_Write`, long `LLMCall` chains, or any node that changes files or invokes external systems.

Agent hints:
For "guard", "safety", "only continue if", "manual approval", "block dangerous", or "threshold", retrieve gating helper nodes.

---CHUNK_BREAK---

## Timed Autonomous Loop Pattern

Pattern Name:
Timed Autonomous Loop

Goal:
Run an agent step only on a schedule or interval.

Typical Node Chain:
Timer_Node -> Text_Gate or easy blocker -> Prompt_Combine -> LLMCall -> JSON_Cleaner -> File_Write.

How it works:
`Timer_Node` emits text only when the interval or clock schedule fires. Use `Text_Gate` to check that the timer output is non-empty, or use `easy blocker` as a manual continue checkpoint. The fired text can become part of the prompt. Persist run results and state with `File_Write`, usually with `Timestamp` included in logs. A heartbeat of 30 minutes may open the heartbeat file and a route node may trigger paths based on if the heartbeat text contains certain phrases, therefore every 30 minutes, you can run specific pathways. Or you could have it send the heartbeat text to an LLM and ask if any of these should trigger a tool call.

When to use:
Use for periodic self-improvement, daily workflow review, scheduled memory consolidation, recurring tool checks, and heartbeat status reports.

Agent hints:
For "run every", "daily", "scheduled", "periodic", "autonomous", or "timer", retrieve `Timer_Node`, `Text_Gate`, `Timestamp`, and `File_Write`.

---CHUNK_BREAK---

## JSON Memory State Pattern

Pattern Name:
JSON Memory State

Goal:
Maintain a persistent structured memory file that an agent can read, update, and save.

Typical Node Chain:
File_Read -> JSON_Cleaner -> JSON_Read / JSON_Edit / JSON_Append / JSON_insert_key / JSON_Remove_Entry -> File_Write.

How it works:
Read the memory file with `File_Read`. Clean or normalize it with `JSON_Cleaner`. Extract fields with `JSON_Read`, append new events with `JSON_Append`, edit existing state with `JSON_Edit`, insert new ordered sections with `JSON_insert_key`, and remove stale entries with `JSON_Remove_Entry`. Save the updated JSON with `File_Write`. Handy for Short Term Memory (STM), removing the oldest entry, and using the oldest entry to maybe update a STM summary or maybe adding some insight from it into LTM. It's best to use an LLM to construct the memory JSON clean it, and append it, and a harness to remove the oldest entry and to feed it into another LLM for potentially constructing the STM sumary or LTM.

When to use:
Use for agent memory, improvement history, workflow metadata, action queues, run logs, persistent configuration, and task state.

Agent hints:
For "memory", "state file", "update JSON", "append history", "persist plan", retrieve the JSON operation nodes plus `File_Read` and `File_Write`.

---CHUNK_BREAK---

## Token Budget Pattern

Pattern Name:
Token Budget Check

Goal:
Estimate prompt size and route, gate, or chunk before calling an LLM.

Typical Node Chain:
File_Read -> Text_Gate / Route / -> Prompt_Combine -> Token_Estimator -> easy compare -> LLMCall -> Token_Estimator -> File_Write.



How it works:
Use `Token_Estimator` to produce a rough token estimate. Use `easy compare` to compare the estimate against a threshold. If too large, route to `Chunk_Splitter` or a summarization path. If within budget, pass directly to `LLMCall`. This is heuristic and should be used for control flow, not exact billing or model-token accounting. This allows you to control your token use. You can ensure prompts are always ecconomical, and you can audit the token useage to a rough amount of accuracy. No more worry about 30,000 token prompts being sent to an LLM API and using up all your token limit. Aditionally, you can set limits on Token usage so that a certain task can use up a certain amount of your token limit while leaving space for other more essential tasks to have token limit always available. You can also set the limit of total token use so that the agent will stop before it goes over an estimated cost, meaning a runaway loop won't accidently cost thousands.

When to use:
Use before large LLM calls, RAG prompt assembly, long file ingestion, comparing to total token allocation, limiting tasks to certain token allocation limits, and recursive summarization.

Agent hints:
For "too long", "context limit", "token budget", "split if large", or "estimate size", retrieve `Token_Estimator`, `easy compare`, and `Chunk_Splitter`.

---CHUNK_BREAK---

## Human Debugging Pattern

Pattern Name:
Human Debugging And Inspection

Goal:
Make agentic workflows understandable and quick to inspect.

Typical Node Chain:
Any important node output -> PreviewAny.
Any important constant -> PrimitiveString.
Any risky action -> easy blocker.

How it works:
Place `PreviewAny` on important outputs while developing, especially `error_string`, LLM responses, cleaned JSON, routed branches, tool results, and terminal text. Use `PrimitiveString` for visible constants instead of burying them inside large widgets. Use `easy blocker` before nodes that write files, call tools, or run shell commands to block the workflow branch if potentially undesireable content is found in the passed text.

When to use:
Use while building, debugging, reviewing, and improving workflows. This pattern is what makes autonomous self-improvement inspectable in minutes instead of opaque.

Agent hints:
For "debug", "inspect", "show result", "make readable", "manual checkpoint", retrieve `PreviewAny`, `PrimitiveString`, and `easy blocker`.


