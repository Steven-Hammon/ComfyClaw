# ComfyClaw-Tools

ComfyClaw-Tools is a small Python CLI tool runner for humans, agents, and harnesses that need predictable tool calls without a framework.

The core idea is simple:

```powershell
python run_tool.py <tool> <action> [--key value ...]
```

It also supports agent-friendly shortcut keys from `TOOLS.md`:

```powershell
python run_tool.py FETCH-DOWNLOAD "--url https://example.com/file.pdf --out file.pdf"
python run_tool.py FILE-TREE "--path C:\ComfyClaw-Tools --depth 2"
python run_tool.py MCP-CALL '--server https://example.com/mcp --name search_files --arguments {"query":"budget report"}'
```

The runner loads a Python file from `tools/`, calls its `run(args)` function, and prints plain text to stdout.

## What It Is Useful For

ComfyClaw-Tools is useful when you want an LLM, automation harness, or human operator to call local capabilities through one consistent terminal interface.

It is designed for:

- Agent tool execution from simple key/value outputs.
- Reading, writing, searching, and inspecting local files.
- Fetching web content and extracting readable text.
- Running a persistent browser session through repeated CLI calls.
- Querying large documents with local embeddings through Ollama.
- Listing and calling HTTP MCP server tools.
- Keeping tool behavior transparent and easy to debug from a terminal.

It is intentionally not a framework. Tools are plain Python files with plain argument parsing.

## Quick Start

On Windows:

```powershell
setup.bat
```

