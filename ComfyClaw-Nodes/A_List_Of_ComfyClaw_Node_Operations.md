# ComfyClaw Node Operations Simple Reference

Purpose:
This document explains what each ComfyClaw node does in workflow terms. It is written for humans and agents designing workflows, not for developers reading internals.

General rules:
- a ready input means it's not blocked.
- Most nodes output `error_string`. Empty `error_string` means the node succeeded normally.
- All nodes, except where specified, as long as the inputs are ready (even nothing connected or and empty string""), it will always output a string (or whatever it's designated, even "") to the outputs. Only blocking an input will cause the node to not fire.

- Many JSON nodes use dot paths such as `TASK0.ONE`, `items.0.name`, or `FILE_MODIFY_DATES.C:/agents/Tools.md`.
- Dynamic input nodes can add more inputs in the UI, usually up to 20.
- Provider outputs such as `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, and `MCP_PROVIDER` are connection objects for other nodes, not normal text.
- The registered node names in `__init__.py` are the authoritative node inventory. Files such as `common.py`, `media_common.py`, `providers.py`, and other helper/support modules are not ComfyUI nodes.


## Core Nodes

### Prompt_Combine

Purpose:
Combines text pieces into one string.

Inputs:
- `text_1`: First string.
- `text_2`, `text_3`, etc.: Optional added strings.

Outputs:
- `combined_string`: All input strings joined directly in numeric order.
- `error_string`: Error if an input is not a string.

Workflow meaning:
Use this to build prompts, file paths, commands, JSON fragments, or any text assembled from parts. It does not add spaces or newlines automatically. 

### Text_Gate

Purpose:
Allows or blocks a string based on text-matching rules.

Inputs:
- `input_string`: Text to test.
- `mode`: `deny` blocks matching text; `allow` only passes matching text.
- `override_text`: Replacement text that can be output instead of the original.
- `use_override`: If enabled, passed output becomes `override_text`.
- `rule_1_type`, `rule_2_type`, etc.: Match type, such as `contains`, `equals`, `starts_with`, or `ends_with`.
- `rule_1_text`, `rule_2_text`, etc.: Text to match.

Outputs:
- `string_output`: Original text, override text, or empty string.
- `error_string`: Validation errors.
- `is_match`: True if any rule matched.

Workflow meaning:
Use this as a text pass/block gate. In deny mode, matched text is stopped. In allow mode, only input with matched text continues. 

### Route

Purpose:
Routes one string to one or more branch outputs.

Inputs:
- `input_string`: Text to route.
- `default_branch`: Branch number to use if no rule matches, or `0` for no default.
- `branch_1_type`, `branch_2_type`, etc.: Match type.
- `branch_1_rule`, `branch_2_rule`, etc.: Text rule for each branch.

Outputs:
- `branch_1` through `branch_20`: Each matching branch receives `input_string`; nonmatching branches output empty strings.
- `index_output`: Number of the first active branch. Default branch also counts. `0` means no route was active.
- `error_string`: Validation errors.
- `default_branch` will send to that default_branch number (eg, default_branch = 1 is `branch_1`) if no matches are detected the `input_string` will be passed to the `default_branch`.

Workflow meaning:
Use this when text can choose one or more workflow paths. The `index_output` can drive later path-selection logic. 

### String_Find_Replace

Purpose:
Replaces every occurrence of one substring with another.

Inputs:
- `string_input`: Text to edit.
- `find_text`: Text to search for.
- `replace_text`: Replacement text.

Outputs:
- `output_string`: Edited text.
- `error_string`: Error if inputs are invalid or `find_text` is empty.

Workflow meaning:
Use this for simple text cleanup, marker replacement, newline insertion, or prompt formatting. 

### File_Read

Purpose:
Reads text from a file.

Inputs:
- `file_path`: Path to the file.

Outputs:
- `file_text`: File contents.
- `error_string`: File/path/read error.

Workflow meaning:
Use this to load prompts, memory files, instructions, JSON stores, or tool output from disk. Works differently from say a Primitive String node that may have the exact same content. The Read_File will reread every time even if the file path and file remain unchanged; the output is exactly the same. However a blocked input will stop it from running. It doesn't cache like a Primitive String node. 

### File_Write

Purpose:
Writes text to a file.

Inputs:
- `file_path`: Path to write.
- `text_input`: Text to write.
- `mode`: `overwrite` replaces the file; `append` adds to the end.
- `success_text`: Text returned when the write succeeds.

Outputs:
- `output_text`: `success_text` after a successful write.
- `error_string`: File/path/write error.

Workflow meaning:
Use this to save logs, memories, generated files, summaries, or workflow state.

### Text_Cleaner

Purpose:
Extracts text between a start marker and an end marker.

Inputs:
- `string_input`: Text to clean.
- `start_text`: Start marker. Empty means start at the beginning.
- `end_text`: End marker. Empty means end at the end.
- `include_start_end`: If true, keep the markers in the output. If false, remove them.

Outputs:
- `output_string`: Extracted text.
- `error_string`: Warning if markers were missing or boundaries were repaired.

Workflow meaning:
Use this to pull a section out of LLM output, tool output, or a file.

### Random_from_List

Purpose:
Selects one non-empty string from a list using a seed.

Inputs:
- `text_1`: First candidate string.
- `text_2`, `text_3`, etc.: Optional added candidate strings.
- `seed`: Integer used to choose the output.

Outputs:
- `string_output`: Selected non-empty string.
- `error_string`: Error if there are no valid strings or seed is invalid.

Workflow meaning:
Use this for deterministic variation. The same seed and same list produce the same selection.


## Utility Nodes

### Boolean_Output_Switch

Purpose:
Routes any input to one of two outputs based on a boolean. 

Inputs:
- `input`: Any value.
- `boolean`: True or false switch.

Outputs:
- `on_true`: Receives `input` when `boolean` is true. Otherwise it's blocked.
- `on_false`: Receives `input` when `boolean` is false. Otherwise it's blocked.
- `index_output`: `0` for `on_true`, `1` for `on_false`.
- `error_string`: Error if `boolean` is not a boolean.

Workflow meaning:
Use this to choose between true-path and false-path execution.

### Or_And

Purpose:
Combines multiple boolean inputs with OR or AND logic.

Inputs:
- `operation`: `Or` or `And`.
- `input_1`, `input_2`, etc.: Boolean inputs. They can be toggled manually or connected.

Outputs:
- `output`: Result of the logic gate.
- `error_string`: Names the first input that is not a boolean.

Workflow meaning:
Use this to combine many conditions into one boolean.

### Any_To_Something

Purpose:
Converts any input into useful basic output types where possible.

Inputs:
- `input`: Any value.

Outputs:
- `string_output`: Plain text version of the input.
- `int_output`: Integer version when possible, otherwise empty string. Floats and numeric strings round to the nearest integer, with Half-up rounding (eg, 3.50 becomes 4).
- `float_output`: Float version when possible, otherwise empty string.
- `boolean_output`: Boolean version when possible, otherwise empty string. Strings `true` and `false` are recognized case-insensitively.
- `error_string`: Currently empty for normal conversion misses. Virtually useless on this node.

Workflow meaning:
Use this when one value might need to feed text, number, or boolean nodes. Can convert most formats either way.

### Save_Media_As

Purpose:
Saves one ComfyUI image, audio object, or text string to a file.

Inputs:
- `output_path`: Destination file path. If it has no extension, the selected media format is appended.
- `media_format`: `png`, `jpg`, `wav`, `mp3`, or `txt`.
- `text_input`: Text source used when saving `txt`.
- `image_input`: Optional ComfyUI `IMAGE` source used for `png` or `jpg`.
- `audio_input`: Optional ComfyUI `AUDIO` source used for `wav` or `mp3`.

Outputs:
- `file_path`: Final saved file path.
- `error_string`: Input, format, conversion, directory, or file-write error.

Workflow meaning:
Use this when a generated image, sound, or text value needs a stable file path for another node or local model. Supply exactly one media source. PNG, JPG, WAV, and TXT are handled directly. MP3 encoding requires optional `pydub` and ffmpeg.

### Has_Changed

Purpose:
Checks whether a file has a different modified timestamp than the last recorded value.

Inputs:
- `data_file`: JSON file used to store previous modified timestamps.
- `file_to_check`: File whose modified date should be checked.

Outputs:
- `has_changed`: True if the file is new to the store or has changed since last check.
- `last_modified`: Current modified timestamp for `file_to_check`.
- `error_string`: File, JSON, or write error.

Workflow meaning:
Use this to trigger work only when a watched file changes. When it detects a change, it updates `data_file`. data_file entry is json. Eg:
{
  "FILE_MODIFY_DATES": {
    "C:/Comfy-Claw/TOOLS.md": "2026-04-23T23:08:21.669511"
  }
}

### Token_Estimator

Purpose:
Estimates token count from word count.

Inputs:
- `input_text`: Text to measure.
- `ratio`: Multiplier applied to word count.

Outputs:
- `token_estimate_int`: Rounded token estimate as an integer.
- `token_estimate_string`: Same estimate as text.
- `word_count_string`: Word count as text.
- `character_count`: Character count as an integer.
- `error_string`: Ratio validation error.

Workflow meaning:
Use this to estimate prompt size before sending text to an LLM. Can also be used for audits, logs, or for model selection etc.

### Timestamp

Purpose:
Outputs the current time.

Inputs:
- `format`: `iso`, `human`, or `unix`.

Outputs:
- `timestamp_string`: Current timestamp in the selected format.
- `error_string`: Time access error.

Workflow meaning:
Use this for logs, file names, memory entries, and run stamps.

### Preview_Any_As_Text

Purpose:
Shows any input as selectable preview text, then resets the preview after a delay.

Inputs:
- `Source`: Any value to display.
- `display_time`: Seconds before the preview resets to `Waiting for trigger`.

Outputs:
- No data outputs. It displays UI preview text only.

Workflow meaning:
Use this for debugging to prove a value or trigger passed through, even when the value is empty text. Ignores caching to show if it's ready or blocked. Cached with "" will show "" whereas blocked will continue to display `Waiting for trigger`.

### Timer_Node

Purpose:
Emits text only when a timer condition is met.

Inputs:
- `output_text`: Text to emit when the timer fires.
- `mode`: `interval` or `clock`.
- `every_mins`: Interval minutes for interval mode.
- `target_time`: `HH:MM` time for clock mode.
- `reset_ratio`: Fraction of the interval/day used as a reset window.
- `state_file_path`: JSON file that stores last-fired state.
- `reset`: Resets the timer state when toggled true.

Outputs:
- `output_text_out`: `output_text` when the timer fires, otherwise empty string.
- `error_string`: State, timing, or validation warning/error.

Workflow meaning:
Use this to schedule recurring workflow actions.

### Trigger

Purpose:
Turns any incoming value into a simple trigger signal.

Inputs:
- `input`: Any value.

Outputs:
- `trigger_string`: Always empty string.
- `triggered`: True when input is not `None` and not empty string.

Workflow meaning:
Use this to detect whether a value arrived, even if the content itself is not needed. Turns any ready signal into "". Used to control the flow from section to section, with Prompt_Combine input not being ready until it gets "" from the trigger.


## JSON Nodes

### JSON_Cleaner

Purpose:
Turns messy JSON-like text into valid JSON text whenever possible.

Inputs:
- `string_input`: Messy text, JSON, JSON inside markdown, or JSON-ish output.

Outputs:
- `json_string`: Valid JSON text. Falls back to `{}` if nothing useful can be salvaged.
- `error_string`: Empty if already clean, or a repair/fallback warning.

Workflow meaning:
Use this after LLM output or tool output before feeding JSON into stricter JSON nodes.

### JSON_Count_keys

Purpose:
Counts keys in a JSON object.

Inputs:
- `json_input`: JSON text.
- `key_path`: Dot path to the object to count. Empty means root.
- `count_mode`: `Root` counts direct keys only. `All` counts nested object keys too.

Outputs:
- `key_count`: Count result.
- `error_string`: JSON/path/type error.

Workflow meaning:
Use this to measure list-like JSON objects. Handy when appending entries to a JSON and requiring the most recent appended entry in a branch. Count the keys, then use "Math Int" (an easy-use node) to subtract 1, then JSON_Read that index. Can also be used to check if a JSON is too long and needs trimming.

### JSON_Read

Purpose:
Reads a key/value from JSON by path or by index.

Inputs:
- `json_input`: JSON text.
- `key_path`: Dot path to read from, or path to the object/list used for indexed reading.
- `index`: Index used when `read_mode` is `index`.
- `read_mode`: `key_path` or `index`.
- `index_mode`: For index mode, `root`, `leaves`, or `all`.

Outputs:
- `key`: Key name for the selected value.
- `value_text`: Selected value as plain text.
- `value_json`: Selected value serialized as JSON.
- `error_string`: JSON/path/index error.

Workflow meaning:
Use this to extract specific JSON values or walk through JSON entries by index. `root` indexes direct children, `leaves` indexes only final values, and `all` indexes branches plus leaves in order. `read_mode` `key_path` ignores index completely. `read_mode` `index` considers "" as the index only, but if a `key_path` input is given, then the `key_path` will be the root where the index starts. Handy for getting an unknown index key or value from inside a nested JSON. Eg, if keys are timestamps inside "documents.logs" then you can get documents.logs.{index0}.

### JSON_Append

Purpose:
Adds a new key/value pair to a JSON object.

Inputs:
- `json_input`: JSON object text.
- `key_path`: Dot path for the new key. Missing parent objects are created.
- `value_text`: New value. If it looks like JSON, it becomes JSON; otherwise it becomes a string.

Outputs:
- `json_string`: Updated JSON.
- `error_string`: Error if the key already exists, path is invalid, or JSON is invalid.

Workflow meaning:
Use this to add new memory entries, fields, nested objects, or task records.

### JSON_Edit

Purpose:
Replaces an existing JSON value.

Inputs:
- `json_input`: JSON text.
- `key_path`: Dot path to an existing key or array index.
- `value_text`: Replacement value. JSON-like values become JSON values.

Outputs:
- `json_string`: Updated JSON.
- `error_string`: Error if the path does not exist or value is empty.

Workflow meaning:
Use this to overwrite existing JSON fields. Great for updating a file that holds variables.

### JSON_Find_First_Last

Purpose:
Finds the first or last root key/value pair matching a rule.

Inputs:
- `input_text`: JSON object text.
- `Find_Mode`: `First` or `Last`.
- `Search_In`: Search in `Key` or `Value`.
- `Condition`: `Does` or `Doesn't`.
- `Match_Type`: `Contains`, `Starts With`, `Ends With`, or `Equals`.
- `Rule_Text`: Text rule.

Outputs:
- `Output_key`: Matched root key.
- `Output_value`: Matched value as plain text.
- `Error_string`: Error or no-match message.

Workflow meaning:
Use this to find a matching JSON entry without knowing its exact key. Great for looking for the first value that doesn't start with "Complete" to find the first incomplete task in a JSON list etc.

### JSON_insert_key

Purpose:
Inserts a new key before or after an existing key in an object.

Inputs:
- `json_input`: JSON object text.
- `key_path`: Target key path, or object path when using index mode.
- `index`: Target index when `insert_mode` is `index`.
- `new_key_path`: New key path to insert. Nested paths create nested values.
- `value_text`: Value for the new key.
- `mode`: `before` or `after`.
- `insert_mode`: `key_path` or `index`.

Outputs:
- `json_string`: Updated JSON with insertion order preserved.
- `error_string`: JSON/path/existing-key error.

Workflow meaning:
Use this when order matters and a key must be inserted in a specific place.  Eg, if keys are timestamps inside "documents.logs" then you can insert a key before documents.logs.{index0}.

### JSON_Remove_Entry

Purpose:
Deletes a JSON key or array item.

Inputs:
- `json_input`: JSON text.
- `key_path`: Dot path to delete, or object path for index mode.
- `index`: Index to delete when `remove_mode` is `index`.
- `remove_mode`: `key_path` or `index`.

Outputs:
- `json_string`: Updated JSON.
- `error_string`: JSON/path/index error.

Workflow meaning:
Use this to remove entries from objects or arrays. Eg, if keys are timestamps inside "documents.logs" then you can remove the documents.logs.{index0} key/value pair.

### JSON_Mass_Math

Purpose:
Applies integer math to every matching sub-key path in a JSON structure.

Inputs:
- `json_input`: JSON text.
- `sub_key_path`: Relative dot path to values to change.
- `operation`: `add`, `subtract`, `multiply`, `divide`, `modulo`, or `power`.
- `int`: Number used in the operation.
- `min`: Lower clamp.
- `max`: Upper clamp.

Outputs:
- `json_output`: Updated JSON. Changed values are stored as strings.
- `lowest_value`: Lowest adjusted integer found.
- `error_string`: JSON/path/math/type error.

Workflow meaning:
Use this to adjust all matching counters, scores, weights, or priorities at once. Can read integer (eg, 1) values from the JSON or string numbers, (eg, "1"), but writes the value as a string number (eg, "1"). Handy for targeting values for adjusting all the values to make sure they are suitable for processing. Like reducing all memory importance values so that there are ranges acceptable for removal.

### JSON_Mass_Math_Keys

Purpose:
Uses matching leaf paths from one JSON object to adjust another JSON object.

Inputs:
- `json_destination`: JSON to modify.
- `operation`: Math operation.
- `json_source`: JSON whose integer leaf values supply the operation amount.
- `min`: Lower clamp.
- `max`: Upper clamp.

Outputs:
- `json_output`: Updated destination JSON.
- `error_string`: JSON/math/type error.

Workflow meaning:
Use this when one JSON object contains per-key adjustment values for another. For instance, matching time stamps from one JSON can be found and adjusted in a much bigger JSON. Helpful for increasing say the importance of only recalled memories in the full memory file.

### JSON_Mass_Remove

Purpose:
Removes root keys whose nested integer value matches a comparison, until the root key count is at or below a limit.

Inputs:
- `json_input`: JSON object text.
- `max_rootkeys`: Desired maximum number of root keys.
- `sub_key_path`: Relative dot path to the integer value to test inside each root entry.
- `logic`: `>`, `<`, `>=`, `<=`, or `=`.
- `int`: Comparison number.

Outputs:
- `json_output`: Reduced JSON.
- `error_string`: Error or warning if it could not reduce enough.

Workflow meaning:
Use this to prune JSON records by score, age, count, or priority. This is great for pruning unnecessary memories from a file which have low importance values, until the memory file is reduced to a viable size. 

### JSON_Tally_Found_Keys

Purpose:
Adds root keys from a source JSON to a destination JSON, and a subkey with an incremented value. If the root key already exists, then in increments the subkey.

Inputs:
- `json_source`: JSON whose root keys should be counted.
- `json_destination`: Existing tally JSON.
- `sub_key_path`: Counter field path inside each destination root entry.

Outputs:
- `json_output`: Updated tally JSON.
- `error_string`: JSON/path/type error.

Workflow meaning:
Use this to increment detection counts for records, memories, task IDs, or keys seen during a workflow. Eg, a memory recall (RAG) JSON might have 3 recalled timestamp memory IDs. This node looks through a JSON of recalled memories and increments any that are already in the destination JOSN and adds any keys that aren't in the destination JSON, to keep a tally of how many times those ids have appeared over many triggers of the node. After 200 iterations, a specific memory may have been recalled more than others, and the subkey has that tally.

### JSON_to_outputs

Purpose:
Walks JSON in order and exposes selected entries as separate string outputs.

Inputs:
- `json_input`: JSON text.
- `output_0_mode`, `output_1_mode`, etc.: Optional output mode for each output. Mode is `key`, `value`, or `key/value`.

Outputs:
- `output_0` through `output_19`: Selected walked entries.
- `error_string`: JSON or mode error.

Workflow meaning:
Use this to fan JSON entries out into separate ComfyUI outputs, so you can process each key separately in 1 go. It's like JSON_read, but for every single index up to 20 in total. Rather than 20 JSON_read nodes reading each index, this is those 20 in 1 node.

### JSON_TO_Markdown

Purpose:
Converts structured JSON prompt sections into lightweight heading-based Markdown.

Inputs:
- `json_input`: JSON text containing the sections to convert.

Outputs:
- `markdown_output`: Converted Markdown text.
- `error_string`: Invalid JSON or conversion error.

Workflow meaning:
Use this to turn structured JSON sections into a readable prompt or document format.

### Markdown_TO_JSON

Purpose:
Converts lightweight heading-based Markdown sections into JSON.

Inputs:
- `markdown_input`: Markdown text to convert.

Outputs:
- `json_output`: Converted JSON text.
- `error_string`: Markdown conversion error.

Workflow meaning:
Use this when human-readable Markdown sections need to become structured JSON for later nodes.

### String_To_Escaped_JSON

Purpose:
Escapes plain text so it can be placed safely inside a JSON string value.

Inputs:
- `string_input`: Plain text to escape.

Outputs:
- `escaped_json`: JSON-string-safe escaped text.
- `error_string`: Input validation error.

Workflow meaning:
Use this when quotes, newlines, tabs, or backslashes in normal text must be embedded inside JSON.

### Escaped_JSON_To_String

Purpose:
Decodes JSON string escapes back into normal text.

Inputs:
- `escaped_json`: Escaped JSON string content.

Outputs:
- `string_output`: Decoded plain text.
- `error_string`: Invalid escaped-string error.

Workflow meaning:
Use this to recover readable text from a JSON-escaped string.

### Embedding_Bundle_To_JSON

Purpose:
Converts JSON object chunks stored in an embedding bundle into one JSON object.

Inputs:
- `embedding_bundle_string`: Embedding bundle JSON from `Embedding`.

Outputs:
- `json_string`: Combined JSON object from bundle chunks.
- `error_string`: Bundle/chunk/duplicate-key error.

Workflow meaning:
Use this when embedded chunks are JSON records and you want the original JSON object back. Helpful when using appending entries to a rag bundle to reduce embedding the entire file from scratch each time, but when you need the appended embedding file to be converted back into a JSON for processing. For instance forgetting memories or dreaming.

### Embedding_Query_To_JSON

Purpose:
Converts `Embedding_Query` result chunks into one JSON object.

Inputs:
- `json_input`: Query result JSON from `Embedding_Query`.

Outputs:
- `json_output`: Combined JSON object from each result's `chunk_text`.
- `error_string`: Result/chunk/duplicate-key error.

Workflow meaning:
Use this to turn retrieved JSON memory chunks back into usable JSON records. Helpful for turning RAG recalled memories into a JSON object for processing, for instance with JSON_Tally_Found_Keys. It also strips the query to reduce token count.


## YAML Nodes

### YAML_Read

Purpose:
Reads a key/value from YAML by dot path or ordered index.

Inputs:
- `yaml_input`: YAML text.
- `key_path`: Dot path to read, or the object/list used as the index root.
- `index`: Index used in `index` read mode.
- `read_mode`: `key_path` or `index`.
- `index_mode`: In index mode, `root`, `leaves`, or `all`.

Outputs:
- `key`: Selected key name.
- `value_text`: Selected value as plain text.
- `value_yaml`: Selected value serialized as YAML.
- `key/value_yaml`: YAML containing the selected key and value.
- `error_string`: YAML, path, mode, or index error.

Workflow meaning:
Use this like `JSON_Read` when the source data is YAML. Index mode can walk direct children, leaves, or all branches and leaves.

### YAML_To_JSON

Purpose:
Converts YAML text into formatted JSON text.

Inputs:
- `yaml_input`: YAML text to convert.

Outputs:
- `json_output`: Converted JSON.
- `error_string`: Invalid YAML or conversion error.

Workflow meaning:
Use this before JSON-processing nodes when the original file or model output is YAML.

### JSON_To_YAML

Purpose:
Converts JSON text into YAML text.

Inputs:
- `json_input`: JSON text to convert.

Outputs:
- `yaml_output`: Converted YAML.
- `error_string`: Invalid JSON or YAML serialization error.

Workflow meaning:
Use this when structured JSON needs to be saved, displayed, or consumed as YAML.


## Embedding Nodes

### Chunk_Splitter

Purpose:
Splits long text into chunks for embedding.

Inputs:
- `input_text`: Text to split.
- `main_chunk_min`: Target amount of main units per chunk.
- `main_chunk_split_type`: Unit for main chunks: `characters`, `words`, `paragraphs`, or `custom`.
- `main_chunk_marker_1` through `main_chunk_marker_5`: Custom markers for main chunks.
- `chunk_limit_min`: Minimum size of each chunk measured by limit units.
- `chunk_limit_max`: Maximum size of each chunk measured by limit units.
- `chunk_limit_split_type`: Unit for measuring chunk limits.
- `chunk_limit_marker_1` through `chunk_limit_marker_5`: Custom markers for limit units.
- `chunk_overlap_min`: Amount of overlap from the next chunk.
- `chunk_overlap_split_type`: Unit for overlap.
- `chunk_overlap_marker_1` through `chunk_overlap_marker_5`: Custom markers for overlap.

Outputs:
- `chunks_text`: Chunks joined by the default chunk break marker.
- `chunks_json`: JSON array of chunk strings.
- `error_string`: Split configuration error.

Workflow meaning:
Use this before `Embedding` to create searchable chunks with optional overlap. Allows you to specify multiple chunking locations, for instance screenplay slugline headings. Gives more control over how the chunks are split for better embedding. Only prepares a document for embedding.

### Load_Embedding_Model

Purpose:
Creates an embedding provider for a local Ollama model.

Inputs:
- `model_name`: Ollama embedding model name.

Outputs:
- `embedding_provider`: Provider object for embedding nodes.
- `error_string`: Validation error.

Workflow meaning:
Use this when embeddings come from local Ollama.

### Load_Embedding_API

Purpose:
Creates an embedding provider for an OpenAI-compatible embedding API.

Inputs:
- `api_base_url`: API base URL.
- `api_key`: API key.
- `model_name`: Embedding model name.

Outputs:
- `embedding_provider`: Provider object for embedding nodes.
- `error_string`: Validation error.

Workflow meaning:
Use this when embeddings come from a remote API.

### Embedding

Purpose:
Embeds chunks and stores chunks plus vectors in a bundle.

Inputs:
- `embedding_provider`: Provider from `Load_Embedding_Model` or `Load_Embedding_API`.
- `chunk_input`: Chunks to embed.
- `input_format`: `json_list` or `break_string`.
- `chunk_break_marker`: Separator used when `input_format` is `break_string`.
- `mode`: `Overwrite` creates a new bundle. `Append` adds to an existing bundle.
- `embedding_bundle_string`: Existing bundle used when appending.

Outputs:
- `embedding_bundle_string`: JSON bundle with model name, chunks, and embeddings.
- `error_string`: Provider, parse, or embedding request error.

Workflow meaning:
Use this to build or extend a searchable embedding store.

### Embedding_Query

Purpose:
Searches an embedding bundle for chunks similar to a query.

Inputs:
- `embedding_provider`: Same kind/model provider used for the bundle.
- `embedding_bundle_string`: Bundle from `Embedding`.
- `query_text`: Text to search for.
- `top_k`: Number of top results.
- `timeout`: Request timeout in seconds.

Outputs:
- `results_json_string`: JSON containing query text and ranked results.
- `best_chunk_text`: Text of the top result.
- `error_string`: Provider, bundle, or query error.

Workflow meaning:
Use this to retrieve relevant memory/document chunks.

## LLM Nodes

### LLM_API_Loader

Purpose:
Creates an LLM provider for an OpenAI-compatible API.

Inputs:
- `api_base_url`: API base URL.
- `api_key`: API key. Can be empty for APIs that do not require one.
- `model_name`: LLM model name.

Outputs:
- `llm_provider`: Provider object for `LLMCall`.
- `error_string`: Validation error.

Workflow meaning:
Use this to configure a remote LLM.

### LLM_Model_Loader

Purpose:
Creates an LLM provider for local Ollama.

Inputs:
- `ollama_base_url`: Ollama server URL.
- `model_name`: Ollama model name.

Outputs:
- `llm_provider`: Provider object for `LLMCall`.
- `error_string`: Validation error.

Workflow meaning:
Use this to configure a local Ollama LLM.

### LLMCall

Purpose:
Sends a text or multimodal prompt to an LLM and returns the response.

Inputs:
- `llm_provider`: Provider from an LLM loader.
- `user_prompt`: Main prompt.
- `temperature`: Sampling temperature.
- `max_output_tokens`: Maximum response tokens.
- `timeout_seconds`: Request timeout.
- `system_prompt`: Optional system prompt.
- `media_conversion`: `base64` converts connected media or media files into request data; `path_only` adds literal media paths to a stable `[Media]` prompt block.
- `image_format`: In-memory image conversion format, `png` or `jpg`.
- `audio_format`: In-memory audio conversion format, `wav` or `mp3`.
- `image_file_path`: Optional image path.
- `sound_file_path`: Optional sound path.
- `image_input`: Optional ComfyUI `IMAGE` input.
- `audio_input`: Optional ComfyUI `AUDIO` input.

Outputs:
- `response_text`: LLM response without `<think>` tags.
- `error_string`: Request or validation error.
- `thinking_output`: Extracted thinking/reasoning text when the provider returns it or when `<think>` tags are present.

Workflow meaning:
Use this for text generation, multimodal image/audio analysis, planning, JSON generation, tool-call generation, and agent steps. In `path_only` mode, direct image/audio sockets are rejected; save them first with `Save_Media_As`. Ollama base64 supports images in this node, while Ollama audio should use a local path workflow.


## MCP Nodes

### MCP_Server_Loader

Purpose:
Creates an MCP provider for a server.

Inputs:
- `mcp_server_url`: MCP server URL.
- `api_key`: Optional API key.

Outputs:
- `mcp_provider`: Provider object for MCP nodes.
- `error_string`: Validation error.

Workflow meaning:
Use this to connect the workflow to an MCP server.

### MCP_List_Tools

Purpose:
Gets the available tools from an MCP server.

Inputs:
- `mcp_provider`: Provider from `MCP_Server_Loader`.
- `timeout`: Request timeout.

Outputs:
- `tools_json_string`: JSON list of available tools.
- `error_string`: Request or validation error.

Workflow meaning:
Use this so an LLM or workflow can see what tools are available.

### MCP_Call

Purpose:
Calls one MCP tool.

Inputs:
- `mcp_provider`: Provider from `MCP_Server_Loader`.
- `tool_call_json`: JSON object with `tool` and optional `arguments`.
- `timeout`: Request timeout.

Outputs:
- `tool_result_text`: Tool result converted to text.
- `error_string`: JSON, MCP, or tool error.

Workflow meaning:
Use this to execute tool calls produced by a workflow or LLM.


## System Nodes

### Tool_Caller

Purpose:
Calls the ComfyClaw interactive `run_tool.py` process through a persistent subprocess.

Inputs:
- `tool_path`: Path to the `run_tool.py` file.
- `venv_path`: Path to the tool virtual environment or its Python executable.
- `tool_call`: Tool name and arguments to send.
- `convert_to_json`: When enabled, converts a command such as `TOOL: --arg value` into the interactive runner's compact JSON format.
- `timeout`: Seconds to wait for tool output.

Outputs:
- `tool_output`: Tool result converted to text.
- `error_string`: Path, parsing, process, timeout, or tool-call error.

Workflow meaning:
Use this to run ComfyClaw CLI tools without starting a new Python process for every call. Each node keeps its own persistent interactive tool session.

### Exec

Purpose:
Runs shell commands in a persistent terminal session.

Inputs:
- `command_text`: Command to run. `exit` closes the session.
- `output_mode`: `Current Command` or `Entire Terminal`.
- `timeout`: Seconds before command timeout closes the session.

Outputs:
- `terminal_text`: Current command output or full session transcript.
- `error_string`: Timeout or execution error.

Workflow meaning:
Use this to run local shell commands and feed their output back into the workflow.

### PyAutoGUI_Simple_OCR

Purpose:
Runs one supported PyAutoGUI desktop action, captures the resulting desktop state, and returns a composited image plus simplified OCR grounding.

Inputs:
- `command_string`: PyAutoGUI-style action such as `click(742,381)`, `write("hello")`, `press("enter")`, or `scroll(-400)`. Empty input captures without an action.
- `ocr_engine`: `PaddleOCR`, `EasyOCR`, or `Tesseract`.
- `max_text_chars`: Removes OCR text longer than this many characters.
- `max_box_width`: Removes OCR boxes wider than this value.
- `max_box_height`: Removes OCR boxes taller than this value.
- `min_confidence`: Removes OCR entries below this confidence.
- `OCR_timeout`: Seconds to wait for OCR before returning a timeout error.
- `tesseract_exe_path`: Optional path to `tesseract.exe`; leave blank to use PATH or common Windows install paths.
- `bg_img_path`: Optional background/base image.
- `overlay_img_path`: Optional transparent overlay image.
- `cursor_img_path`: Optional cursor marker image.
- `screenshot_offset_x`, `screenshot_offset_y`: Position of the screenshot on the composite canvas.
- `cursor_offset_x`, `cursor_offset_y`: Cursor marker alignment offsets.

Special commands:
- `wait` or `wait(seconds)`: Performs no PyAutoGUI action, optionally waits, then captures the desktop.
- `screenshot(...)`: Uses the screenshot command's returned image directly and skips the normal automatic screenshot/composite step.

Outputs:
- `image`: Composite ordered as background, screenshot, overlay, then cursor. A screenshot command returns its own screenshot image instead.
- `OCR_JSON`: Compact JSON containing desktop `resolution`, current `cursor`, and filtered OCR entries with `text`, `bbox`, and `confidence`.
- `error_string`: Command, screenshot, image, cursor, OCR, normalization, timeout, or dependency error.

Workflow meaning:
Use this as a grounded desktop-control step for a multimodal agent. Each execution represents a fresh desktop state. OCR always runs on the raw captured screenshot rather than the composited overlay image.
PaddleOCR is initialized with a conservative CPU profile that disables MKLDNN/oneDNN to avoid common Windows Paddle runtime failures.
