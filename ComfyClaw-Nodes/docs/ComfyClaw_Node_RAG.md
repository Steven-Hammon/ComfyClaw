# ComfyClaw Node RAG Reference

Purpose:
This document is written for retrieval-augmented agents that need to understand which ComfyClaw and supporting ComfyUI nodes to use when designing, improving, or explaining an agentic ComfyUI workflow.

Scope:
The ComfyClaw nodes are implemented in this repository. The helper nodes are included because they are valuable in ComfyClaw workflows, but they come from existing external node packs such as ComfyUI core and EasyUse.

Important workflow JSON note:
The example file `Example_Workflows/All_Nodes.json` is saved ComfyUI UI workflow JSON. It is not the smaller API prompt JSON format. In UI workflow JSON, each node has a `type`, `inputs`, `outputs`, `widgets_values`, and metadata in `properties`. Connected inputs use numeric `link` ids; unconnected widget values appear in `widgets_values`.

General ComfyClaw conventions:
- Exact node type names matter. Use the names in this document exactly.
- Most ComfyClaw nodes return an `error_string` output instead of crashing the graph.
- Empty `error_string` means normal success.
- Provider sockets such as `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, and `MCP_PROVIDER` carry provider objects, not plain strings.
- JSON key paths use dot-separated paths such as `scene.title`, `items.0.name`, or `a.0`.
- Dynamic input nodes can expose up to 20 optional inputs.

---CHUNK_BREAK---

## Prompt_Combine

Node Name:
Prompt_Combine

Internal processing description:
Combines multiple string fragments into one continuous string. It starts with required `text_1`, then collects optional dynamic inputs named `text_2`, `text_3`, and so on in numeric order. It does not insert spaces, newlines, commas, or separators automatically. Every provided input must already be a string. If any input is not a string, the node returns an empty `combined_string` and an explanatory `error_string`.

Inputs:
- `text_1`: STRING. Required first text fragment.
- `text_2` through `text_20`: STRING. Optional dynamic fragments.

Outputs:
- `combined_string`: STRING. All text fragments joined directly.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
PrimitiveString, File_Read, JSON_Read, Embedding_Query, Timestamp, Random_from_List, String_Find_Replace, LLMCall, MCP_Call, Exec, File_Write.

When to use the Node:
Use when assembling a prompt, command, file path, JSON fragment, or tool-call string from smaller parts. It is the main prompt construction node before `LLMCall`.

How it's used in a ComfyUI Json:
- `type`: `Prompt_Combine`.
- Widget order: `text_1`, then dynamic `text_2`, `text_3`, etc.
- Dynamic UI state may appear under `properties.comfyclaw_dynamic_state.texts`.
- Link any upstream string into a `text_N` input socket, or store literal text in `widgets_values`.

Keywords:
combine prompt, concatenate, join strings, merge text, append context, prepend instructions, prompt builder.

---CHUNK_BREAK---

## Text_Gate

Node Name:
Text_Gate

Internal processing description:
Allows or blocks a string using simple match rules. Rules can use `contains`, `equals`, `starts_with`, or `ends_with`. Empty rule text is ignored. When `mode` is false, the node is in deny mode: matching text is blocked and non-matching text passes. When `mode` is true, the node is in allow mode: matching text passes and non-matching text is blocked. `use_override` can replace the passed output with `override_text` for matching cases. `is_match` reports whether any rule matched.

Inputs:
- `input_string`: STRING. Text to test.
- `mode`: BOOLEAN. False means deny matched text; true means allow matched text.
- `override_text`: STRING. Replacement output when override is used.
- `use_override`: BOOLEAN. Enables override behavior.
- `rule_1_type` through `rule_20_type`: COMBO. Optional dynamic match type.
- `rule_1_text` through `rule_20_text`: STRING. Optional dynamic match text.

Outputs:
- `string_output`: STRING. Passed original text, override text, or empty string.
- `error_string`: STRING. Validation error or empty string.
- `is_match`: BOOLEAN. True when any rule matched.

A selection of other Nodes they are often used with:
Route, StringCompare, easy blocker, LLMCall, Exec, File_Write, PreviewAny.

When to use the Node:
Use for safety checks, keyword filters, simple pass/block control, suppressing empty or unsafe downstream actions, and routing based on whether output contains markers.

How it's used in a ComfyUI Json:
- `type`: `Text_Gate`.
- Core widget order: `input_string`, `mode`, `override_text`, `use_override`.
- Dynamic rule widgets are pairs such as `rule_1_type`, `rule_1_text`.
- Dynamic UI state may appear under `properties.comfyclaw_dynamic_state.rules`.

Keywords:
gate, block text, allow if, deny if, safety filter, keyword check, conditional pass, matched boolean.

---CHUNK_BREAK---

## Route

Node Name:
Route

Internal processing description:
Routes one string to up to 20 branch outputs. Each dynamic branch has a match type and rule text. If a branch rule matches, the full original `input_string` is copied to that branch output. Multiple branches can receive the same string if multiple rules match. If no branch matches and `default_branch` is between 1 and 20, the input is copied to that default branch. Empty branch rules are ignored.

Inputs:
- `input_string`: STRING. Text to route.
- `default_branch`: INT. Branch number to use when no rule matches, or 0 for no default.
- `branch_1_type` through `branch_20_type`: COMBO. Optional dynamic match type.
- `branch_1_rule` through `branch_20_rule`: STRING. Optional dynamic branch rule.

Outputs:
- `branch_1` through `branch_20`: STRING. Matching branch outputs receive the input string; others are empty.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
Text_Gate, LLMCall, JSON_Cleaner, JSON_Read, File_Write, Exec, MCP_Call, PreviewAny.

When to use the Node:
Use when one text value can lead to multiple downstream paths, such as classifying an LLM response into `write`, `execute`, `ask`, `search`, or `done`.

How it's used in a ComfyUI Json:
- `type`: `Route`.
- Core widget order: `input_string`, `default_branch`, then dynamic branch widgets.
- Dynamic branch widgets are pairs such as `branch_1_type`, `branch_1_rule`.
- Dynamic UI state may appear under `properties.comfyclaw_dynamic_state.branches`.

Keywords:
route, branch, choose action, classify response, send to branch, default branch, multi-path control.

---CHUNK_BREAK---

## String_Find_Replace

Node Name:
String_Find_Replace

Internal processing description:
Replaces every occurrence of `find_text` in `string_input` with `replace_text`. The node decodes common escaped sequences in `find_text` and `replace_text`: `\n`, `\r`, `\r\n`, and `\t`. Replacement is literal substring replacement, not regex. `find_text` cannot be empty.

Inputs:
- `string_input`: STRING. Source text.
- `find_text`: STRING. Literal text to find.
- `replace_text`: STRING. Literal replacement text.

Outputs:
- `output_string`: STRING. Text after replacements.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
Prompt_Combine, Text_Cleaner, JSON_Cleaner, LLMCall, File_Read, File_Write.

When to use the Node:
Use for deterministic cleanup, marker normalization, placeholder replacement, newline conversion, removing unwanted text, or shaping LLM output before JSON parsing.

How it's used in a ComfyUI Json:
- `type`: `String_Find_Replace`.
- Widget order: `string_input`, `find_text`, `replace_text`.
- Use escaped sequences such as `\\n` in widget values when matching literal newlines.

Keywords:
find replace, replace substring, remove marker, normalize newline, template placeholder, deterministic text edit.

---CHUNK_BREAK---

## File_Read

Node Name:
File_Read

Internal processing description:
Reads raw text from a file path. Relative paths resolve against the current working directory of the ComfyUI process, and `~` is expanded. The node validates that the path exists and is a file. It attempts UTF-8, UTF-8 with BOM, and the system preferred encoding. It is always treated as changed so external edits to the file are picked up.

Inputs:
- `file_path`: STRING. Absolute or relative path to a text file.

Outputs:
- `file_text`: STRING. File contents.
- `error_string`: STRING. Filesystem or validation error, or empty string.

A selection of other Nodes they are often used with:
Text_Cleaner, JSON_Cleaner, Chunk_Splitter, Embedding, LLMCall, Prompt_Combine, PreviewAny.

When to use the Node:
Use to load instructions, memory, previous outputs, RAG source text, JSON state, tool schemas, workflow files, or any local text document.

How it's used in a ComfyUI Json:
- `type`: `File_Read`.
- Widget order: `file_path`.
- The path can be literal in `widgets_values` or linked from `Prompt_Combine` or `PrimitiveString`.

Keywords:
read file, load file, load memory, read docs, read workflow, import text, load JSON, external state.

---CHUNK_BREAK---

## File_Write

Node Name:
File_Write

Internal processing description:
Writes `text_input` to `file_path` using UTF-8. Relative paths resolve against the current ComfyUI working directory, and `~` is expanded. The parent directory must already exist. `mode` is either `overwrite` or `append`. On success, the node returns `success_text` as `output_text`; it does not automatically echo the written text. The node is marked as an output node and is always treated as changed.

Inputs:
- `file_path`: STRING. Target file path.
- `text_input`: STRING. Text to write.
- `mode`: COMBO. `overwrite` or `append`.
- `success_text`: STRING. Text emitted after successful write.

Outputs:
- `output_text`: STRING. The configured success text.
- `error_string`: STRING. Filesystem or validation error, or empty string.

A selection of other Nodes they are often used with:
LLMCall, JSON_Cleaner, JSON_Edit, JSON_Append, Timestamp, Prompt_Combine, MCP_Call, Exec.

When to use the Node:
Use to persist generated reports, workflow JSON, agent memory, logs, tool results, RAG bundles, or state snapshots.

How it's used in a ComfyUI Json:
- `type`: `File_Write`.
- Widget order: `file_path`, `text_input`, `mode`, `success_text`.
- `OUTPUT_NODE = True`; ComfyUI treats it as an output node.

Keywords:
write file, save output, persist memory, append log, overwrite state, save workflow, export result.

---CHUNK_BREAK---

## Text_Cleaner

Node Name:
Text_Cleaner

Internal processing description:
Extracts a section of text between `start_text` and `end_text`. Escaped marker text such as `\\n` and `\\t` is decoded before matching. If `start_text` is empty, extraction begins at the start; if `end_text` is empty, extraction ends at the end. `include_start_end` controls whether markers are included. If markers are missing, the node repairs boundaries and reports warnings in `error_string`.

Inputs:
- `string_input`: STRING. Source text.
- `start_text`: STRING. Start marker.
- `end_text`: STRING. End marker.
- `include_start_end`: BOOLEAN. Include or exclude markers in output.

Outputs:
- `output_string`: STRING. Extracted section.
- `error_string`: STRING. Warnings or validation error, or empty string.

A selection of other Nodes they are often used with:
File_Read, LLMCall, JSON_Cleaner, String_Find_Replace, Prompt_Combine, File_Write.

When to use the Node:
Use to pull a marked section from a file, LLM response, markdown document, prompt template, or generated workflow.

How it's used in a ComfyUI Json:
- `type`: `Text_Cleaner`.
- Widget order: `string_input`, `start_text`, `end_text`, `include_start_end`.
- Use escaped newline markers in `widgets_values` when matching multi-line boundaries.

Keywords:
extract between markers, isolate block, trim response, remove wrapper, get tagged text, parse fenced output.

---CHUNK_BREAK---

## JSON_Cleaner

Node Name:
JSON_Cleaner

Internal processing description:
Extracts and repairs a JSON object from messy text. It takes the candidate from the first `{` to the last `}`. It tries direct parsing first, then repairs common LLM formatting problems: markdown code fences, curly quotes, invalid control characters, trailing commas, repeated commas, and likely missing line commas. It returns pretty JSON. It extracts objects, not bare arrays.

Inputs:
- `string_input`: STRING. Text that may contain a JSON object.

Outputs:
- `json_string`: STRING. Cleaned JSON object string, or `{}` on failure.
- `error_string`: STRING. Parse/repair message or empty string.

A selection of other Nodes they are often used with:
LLMCall, Text_Cleaner, String_Find_Replace, JSON_Read, JSON_Edit, JSON_Append, JSON_insert_key, JSON_Remove_Entry, JSON_Count_keys, File_Write.

When to use the Node:
Use after `LLMCall` when the model is expected to return JSON, or after `File_Read` when a file contains JSON embedded in prose.

How it's used in a ComfyUI Json:
- `type`: `JSON_Cleaner`.
- Widget order: `string_input`.
- Common connection: `LLMCall.response_text` to `JSON_Cleaner.string_input`.

Keywords:
clean JSON, extract JSON, repair JSON, parse LLM JSON, remove code fence, structured output.

---CHUNK_BREAK---

## JSON_Count_keys

Node Name:
JSON_Count_keys

Internal processing description:
Parses `json_input` and counts only the keys on the root JSON object. It does not count nested keys. The root value must be a JSON object; arrays, strings, numbers, booleans, and null return an error. The count follows the parsed object key order, which matters when paired with index-based JSON operations.

Inputs:
- `json_input`: STRING. JSON object text.

Outputs:
- `key_count`: INT. Number of root keys.
- `error_string`: STRING. Validation or parse error, or empty string.

A selection of other Nodes they are often used with:
JSON_Cleaner, JSON_Read, JSON_insert_key, JSON_Remove_Entry, Route, Token_Estimator.

When to use the Node:
Use when an agent needs to iterate over root object entries, check whether a JSON plan has items, or calculate an ordered insertion/removal position.

How it's used in a ComfyUI Json:
- `type`: `JSON_Count_keys`.
- Widget order: `json_input`.
- Connect clean JSON from `JSON_Cleaner` or `File_Read`.

Keywords:
count JSON keys, root key count, object length, ordered keys, iterate JSON object.

---CHUNK_BREAK---

## JSON_Read

Node Name:
JSON_Read

Internal processing description:
Reads a value from parsed JSON by dot-separated key path or by ordered object index. In `key_path` mode, `key_path` must be non-empty and can address nested objects and arrays, such as `items.0.title`. In `index` mode, `key_path` selects the object to index; an empty path targets the root object. The node returns both plain text and JSON serialization of the selected value.

Inputs:
- `json_input`: STRING. JSON text.
- `key_path`: STRING. Dot-separated path. Empty is allowed only for root access in `index` mode.
- `index`: INT. Ordered key index used in `index` mode.
- `read_mode`: COMBO. `key_path` or `index`.

Outputs:
- `value_text`: STRING. Plain text representation of the selected value.
- `value_json`: STRING. JSON serialized representation of the selected value.
- `error_string`: STRING. Parse/path error, or empty string.

A selection of other Nodes they are often used with:
JSON_Cleaner, JSON_Count_keys, Prompt_Combine, LLMCall, Route, File_Write, StringCompare.

When to use the Node:
Use to extract actions, arguments, file paths, prompt sections, tool names, result fields, memory values, or individual plan steps from structured JSON.

How it's used in a ComfyUI Json:
- `type`: `JSON_Read`.
- Widget order: `json_input`, `key_path`, `index`, `read_mode`.
- Use `value_text` for prompt/string workflows and `value_json` for downstream JSON editing.

Keywords:
read JSON field, get key, extract value, lookup path, get action, get arguments, index object.

---CHUNK_BREAK---

## JSON_Append

Node Name:
JSON_Append

Internal processing description:
Appends `value_text` to a JSON array at `key_path`. If the target object key does not exist, it creates a new array containing the value. If the target exists but is not an array, the operation fails. `value_text` is parsed as JSON when possible, so numbers, booleans, arrays, and objects keep their JSON types; otherwise it remains a string. The path must end in an object key, not an array index.

Inputs:
- `json_input`: STRING. JSON text.
- `key_path`: STRING. Dot-separated path to an object key whose value should be an array.
- `value_text`: STRING. Value to append, parsed as JSON if possible.

Outputs:
- `json_string`: STRING. Updated JSON on success; often original JSON on error.
- `error_string`: STRING. Parse/path/type error, or empty string.

A selection of other Nodes they are often used with:
JSON_Cleaner, JSON_Read, JSON_Edit, JSON_Remove_Entry, File_Read, File_Write, LLMCall.

When to use the Node:
Use to add messages, observations, tool results, critique notes, memory entries, candidate improvements, or action history items to a JSON array.

How it's used in a ComfyUI Json:
- `type`: `JSON_Append`.
- Widget order: `json_input`, `key_path`, `value_text`.
- `key_path` cannot be empty and cannot end with an array index.

Keywords:
append JSON, add to array, push item, add memory entry, add log event, accumulate results.

---CHUNK_BREAK---

## JSON_Edit

Node Name:
JSON_Edit

Internal processing description:
Replaces an existing value at `key_path` in parsed JSON. The target key or array index must already exist. `value_text` cannot be empty and is parsed as JSON when possible. If the path is missing, the parent type is wrong, or the array index is out of range, the node returns the original JSON with an error.

Inputs:
- `json_input`: STRING. JSON text.
- `key_path`: STRING. Dot-separated path to an existing key or array index.
- `value_text`: STRING. Replacement value, parsed as JSON if possible.

Outputs:
- `json_string`: STRING. Updated JSON on success.
- `error_string`: STRING. Parse/path/type error, or empty string.

A selection of other Nodes they are often used with:
JSON_Cleaner, JSON_Read, JSON_Append, JSON_Remove_Entry, JSON_insert_key, File_Write, LLMCall.

When to use the Node:
Use to update an existing agent state field, replace a plan step, change a config value, store a selected action, or overwrite a memory property.

How it's used in a ComfyUI Json:
- `type`: `JSON_Edit`.
- Widget order: `json_input`, `key_path`, `value_text`.
- Use quoted JSON strings such as `"ready"` when you need the replacement to remain a JSON string.

Keywords:
edit JSON, replace value, update state, set existing key, overwrite field, modify config.

---CHUNK_BREAK---

## JSON_insert_key

Node Name:
JSON_insert_key

Internal processing description:
Inserts a new root-level key into an ordered JSON object before or after another root key. The insertion target can be selected by `key_path` or by root-key `index`. Nested-looking paths are coerced to object keys, but ordering is applied at the root. For example, `new_key_path` of `chapter.word_1` creates root key `chapter` with value `{"word_1": value}`. The root JSON must be an object, and the new root key must not already exist.

Inputs:
- `json_input`: STRING. JSON object text.
- `key_path`: STRING. Existing key path used to locate neighboring root key in `key_path` mode.
- `index`: INT. Existing root key index used in `index` mode.
- `new_key_path`: STRING. New key path to insert.
- `value_text`: STRING. New value, parsed as JSON if possible.
- `mode`: COMBO. `before` or `after`.
- `insert_mode`: COMBO. `key_path` or `index`.

Outputs:
- `json_string`: STRING. Updated ordered JSON object.
- `error_string`: STRING. Parse/path/duplicate-key error, or empty string.

A selection of other Nodes they are often used with:
JSON_Cleaner, JSON_Count_keys, JSON_Read, JSON_Edit, JSON_Remove_Entry, Timestamp, File_Write.

When to use the Node:
Use when adding a new ordered section, inserting a workflow step before/after another step, preserving readable JSON order, or adding a nested object under a new root key.

How it's used in a ComfyUI Json:
- `type`: `JSON_insert_key`.
- Widget order: `json_input`, `key_path`, `index`, `new_key_path`, `value_text`, `mode`, `insert_mode`.
- Exact casing matters: the type is `JSON_insert_key`, not `JSON_Insert_Key`.

Keywords:
insert key, add ordered JSON key, insert before, insert after, new root key, ordered plan.

---CHUNK_BREAK---

## JSON_Remove_Entry

Node Name:
JSON_Remove_Entry

Internal processing description:
Deletes a key or array entry from parsed JSON. In `key_path` mode, `key_path` identifies the object key or array index to delete. In `index` mode, `key_path` selects an object, or the root object if empty, and `index` selects which ordered key to remove from that object. If the path or index is missing, the original JSON is returned with an error.

Inputs:
- `json_input`: STRING. JSON text.
- `key_path`: STRING. Dot-separated path. Required in `key_path` mode; optional in `index` mode.
- `index`: INT. Ordered object key index used in `index` mode.
- `remove_mode`: COMBO. `key_path` or `index`.

Outputs:
- `json_string`: STRING. Updated JSON on success.
- `error_string`: STRING. Parse/path/type error, or empty string.

A selection of other Nodes they are often used with:
JSON_Cleaner, JSON_Read, JSON_Count_keys, JSON_Edit, JSON_insert_key, File_Write.

When to use the Node:
Use to prune stale memory, remove completed work items, delete bad tool results, drop a plan step, or delete a JSON array item.

How it's used in a ComfyUI Json:
- `type`: `JSON_Remove_Entry`.
- Widget order: `json_input`, `key_path`, `index`, `remove_mode`.
- Use `remove_mode=index` when deleting an ordered root or nested-object key by position.

Keywords:
remove JSON, delete key, delete array item, prune memory, remove plan step, drop entry.

---CHUNK_BREAK---

## Chunk_Splitter

Node Name:
Chunk_Splitter

Internal processing description:
Splits long text into bounded chunks with optional overlap. It has three configuration groups: main chunk, chunk limit, and chunk overlap. Split types are `characters`, `words`, `paragraphs`, and `custom`. Custom splitting uses up to five marker strings. The main chunk group chooses the initial chunk unit count. The limit group enforces minimum and maximum size in its own unit. The overlap group takes a prefix from the following text and appends it to the current chunk for context. Output is returned both as break-delimited text and as a JSON list.

Inputs:
- `input_text`: STRING. Text to split.
- `main_chunk_min`: INT. Desired number of main split units.
- `main_chunk_split_type`: COMBO. `characters`, `words`, `paragraphs`, or `custom`.
- `main_chunk_marker_1` through `main_chunk_marker_5`: STRING. Custom main markers.
- `chunk_limit_min`: INT. Minimum chunk size in limit units.
- `chunk_limit_max`: INT. Maximum chunk size in limit units.
- `chunk_limit_split_type`: COMBO. Unit used for limit checking.
- `chunk_limit_marker_1` through `chunk_limit_marker_5`: STRING. Custom limit markers.
- `chunk_overlap_min`: INT. Number of overlap units from the next chunk.
- `chunk_overlap_split_type`: COMBO. Unit used for overlap.
- `chunk_overlap_marker_1` through `chunk_overlap_marker_5`: STRING. Custom overlap markers.

Outputs:
- `chunks_text`: STRING. Chunks joined with `---CHUNK_BREAK---`.
- `chunks_json`: STRING. JSON array of chunk strings.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
File_Read, Text_Cleaner, Embedding, Token_Estimator, Prompt_Combine, File_Write, PreviewAny.

When to use the Node:
Use before embedding, summarization, or long-context LLM work. It is especially useful for RAG source preparation and documentation chunking.

How it's used in a ComfyUI Json:
- `type`: `Chunk_Splitter`.
- Widget order is exactly the input order listed above.
- Connect `chunks_json` to `Embedding.chunk_input` with `input_format=json_list`.
- Connect `chunks_text` to `Embedding.chunk_input` with `input_format=break_string`.

Keywords:
chunk text, split document, make RAG chunks, chunk overlap, paragraph chunks, custom markers.

---CHUNK_BREAK---

## Load_Embedding_Model

Node Name:
Load_Embedding_Model

Internal processing description:
Creates an `EMBEDDING_PROVIDER` for a local Ollama embedding model. The base URL is fixed to `http://127.0.0.1:11434`. The node validates that `model_name` is a non-empty string and stores provider configuration with `provider_kind` set to `ollama`. It does not make an embedding request by itself.