Or manually:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m playwright install
```

Run a tool:

```powershell
python run_tool.py fetch get --url https://example.com
python run_tool.py file_read full --path README.md
python run_tool.py file tree --path . --depth 2
```

## Two Call Styles

### Standard CLI Style

This is the direct style:

```powershell
python run_tool.py fetch get --url https://example.com --out page.html
python run_tool.py browser goto --url https://example.com
python run_tool.py file_write append --path notes.txt --content "new note"
```

### Agent Key Style

This is the harness-friendly style. The key maps to `<tool> <action>`, and the value is the raw argument string.

```json
{
  "FETCH-DOWNLOAD": "--url https://example.com/file.pdf --out file.pdf"
}
```

Your harness can run:

```powershell
python run_tool.py FETCH-DOWNLOAD "--url https://example.com/file.pdf --out file.pdf"
```

The runner converts that into:

```powershell
python run_tool.py fetch download --url https://example.com/file.pdf --out file.pdf
```

Hyphen and underscore keys are both supported:

```powershell
python run_tool.py FILE_READ-FULL "--path notes.txt"
python run_tool.py FILE_READ_FULL "--path notes.txt"
```

Tool keys are normalized before matching. Case, quotes, angle brackets, trailing colons, hyphens, underscores, and extra symbols are stripped or collapsed, so these all resolve to the same action:

```powershell
python run_tool.py FILE_WRITE-OVERWRITE "--path notes.txt --content hello"
python run_tool.py "<file write overwrite>:" "--path notes.txt --content hello"
python run_tool.py FILEWRITEOVERWRITE "--path notes.txt --content hello"
```

## Argument Handling

Each tool declares the valid arguments for each action in `ACTION_ARGUMENTS`.

The runner uses that declaration to split raw text safely:

```powershell
python run_tool.py SEARCH-INTERNET "--query a messy query with spaces --out results.txt"
```

The value for `--query` becomes:

```text
a messy query with spaces
```

Then `--out` starts the next argument because it is a known argument for `SEARCH-INTERNET`.

This is the main reason the agent-key style is useful: the agent only has to output a key and a raw value string. The runner does the conversion.

When typing commands by hand in PowerShell, wrap raw argument strings in single quotes if they contain JSON. A harness can pass the raw value directly.

## Interactive Mode

Use `--interactive` when another process needs to drive ComfyClaw-Tools directly over stdin/stdout without CMD or shell argument parsing.

```powershell
python run_tool.py --interactive
```

In this mode, `run_tool.py` stays alive and reads one newline-delimited JSON object per stdin line:

```json
{"tool":"FILE_WRITE-APPEND","args":{"path":"C:\\Claw\\Workspace\\ToDo_List.md","content":"\n## Tool & Environment Audit\n- Objective: etc"}}
```

The `tool` value can be an agent key such as `FILE_WRITE-APPEND`, `FETCH-GET`, or `MCP-CALL`. It can also be a direct tool module name if `args` includes an `action` field:

```json
{"tool":"file_read","args":{"action":"full","path":"README.md"}}
```

Interactive mode forwards the selected tool's returned text to stdout and flushes immediately. It does not wrap or reinterpret successful tool output. If `run_tool.py` cannot reach the tool because the JSON is malformed, the tool name is unknown, or dispatch fails, it writes a plain `Error: ...` message to stdout so the caller receives a response.

Newlines inside JSON string values are preserved as data after JSON decoding. This is the preferred mode for ComfyUI nodes or other callers that need to pass markdown, multiline text, or special characters without shell corruption.

## Available Tools

Full agent-facing tool docs live in [TOOLS.md](./TOOLS.md).

Current tool modules:

| Tool | Actions | Purpose |
| --- | --- | --- |
| `fetch` | `get`, `download` | Static HTTP GET and file downloads. |
| `html` | `extract` | Extract readable text from HTML. |
| `pdf` | `extract` | Extract text from local PDFs. |
| `search` | `internet`, `text` | Internet search through `ddgs`. |
| `browser` | `goto`, `click`, `type`, `press`, `state`, `screenshot`, `end` | Persistent Playwright browser session controlled by repeated CLI calls. |
| `ragquerydoc` | `query`, `path` | Query large local documents using Ollama embeddings and cached bundles. |
| `file_read` | `full`, `slice`, `head`, `tail`, `search`, `metadata` | Read and inspect files. |
| `file_write` | `overwrite`, `append`, `prepend`, `insert_at_line`, `find_and_replace` | Write and edit files. |
| `file` | `list`, `tree` | Directory listing and tree output without changing directories. |
| `mcp` | `list`, `call` | List and call tools on HTTP MCP servers. |

## Examples

Fetch a page:

```powershell
python run_tool.py FETCH-GET "--url https://example.com --out page.html"
```

Extract readable text from HTML:

```powershell
python run_tool.py HTML_EXTRACT "--file page.html --out page.txt"
```

Search the internet:

```powershell
python run_tool.py SEARCH-INTERNET "--query python argparse --results 10"
```

Use `--results` to request more matches:

```powershell
python run_tool.py SEARCH-INTERNET "--query python argparse --results 50"
```

Read a file with line numbers:

```powershell
python run_tool.py FILE_READ-FULL "--path script.py --include_line_numbers true"
```

Replace text in a file:

```powershell
python run_tool.py FILE_WRITE-FIND_AND_REPLACE "--path config.yaml --find version: 1.0.0 --replace version: 1.1.0 --backup true"
```

List a directory:

```powershell
python run_tool.py FILE-LIST "--path C:\ComfyClaw-Tools"
```

Show a directory tree:

```powershell
python run_tool.py FILE-TREE "--path C:\ComfyClaw-Tools --depth 2"
```

Use the browser:

```powershell
python run_tool.py BROWSER-GOTO "--url https://example.com"
python run_tool.py BROWSER-CLICK "--selector a:has-text('Login')"
python run_tool.py BROWSER-STATE ""
python run_tool.py BROWSER-END ""
```

Query a large local document:

```powershell
python run_tool.py RAGQUERYDOC-QUERY "--path TOOLS.md --query browser screenshot action --chunk-type paragraphs --chunk-size 2"
```

List tools from an HTTP MCP server:

```powershell
python run_tool.py MCP-LIST "--server https://example.com/mcp"
```

Call an MCP tool:

```powershell
python run_tool.py MCP-CALL '--server https://example.com/mcp --name search_files --arguments {"query":"budget report"}'
```

## Persistent Browser

The browser tool uses a local background server:

- `browser_server.py` owns the Playwright browser session.
- `tools/browser.py` is a thin client that sends commands to the server.
- The first browser command starts the server automatically if it is not already running.
- Browser state persists across commands until `BROWSER-END`.

This makes step-by-step browser work possible:

```powershell
python run_tool.py BROWSER-GOTO "--url https://example.com"
python run_tool.py BROWSER-TYPE "--selector #search --text playwright"
python run_tool.py BROWSER-PRESS "--selector #search --key Enter"
python run_tool.py BROWSER-STATE ""
```

## RAG Document Query

`ragquerydoc` chunks a local document, embeds the chunks with Ollama, caches the embedding bundle, and queries the cached bundle on later calls when the path and chunk settings match.

Settings live in `ragquerydoc_settings.txt`:

```text
overlap=1
before=1
after=1
topk_results=3
embedding_model=qwen3-embedding:latest
```

The default Ollama endpoint is:

```text
http://127.0.0.1:11434/api/embed
```

## MCP Support

The `mcp` tool supports HTTP MCP servers.

`MCP-LIST` performs:

```text
initialize -> notifications/initialized -> tools/list
```

`MCP-CALL` performs:

```text
initialize -> notifications/initialized -> tools/call
```

Optional arguments:

- `--token`: bearer token for Authorization.
- `--timeout`: request timeout in seconds.
- `--protocol_version`: MCP protocol version, default `2025-06-18`.

## Settings

General settings live in `settings.json`:

```json
{
  "TruncatedCharacters": 40000,
  "BrowserTimeoutMs": 10000,
  "BrowserVisibleTextChars": 20000,
  "BrowserPort": 9999,
  "BrowserHeadless": true
}
```

`TruncatedCharacters` controls large plain-text output from tools that truncate terminal output.

If a tool supports `--out`, use it to save full output to a file instead of printing everything to the terminal.

## Project Structure

```text
.
|-- run_tool.py
|-- browser_server.py
|-- settings.json
|-- ragquerydoc_settings.txt
|-- requirements.txt
|-- setup.bat
|-- TOOLS.md
|-- tools/
|   |-- browser.py
|   |-- fetch.py
|   |-- file.py
|   |-- file_read.py
|   |-- file_write.py
|   |-- html.py
|   |-- mcp.py
|   |-- pdf.py
|   |-- ragquerydoc.py
|   |-- search.py
```

## Adding a Tool

Create a new Python file in `tools/`.

Example:

```python
ACTION_ARGUMENTS = {
    "hello": {"name"},
}


def run(args: list[str]) -> str:
    action = args[0]
    if action != "hello":
        return f"Error: unknown action {action}"
    return "Hello"
```

Tool files should:

- Implement `run(args: list[str]) -> str`.
- Return plain text.
- Return errors as `Error: ...` or `ERROR: ...`.
- Catch exceptions and convert them to readable errors.
- Add `ACTION_ARGUMENTS` so agent-key calls can be parsed correctly.

## Safety Model

ComfyClaw-Tools keeps the tools raw and powerful. It does not try to be the security boundary.

If an agent is using this project, the harness should decide what is allowed before calling `run_tool.py`. That keeps the tools simple while letting the harness enforce policy, permissions, approvals, or path restrictions.

## License

Apache License 2.0. See the repository root `LICENSE`.
