

=== INSTRUCTIONS ===

# Based on the above CONTEXT, first, work out what the current situation is; think about what is being worked on, what is it that's trying to be accomplished? Consider the later content in the CONTEXT as more important than the earlier content. With that understanding of the current situation, consider which tools are best suited for progressing.

List the Tool Names of 2-5 tools that would be useful for the next step in this process. The more obvious the tool call, the less Tool Names you need to present. The more uncertain about the next course of action, the more Tool Names you can present. Output as JSON. You Must at all costs, focus purely on outputting a JSON object that is the exact style of the Example below. You MUST at least have 1 Key of "TOOL1" and if you have more tools you wan to suggest, they MUST be "TOOL2" "TOOL3" etc. You MUST ONLY have the tool NAME in the values. Those Tool NAMES in the values will be used for the AGENT to call tools. If you do not get this right, the agent will not be able to call any tools. You must get it right so the Agent can have some tools it can call.

EXAMPLE:
{
  "TOOL1": "#FILE_READ-FULL",
  "TOOL2": "#FILE_WRITE-OVERWRITE",
  "TOOL3": "#SEND_MESSAGE",
  "TOOL4": "#SEARCH_LTM",
  "TOOL5": "#SEARCH-INTERNET"
}

List 2-5 tool names in the values of a JSON object, like how the Example above is formatted.