Inputs:
- `model_name`: STRING. Local Ollama embedding model name.

Outputs:
- `embedding_provider`: EMBEDDING_PROVIDER. Provider object for embedding nodes.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
Embedding, Embedding_Query, Chunk_Splitter, File_Read.

When to use the Node:
Use when embeddings should be generated locally with Ollama instead of a remote API.

How it's used in a ComfyUI Json:
- `type`: `Load_Embedding_Model`.
- Widget order: `model_name`.
- Link output `embedding_provider` into `Embedding.embedding_provider` or `Embedding_Query.embedding_provider`.

Keywords:
local embeddings, Ollama embeddings, embedding model, RAG provider, load embedding model.

---CHUNK_BREAK---

## Load_Embedding_API

Node Name:
Load_Embedding_API

Internal processing description:
Creates an `EMBEDDING_PROVIDER` for an OpenAI-compatible remote embeddings API. It validates `api_base_url`, `api_key`, and `model_name` as non-empty strings and checks that the URL is HTTP or HTTPS. The base URL is normalized by removing trailing slashes. It stores provider configuration with `provider_kind` set to `api`.

Inputs:
- `api_base_url`: STRING. Default `https://api.openai.com/v1`.
- `api_key`: STRING. API key.
- `model_name`: STRING. Embedding model name.

