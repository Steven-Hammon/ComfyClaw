## FETCH-GET
ARGS: `--url` required. `--out` optional.
SUMMARY: Raw HTTP GET for static content. Use for simple pages, APIs, or source HTML that does not need JavaScript.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FETCH-GET": "--url https://example.com"
}

{
  "MESSAGE-USER": "",
  "CREATE_TASK": "",
  "FETCH-GET": "--url https://example.com --out page.html"
}

---

## FETCH-DOWNLOAD
ARGS: `--url` required. `--out` required.
SUMMARY: Downloads a file as bytes and writes to `out`. Use when you already have a direct file URL.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FETCH-DOWNLOAD": "--url https://example.com/file.pdf --out file.pdf"
}

---

## HTML_EXTRACT
ARGS: `--file` or `--url` required. `--out` optional.
SUMMARY: Strips scripts/styles from HTML and returns clean readable text. Use after FETCH_GET or on any local HTML file.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "HTML_EXTRACT": "--file page.html"
}

{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "HTML_EXTRACT": "--url https://example.com --out page.txt"
}

---

## PDF-EXTRACT
ARGS: `--file` required. `--out` optional.
SUMMARY: Extracts text from a local PDF. Without `--out` returns truncated result; with `--out` saves full text.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "PDF-EXTRACT": "--file doc.pdf"
}

{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "PDF-EXTRACT": "--file report.pdf --out report.txt"
}

---

## SEARCH-INTERNET
ARGS: `--query` required. `--out` optional. `--results` optional (default: 10).
SUMMARY: Internet search via DuckDuckGo. Returns title, URL, and snippet for each result. Use `--results` to request more or fewer matches.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "SEARCH-INTERNET": "--query python argparse"
}

{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "SEARCH-INTERNET": "--query python argparse --results 50"
}

---

## BROWSER-GOTO
ARGS: `--url` required.
SUMMARY: Navigates the persistent browser to a URL. Always use this first. Returns Page State (URL, title, visible text, interactive selectors).
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "BROWSER-GOTO": "--url https://example.com"
}

---

## BROWSER-CLICK
ARGS: `--selector` required.
SUMMARY: Clicks an element on the current page. Use selectors from Page State. Returns updated Page State.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "BROWSER-CLICK": "--selector a:has-text('Login')"
}

---

## BROWSER-TYPE
ARGS: `--selector` required. `--text` required.
SUMMARY: Types text into an input on the current page. Returns updated Page State.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "BROWSER-TYPE": "--selector #search --text python playwright"
}

---

## BROWSER-PRESS
ARGS: `--selector` required. `--key` required.
SUMMARY: Presses a keyboard key on an element. Use after `type` to submit forms with Enter, or for Tab/Escape/Arrow keys.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "BROWSER-PRESS": "--selector #search --key Enter"
}

---

## BROWSER-STATE
ARGS: none.
SUMMARY: Returns current Page State without interacting. Use to inspect the page between actions.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "BROWSER-STATE": ""
}

---

## BROWSER-SCREENSHOT
ARGS: `--out` optional (default: screenshot.png).
SUMMARY: Saves a PNG of the current page. Use for visual verification after navigation or interaction.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "BROWSER-SCREENSHOT": "--out page.png"
}

---

## BROWSER-END
ARGS: none.
SUMMARY: Closes the persistent browser session. Use when the browser task is complete.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "BROWSER-END": ""
}

---

## RAGQUERYDOC-QUERY
ARGS: `--path` required. `--query` required. `--chunk-type` required (paragraphs/words). `--chunk-size` required. `--out` optional.
SUMMARY: Semantic search over a local file using cached embeddings. Use when a file is too large to read in full. Retry with different `--chunk-type` or `--chunk-size` if results are too narrow or broad.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "RAGQUERYDOC-QUERY": "--path TOOLS.md --query which action returns cookies --chunk-type paragraphs --chunk-size 2"
}

---

## FILE_READ-FULL
ARGS: `--path` required. `--encoding` optional. `--include_line_numbers` optional.
SUMMARY: Reads entire file contents. Use only for small files; prefer `slice`, `head`, or `tail` for large files.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_READ-FULL": "--path notes.txt --include_line_numbers true"
}

---

## FILE_READ-SLICE
ARGS: `--path` required. `--start_line` required. `--end_line` required. `--encoding` optional. `--include_line_numbers` optional.
SUMMARY: Reads a specific line range (1-indexed, inclusive). Use for large files when you know roughly where the content is.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_READ-SLICE": "--path server.log --start_line 120 --end_line 160 --include_line_numbers true"
}

---

## FILE_READ-HEAD
ARGS: `--path` required. `--lines` optional (default: 20). `--encoding` optional. `--include_line_numbers` optional.
SUMMARY: Reads the first N lines. Use to inspect file structure or headers before reading the rest.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_READ-HEAD": "--path config.yaml --lines 30"
}