Outputs:
- `embedding_provider`: EMBEDDING_PROVIDER. Provider object.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
Embedding, Embedding_Query, Chunk_Splitter, File_Read.

When to use the Node:
Use when embeddings should be created by a remote OpenAI-compatible API.

How it's used in a ComfyUI Json:
- `type`: `Load_Embedding_API`.
- Widget order: `api_base_url`, `api_key`, `model_name`.
- Link output `embedding_provider` into embedding nodes.

Keywords:
remote embeddings, API embeddings, OpenAI-compatible embeddings, embedding provider.

---CHUNK_BREAK---

## Embedding

Node Name:
Embedding

Internal processing description:
Embeds a list of text chunks using an `EMBEDDING_PROVIDER`. For Ollama, it tries `/api/embed` and falls back to `/api/embeddings`. For API providers, it posts to `{api_base_url}/embeddings` with bearer authentication. `chunk_input` can be a JSON array of strings or a break-delimited string. Empty chunks are skipped. The output bundle is JSON containing `model_name`, `provider_kind`, `chunks`, and `embeddings`.

Inputs:
- `embedding_provider`: EMBEDDING_PROVIDER. From `Load_Embedding_Model` or `Load_Embedding_API`.
- `chunk_input`: STRING. JSON array or break-delimited text.
- `input_format`: COMBO. `json_list` or `break_string`.
- `chunk_break_marker`: STRING. Delimiter used in `break_string` mode.

Outputs:
- `embedding_bundle_string`: STRING. JSON bundle containing chunks and vectors.
- `error_string`: STRING. Parse/request error or empty string.

A selection of other Nodes they are often used with:
Load_Embedding_Model, Load_Embedding_API, Chunk_Splitter, File_Read, File_Write, Embedding_Query.

When to use the Node:
Use to create a reusable RAG bundle from docs, workflow references, memory, or design requirements.

How it's used in a ComfyUI Json:
- `type`: `Embedding`.
- Widget order after linked provider: `chunk_input`, `input_format`, `chunk_break_marker`.
- Link `embedding_provider` from an embedding loader.
- Use `chunks_json` from `Chunk_Splitter` with `input_format=json_list`.

Keywords:
embed chunks, create RAG index, embedding bundle, vectorize docs, store embeddings.

---CHUNK_BREAK---

## Embedding_Query

Node Name:
Embedding_Query

Internal processing description:
Searches an embedding bundle with cosine similarity. It embeds `query_text` with the supplied provider, validates that the provider model matches the bundle model, compares the query vector to stored chunk vectors, sorts by descending similarity, and returns the top results. It also returns the best chunk directly as text.

Inputs:
- `embedding_provider`: EMBEDDING_PROVIDER. Same model/provider family used to create the bundle.
- `embedding_bundle_string`: STRING. JSON bundle from `Embedding`.
- `query_text`: STRING. Search query.
- `top_k`: INT. Number of results to return.
- `timeout`: INT. Timeout for query embedding request.