---

## FILE_READ-TAIL
ARGS: `--path` required. `--lines` optional (default: 20). `--encoding` optional. `--include_line_numbers` optional.
SUMMARY: Reads the last N lines. Use for recent log entries or closing sections of a file.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_READ-TAIL": "--path output.log --lines 50"
}

---

## FILE_READ-SEARCH
ARGS: `--path` required. `--pattern` required. `--encoding` optional. `--include_line_numbers` optional (default: true). `--use_regex` optional (default: false).
SUMMARY: Returns only lines matching a pattern. Use to locate specific content in large files; follow up with `slice` for context.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_READ-SEARCH": "--path app.log --pattern error"
}

---

## FILE_READ-METADATA
ARGS: `--path` required.
SUMMARY: Returns file size, line count, encoding, and last modified time without reading contents. Use before deciding how to read a large file.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_READ-METADATA": "--path data.csv"
}

---

## FILE_WRITE-OVERWRITE
ARGS: `--path` required. `--content` required. `--encoding` optional. `--create_if_missing` optional (default: true). `--backup` optional (default: false).
SUMMARY: Replaces entire file with `--content`. Use for new files or complete rewrites. Set `--backup true` to save original as `.bak`.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_WRITE-OVERWRITE": "--path report.txt --content Full report content. --backup true"
}

---

## FILE_WRITE-APPEND
ARGS: `--path` required. `--content` required. `--encoding` optional. `--create_if_missing` optional (default: true).
SUMMARY: Adds `--content` to the end of a file without modifying existing content.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_WRITE-APPEND": "--path run.log --content Step 3 complete.\n"
}

---

## FILE_WRITE-PREPEND
ARGS: `--path` required. `--content` required. `--encoding` optional. `--create_if_missing` optional (default: true).
SUMMARY: Inserts `--content` at the start of a file, pushing existing content down.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_WRITE-PREPEND": "--path notes.txt --content === Updated 2025-01-15 ===\n"
}

---

## FILE_WRITE-INSERT_AT_LINE
ARGS: `--path` required. `--content` required. `--line` required. `--encoding` optional. `--backup` optional (default: false).
SUMMARY: Inserts `--content` at a specific line number, shifting existing lines down. Use FILE_READ-SEARCH first to confirm the target line.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_WRITE-INSERT_AT_LINE": "--path main.py --line 42 --content     logger.debug('Checkpoint')\n"
}

---

## FILE_WRITE-FIND_AND_REPLACE
ARGS: `--path` required. `--find` required. `--replace` required. `--encoding` optional. `--use_regex` optional (default: false). `--replace_all` optional (default: true). `--backup` optional (default: false).
SUMMARY: Replaces occurrences of `--find` with `--replace`. Safer than overwrite for targeted edits. Returns count of replacements made.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE_WRITE-FIND_AND_REPLACE": "--path config.yaml --find version:\n1.0.0 --replace version:\n1.1.0"
}

---

## MCP-LIST
ARGS: `--server` required. `--token` optional. `--timeout` optional. `--protocol_version` optional.
SUMMARY: Requests the tool manifest from an HTTP MCP server. Returns available tool names, descriptions, and input schemas. Always call this before MCP-CALL if you don't already know the server's tools.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "MCP-LIST": "--server https://example.com/mcp"
}

---

## MCP-CALL
ARGS: `--server` required. Use either `--tool` JSON or `--name` plus optional `--arguments` JSON. `--token`, `--timeout`, and `--protocol_version` optional.
SUMMARY: Sends a tool call to an HTTP MCP server using MCP initialize, initialized, then tools/call. Use MCP-LIST first to get the correct tool name and input schema. Put JSON values last when possible so the raw value is preserved cleanly.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "MCP-CALL": "--server https://example.com/mcp --tool {\"name\": \"search_files\", \"arguments\": {\"query\": \"budget report\"}}"
}

{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "MCP-CALL": "--server https://example.com/mcp --name search_files --arguments {\"query\": \"budget report\"}"
}

---

## FILE-LIST
ARGS: `--path` required.
SUMMARY: Returns the contents of a directory in standard listing format (name, size, date). Use instead of CMD dir to avoid navigating away from the current working directory.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE-LIST": "--path C:\\Users\\project"
}

---

## FILE-TREE
ARGS: `--path` required. `--depth` optional (default: 3).
SUMMARY: Returns the recursive directory structure under `--path` as an indented tree. Use `--depth` to limit how many levels deep it goes.
EXAMPLE:
{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE-TREE": "--path C:\\Users\\project"
}

{
  "MESSAGE_USER": "",
  "CREATE_TASK": "",
  "FILE-TREE": "--path C:\\Users\\project --depth 2"
}

---