Outputs:
- `results_json_string`: STRING. JSON object containing ranked results.
- `best_chunk_text`: STRING. Highest scoring chunk text.
- `error_string`: STRING. Bundle/query error or empty string.

A selection of other Nodes they are often used with:
Load_Embedding_Model, Load_Embedding_API, Embedding, File_Read, Prompt_Combine, LLMCall, PreviewAny.

When to use the Node:
Use when an agent needs relevant documentation, memory, design notes, or workflow context for the current question.

How it's used in a ComfyUI Json:
- `type`: `Embedding_Query`.
- Widget order after provider and bundle: `query_text`, `top_k`, `timeout`.
- Connect `best_chunk_text` or `results_json_string` into `Prompt_Combine` before `LLMCall`.

Keywords:
query embeddings, retrieve chunk, RAG search, semantic search, best chunk, top k.

---CHUNK_BREAK---

## LLM_API_Loader

Node Name:
LLM_API_Loader

Internal processing description:
Creates an `LLM_PROVIDER` for an OpenAI-compatible chat completions API. It validates `api_base_url` and `model_name` as non-empty strings and validates the URL. `api_key` may be empty, which supports local OpenAI-compatible servers without authentication. The base URL is normalized by removing trailing slashes.

Inputs:
- `api_base_url`: STRING. Default `https://api.openai.com/v1`.
- `api_key`: STRING. Optional bearer token.
- `model_name`: STRING. Chat model name.

Outputs:
- `llm_provider`: LLM_PROVIDER. Provider object for `LLMCall`.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
LLMCall, Prompt_Combine, Embedding_Query, JSON_Cleaner.

When to use the Node:
Use when the workflow should call a remote or OpenAI-compatible chat API.

How it's used in a ComfyUI Json:
- `type`: `LLM_API_Loader`.
- Widget order: `api_base_url`, `api_key`, `model_name`.
- Link `llm_provider` into `LLMCall.llm_provider`.

Keywords:
load LLM API, OpenAI-compatible LLM, remote chat model, API provider.

---CHUNK_BREAK---

## LLM_Model_Loader

Node Name:
LLM_Model_Loader

Internal processing description:
Creates an `LLM_PROVIDER` for local Ollama generation. It validates `ollama_base_url` and `model_name` as non-empty strings and checks that the URL is HTTP or HTTPS. It stores provider configuration with `provider_kind` set to `ollama` and an empty API key.

Inputs:
- `ollama_base_url`: STRING. Default `http://127.0.0.1:11434`.
- `model_name`: STRING. Local Ollama model name.

Outputs:
- `llm_provider`: LLM_PROVIDER. Provider object for `LLMCall`.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
LLMCall, Prompt_Combine, Embedding_Query, JSON_Cleaner.

When to use the Node:
Use when the workflow should call a local Ollama model.

How it's used in a ComfyUI Json:
- `type`: `LLM_Model_Loader`.
- Widget order: `ollama_base_url`, `model_name`.
- Link `llm_provider` into `LLMCall.llm_provider`.

Keywords:
local LLM, Ollama model, load local model, local generation.

---CHUNK_BREAK---

## LLMCall

Node Name:
LLMCall

Internal processing description:
Sends `user_prompt` to an `LLM_PROVIDER` and returns text. For Ollama providers, it posts to `/api/generate` with `stream: false`, `temperature`, and `num_predict`. For API providers, it posts to `/chat/completions` with one user message, `temperature`, and `max_tokens`. If the provider has an API key, it is sent as a bearer token. The node extracts plain message text from OpenAI-compatible responses. It is always treated as changed so calls can run repeatedly.

Inputs:
- `llm_provider`: LLM_PROVIDER. From `LLM_API_Loader` or `LLM_Model_Loader`.
- `user_prompt`: STRING. Prompt text. Must not be empty.
- `temperature`: FLOAT. Sampling temperature.
- `max_output_tokens`: INT. Maximum output tokens.
- `timeout_seconds`: FLOAT. Request timeout.

Outputs:
- `response_text`: STRING. Model response text.
- `error_string`: STRING. Request/validation error or empty string.

A selection of other Nodes they are often used with:
LLM_API_Loader, LLM_Model_Loader, Prompt_Combine, Embedding_Query, JSON_Cleaner, Text_Gate, Route, MCP_Call, File_Write, PreviewAny.

When to use the Node:
Use for reasoning, planning, critique, workflow improvement, JSON generation, prompt rewriting, tool-call planning, summarization, and natural language generation.

How it's used in a ComfyUI Json:
- `type`: `LLMCall`.
- Widget order after linked provider: `user_prompt`, `temperature`, `max_output_tokens`, `timeout_seconds`.
- Link provider output from either LLM loader into `llm_provider`.

Keywords:
call LLM, ask model, generate response, reason, critique, plan, brainstorm, produce JSON.

---CHUNK_BREAK---

## Token_Estimator

Node Name:
Token_Estimator

Internal processing description:
Estimates token count from word count. It counts non-whitespace word-like spans and multiplies by `ratio`, then rounds to an integer. The default ratio is 1.3. This is a heuristic, not a tokenizer-accurate model count. If `input_text` is not a string, it returns zero counts without an error. If `ratio` is non-numeric or not greater than zero, it returns an error.

Inputs:
- `input_text`: STRING. Text to estimate.
- `ratio`: FLOAT. Word-to-token multiplier.

Outputs:
- `token_estimate_int`: INT. Rounded token estimate.
- `token_estimate_string`: STRING. Token estimate as text.
- `word_count_string`: STRING. Word count as text.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
File_Read, Prompt_Combine, Chunk_Splitter, LLMCall, Text_Gate, PreviewAny.

When to use the Node:
Use when deciding whether a prompt, document, retrieved chunk, or accumulated memory is likely too large for an LLM call.

How it's used in a ComfyUI Json:
- `type`: `Token_Estimator`.
- Widget order: `input_text`, `ratio`.
- Use the integer output for numeric comparisons only if a compatible comparison node is available.

Keywords:
token estimate, word count, prompt size, context budget, chunk sizing, too long check.

---CHUNK_BREAK---

## Timestamp

Node Name:
Timestamp

Internal processing description:
Returns the current local system timestamp. `iso` returns an ISO timestamp with timezone and no microseconds. `human` returns a readable date/time string. `unix` returns integer seconds since Unix epoch as text. The node is always treated as changed so the timestamp updates each run.

Inputs:
- `format`: COMBO. `iso`, `human`, or `unix`.

Outputs:
- `timestamp_string`: STRING. Current timestamp in the selected format.
- `error_string`: STRING. Clock/system error or empty string.

A selection of other Nodes they are often used with:
Prompt_Combine, File_Write, JSON_insert_key, JSON_Edit, Random_from_List, PreviewAny.

When to use the Node:
Use for audit logs, filenames, memory entries, workflow improvement reports, generated JSON, or time-aware prompts.

How it's used in a ComfyUI Json:
- `type`: `Timestamp`.
- Widget order: `format`.
- Feed `timestamp_string` into `Prompt_Combine`, `File_Write`, or JSON value fields.

Keywords:
timestamp, current time, dated log, file suffix, audit trail, run time, now.

---CHUNK_BREAK---

## Random_from_List

Node Name:
Random_from_List

Internal processing description:
Selects one non-empty string from `text_1` and optional dynamic text inputs. Selection is deterministic: it uses `seed % number_of_non_empty_values`. Empty strings are skipped, but whitespace-only strings count as non-empty. All provided values must be strings. The node is considered changed when the seed changes.

Inputs:
- `text_1`: STRING. Required first candidate.
- `text_2` through `text_20`: STRING. Optional dynamic candidates.
- `seed`: INT. Deterministic selection seed.

Outputs:
- `string_output`: STRING. Selected candidate string.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
Prompt_Combine, LLMCall, Route, Text_Gate, File_Write, PrimitiveString.

When to use the Node:
Use to vary prompts, choose among strategies, rotate critique lenses, select canned actions, or introduce deterministic variation into an agent loop.

How it's used in a ComfyUI Json:
- `type`: `Random_from_List`.
- Core inputs include `text_1` and `seed`; dynamic text rows are `text_2`, `text_3`, etc.
- Dynamic UI state may appear under `properties.comfyclaw_dynamic_state.texts`.
- Some saved workflows include button serialization artifacts; agents should focus on actual text sockets and seed.

Keywords:
random choice, choose strategy, prompt variation, deterministic random, select from list, rotate ideas.

---CHUNK_BREAK---

## Timer_Node

Node Name:
Timer_Node

Internal processing description:
Emits `output_text` only when a timer condition has elapsed. It stores state in a JSON file containing `last_fired` and `last_fired_date`. Missing or invalid state files are created or repaired. In `interval` mode, it fires after at least `every_mins` minutes since last fire. In `clock` mode, it fires when local time matches `target_time` in `HH:MM` and it has not fired that day. `reset` is latched by node/session id so reset happens on a rising edge.

Inputs:
- `output_text`: STRING. Text emitted when the timer fires.
- `mode`: COMBO. `interval` or `clock`.
- `every_mins`: INT. Interval minutes.
- `target_time`: STRING. `HH:MM` local time for clock mode.
- `reset_ratio`: FLOAT. Reset window ratio. Invalid values are treated as 0.5.
- `state_file_path`: STRING. Path to timer state JSON.
- `reset`: BOOLEAN. Resets state on rising edge.
- Hidden `unique_id`: supplied by ComfyUI.

Outputs:
- `output_text_out`: STRING. The trigger text when fired, otherwise empty.
- `error_string`: STRING. Warning/reset/error message or empty string.

A selection of other Nodes they are often used with:
Text_Gate, easy blocker, LLMCall, File_Write, Timestamp, Exec, PreviewAny.

When to use the Node:
Use for periodic agent runs, daily workflow checks, scheduled self-improvement, polling, heartbeat logging, or time-based gating.

How it's used in a ComfyUI Json:
- `type`: `Timer_Node`.
- Widget order: `output_text`, `mode`, `every_mins`, `target_time`, `reset_ratio`, `state_file_path`, `reset`.
- Hidden `unique_id` is runtime metadata, not a normal widget.

Keywords:
timer, schedule, interval trigger, daily trigger, periodic agent, heartbeat, run every N minutes.

---CHUNK_BREAK---

## MCP_Server_Loader

Node Name:
MCP_Server_Loader

Internal processing description:
Creates an `MCP_PROVIDER` for an HTTP-accessible MCP server. It validates that `mcp_server_url` is a non-empty HTTP or HTTPS URL and normalizes trailing slashes. `api_key` is optional and stored for bearer authentication. This node only configures the provider; it does not list or call tools.

Inputs:
- `mcp_server_url`: STRING. Default `http://127.0.0.1:8080`.
- `api_key`: STRING. Optional bearer token.

Outputs:
- `mcp_provider`: MCP_PROVIDER. Provider object for MCP nodes.
- `error_string`: STRING. Validation error or empty string.

A selection of other Nodes they are often used with:
MCP_List_Tools, MCP_Call, LLMCall, JSON_Cleaner, Prompt_Combine.

When to use the Node:
Use when a workflow needs tools exposed through an MCP HTTP server.

How it's used in a ComfyUI Json:
- `type`: `MCP_Server_Loader`.
- Widget order: `mcp_server_url`, `api_key`.
- Link `mcp_provider` into `MCP_List_Tools` and `MCP_Call`.

Keywords:
MCP provider, load MCP server, tool server, external tools, model context protocol.

---CHUNK_BREAK---

## MCP_List_Tools

Node Name:
MCP_List_Tools

Internal processing description:
Initializes an MCP HTTP session, sends the initialized notification, then requests `tools/list`. It returns the server's `tools` array formatted as JSON. It errors if the provider is invalid, timeout is invalid, request fails, or the result does not contain a tools array. It is always treated as changed so tool lists can refresh.

Inputs:
- `mcp_provider`: MCP_PROVIDER. From `MCP_Server_Loader`.
- `timeout`: INT. Request timeout in seconds.

Outputs:
- `tools_json_string`: STRING. JSON array of MCP tool descriptions.
- `error_string`: STRING. Request/schema error or empty string.

A selection of other Nodes they are often used with:
MCP_Server_Loader, LLMCall, Prompt_Combine, JSON_Cleaner, JSON_Read, PreviewAny.

When to use the Node:
Use before tool planning so an LLM can see available tool names, descriptions, and argument schemas.

How it's used in a ComfyUI Json:
- `type`: `MCP_List_Tools`.
- Widget order after linked provider: `timeout`.
- Link `MCP_Server_Loader.mcp_provider` into `mcp_provider`.

Keywords:
list tools, MCP tools, tool schema, available actions, tool descriptions, discover tools.

---CHUNK_BREAK---

## MCP_Call

Node Name:
MCP_Call

Internal processing description:
Executes one MCP tool call. `tool_call_json` must decode to an object with a non-empty string field `tool` and an optional object field `arguments`. The node initializes an MCP HTTP session and sends `tools/call` with the tool name and arguments. It serializes results into text, preferring text content, structured content, or JSON. If the MCP result has `isError`, the serialized result is returned as `error_string`.

Inputs:
- `mcp_provider`: MCP_PROVIDER. From `MCP_Server_Loader`.
- `tool_call_json`: STRING. JSON object like `{"tool":"tool_name","arguments":{...}}`.
- `timeout`: INT. Request timeout in seconds.

Outputs:
- `tool_result_text`: STRING. Serialized successful tool result.
- `error_string`: STRING. Tool/API error or empty string.

A selection of other Nodes they are often used with:
MCP_Server_Loader, MCP_List_Tools, LLMCall, JSON_Cleaner, JSON_Read, Prompt_Combine, File_Write.

When to use the Node:
Use after an LLM has selected a tool and produced validated tool-call JSON. It bridges model reasoning into external action.

How it's used in a ComfyUI Json:
- `type`: `MCP_Call`.
- Widget order after linked provider: `tool_call_json`, `timeout`.
- Link provider from `MCP_Server_Loader`.
- `OUTPUT_NODE = True`.

Keywords:
call tool, MCP call, execute tool, tool action, external action, use server tool.

---CHUNK_BREAK---

## Exec

Node Name:
Exec

Internal processing description:
Runs shell commands in a persistent per-node shell session. On Windows it starts `cmd.exe`; on other systems it starts the user shell or `/bin/sh`. Environment changes can persist across calls for the same node. After each command, the node writes an internal marker to detect completion. `output_mode` returns either the current command block or the full accumulated transcript. Sending `exit` closes the session. On timeout or execution error, the shell session is closed.

Inputs:
- `command_text`: STRING. Shell command. Cannot be empty.
- `output_mode`: COMBO. `Current Command` or `Entire Terminal`.
- `timeout`: INT. Timeout in seconds.
- Hidden `unique_id`: supplied by ComfyUI for per-node shell isolation.

Outputs:
- `terminal_text`: STRING. Command output or full session history.
- `error_string`: STRING. Execution/timeout error or empty string.

A selection of other Nodes they are often used with:
Text_Gate, easy blocker, LLMCall, Prompt_Combine, File_Read, File_Write, StringCompare, PreviewAny.

When to use the Node:
Use to inspect the local environment, run tests, call CLI tools, list files, or execute controlled commands. Gate LLM-generated commands before this node.

How it's used in a ComfyUI Json:
- `type`: `Exec`.
- Widget order: `command_text`, `output_mode`, `timeout`.
- `OUTPUT_NODE = True`.
- Hidden `unique_id` is runtime metadata, not a normal widget.

Keywords:
execute command, shell, terminal, run tests, inspect files, command output, persistent shell, CLI action.

---CHUNK_BREAK---

## easy blocker

Node Name:
easy blocker

Internal processing description:
External helper node from `comfyui-easy-use`, not ComfyClaw. It acts as a wildcard pass-through blocker/gate. The example workflow shows an any-type input named `in`, a boolean control named `continue`, and an any-type output named `out`. Treat it as a manual or boolean-controlled checkpoint for allowing or preventing downstream flow without transforming the payload.

Inputs:
- `in`: `*`. Any payload type.
- `continue`: BOOLEAN. Whether to allow the payload to pass through.

Outputs:
- `out`: `*`. Passed-through payload when allowed.

A selection of other Nodes they are often used with:
Timer_Node, Text_Gate, easy compare, StringCompare, Exec, LLMCall, MCP_Call, File_Write, PreviewAny.

When to use the Node:
Use before expensive, risky, or state-changing nodes when a workflow needs a manual checkpoint or boolean pause point. It is especially useful before `Exec`, `MCP_Call`, and `File_Write`.

How it's used in a ComfyUI Json:
- `type`: `easy blocker`.
- `properties.cnr_id`: `comfyui-easy-use`.
- Widget order: `continue`.
- The example uses EasyUse version `1.3.6`.

Keywords:
blocker, manual gate, continue switch, pause workflow, checkpoint, safety stop, prevent execution.

---CHUNK_BREAK---

## easy compare

Node Name:
easy compare

Internal processing description:
External helper node from `comfyui-easy-use`, not ComfyClaw. This is the EasyUse compare node the user referred to as Compare-EasyUse. It compares two wildcard values using a selected comparison expression and returns a boolean. The example workflow shows inputs `a`, `b`, and `comparison`, with widget value `a < b`. Because `a` and `b` are wildcard sockets, the node can be useful for numeric, string, boolean, or other comparable values depending on EasyUse's implementation.

Inputs:
- `a`: `*`. Left value.
- `b`: `*`. Right value.
- `comparison`: COMBO. Comparison operation. Example value: `a < b`.

Outputs:
- `boolean`: BOOLEAN. Result of the selected comparison.

A selection of other Nodes they are often used with:
Token_Estimator, JSON_Count_keys, StringCompare, Text_Gate, easy blocker, Timer_Node, Route, PreviewAny.

When to use the Node:
Use when a workflow needs boolean control based on comparing two values, especially numeric thresholds such as token estimate under a limit, JSON key count greater than zero, timer output present, or a score crossing a threshold. Use `StringCompare` when the comparison is specifically string-mode based and you want ComfyUI core behavior.

How it's used in a ComfyUI Json:
- `type`: `easy compare`.
- `properties.cnr_id`: `comfyui-easy-use`.
- Widget order: `comparison`.
- Inputs `a` and `b` can be linked from any compatible output because their socket type is `*`.
- The separate example workflow is `Example_Workflows/Compare-EasyUse.json`.

Keywords:
compare values, EasyUse compare, numeric condition, less than, greater than, threshold, boolean comparison, token limit check.

---CHUNK_BREAK---

## StringCompare

Node Name:
StringCompare

Internal processing description:
External helper node from ComfyUI core, not ComfyClaw. It compares two strings and returns a boolean. The example workflow shows inputs `string_a`, `string_b`, `mode`, and `case_sensitive`, with mode set to `Starts With`. It is useful for simple string conditions. Unlike `Text_Gate`, it does not pass through the original text and does not return an `error_string`.

Inputs:
- `string_a`: STRING. Left/source string.
- `string_b`: STRING. Right/pattern string.
- `mode`: COMBO. String comparison mode. Example: `Starts With`.
- `case_sensitive`: BOOLEAN. Whether comparison respects case.

Outputs:
- `BOOLEAN`: BOOLEAN. Result of the comparison.

A selection of other Nodes they are often used with:
PrimitiveString, easy blocker, easy compare, Text_Gate, Route, Exec, LLMCall, PreviewAny.

When to use the Node:
Use when a workflow needs a simple boolean result from string comparison, such as checking whether an LLM output starts with a marker or whether an `error_string` is empty/non-empty when paired with the right mode.

How it's used in a ComfyUI Json:
- `type`: `StringCompare`.
- `properties.cnr_id`: `comfy-core`.
- Widget order: `string_a`, `string_b`, `mode`, `case_sensitive`.

Keywords:
compare strings, boolean string check, starts with, equals, case sensitive, string condition.

---CHUNK_BREAK---

## PrimitiveString

Node Name:
PrimitiveString

Internal processing description:
External helper node from ComfyUI core, not ComfyClaw. It creates a simple string value from a widget and exposes it as a `STRING` output. It is a basic constant/input node for workflows and does not transform the text.

Inputs:
- `value`: STRING. Literal string value.

Outputs:
- `STRING`: STRING. The literal string.

A selection of other Nodes they are often used with:
Prompt_Combine, StringCompare, Text_Gate, Route, File_Read, File_Write, LLMCall, MCP_Call, Exec.

When to use the Node:
Use for constants, markers, filenames, fixed prompts, comparison strings, command snippets, JSON keys, and other literal text values that should be visibly wired through the graph.

How it's used in a ComfyUI Json:
- `type`: `PrimitiveString`.
- `properties.cnr_id`: `comfy-core`.
- Widget order: `value`.

Keywords:
string constant, literal text, fixed value, marker text, prompt constant, file path constant.

---CHUNK_BREAK---

## PreviewAny

Node Name:
PreviewAny

Internal processing description:
External helper node from ComfyUI core, not ComfyClaw. It previews the incoming value from a wildcard `source` input. It is a debugging and inspection node rather than a transformation node. The example workflow shows no outputs.

Inputs:
- `source`: `*`. Any value to preview.

Outputs:
- None.

A selection of other Nodes they are often used with:
All ComfyClaw nodes, especially LLMCall, JSON_Cleaner, JSON_Read, Embedding_Query, MCP_Call, Exec, Text_Gate, Route, Timer_Node.

When to use the Node:
Use while building or improving workflows to inspect intermediate outputs, generated JSON, tool results, terminal output, retrieved chunks, booleans, and every important `error_string`.

How it's used in a ComfyUI Json:
- `type`: `PreviewAny`.
- `properties.cnr_id`: `comfy-core`.
- One wildcard input named `source`.
- The example workflow serializes three null widget values; these are UI artifacts, not semantic inputs for the agent.

Keywords:
preview, debug output, inspect value, show result, view error, monitor workflow, display intermediate.

