"""ComfyUI entrypoint for the ComfyClaw custom node package."""

from .any_to_something import AnyToSomething
from .boolean_output_switch import BooleanOutputSwitch
from .chunk_splitter import ChunkSplitter
from .embedding import Embedding
from .embedding_bundle_to_json import EmbeddingBundleToJSON
from .embedding_query import EmbeddingQuery
from .embedding_query_to_json import EmbeddingQueryToJSON
from .escaped_json_to_string import EscapedJSONToString
from .exec_node import Exec
from .file_read import FileRead
from .file_write import FileWrite
from .has_changed import HasChanged
from .json_append import JSONAppend
from .json_cleaner import JSONCleaner
from .json_count_keys import JSONCountKeys
from .json_edit import JSONEdit
from .json_find_first_last import JSONFindFirstLast
from .json_insert_key import JSONInsertKey
from .json_mass_math import JSONMassMath
from .json_mass_math_keys import JSONMassMathKeys
from .json_mass_remove import JSONMassRemove
from .json_read import JSONRead
from .json_remove_entry import JSONRemoveEntry
from .json_tally_found_keys import JSONTallyFoundKeys
from .json_to_markdown import JSONToMarkdown
from .json_to_yaml import JSONToYAML
from .json_to_outputs import JSONToOutputs
from .llm_api_loader import LLMAPILoader
from .llm_call import LLMCall
from .llm_model_loader import LLMModelLoader
from .markdown_to_json import MarkdownToJSON
from .load_embedding_api import LoadEmbeddingAPI
from .load_embedding_model import LoadEmbeddingModel
from .mcp_call import MCPCall
from .mcp_list_tools import MCPListTools
from .mcp_server_loader import MCPServerLoader
from .or_and import OrAnd
from .preview_any_as_text import PreviewAnyAsText
from .prompt_combine import PromptCombine
from .random_from_list import RandomFromList
from .route import Route
from .string_find_replace import StringFindReplace
from .string_to_escaped_json import StringToEscapedJSON
from .text_cleaner import TextCleaner
from .text_gate import TextGate
from .timer_node import TimerNode
from .timestamp import Timestamp
from .tool_caller import ToolCaller
from .token_estimator import TokenEstimator
from .trigger import Trigger
from .yaml_read import YAMLRead
from .yaml_to_json import YAMLToJSON

NODE_CLASS_MAPPINGS = {
    "Boolean_Output_Switch": BooleanOutputSwitch,
    "Or_And": OrAnd,
    "Prompt_Combine": PromptCombine,
    "Text_Gate": TextGate,
    "Route": Route,
    "String_Find_Replace": StringFindReplace,
    "Any_To_Something": AnyToSomething,
    "File_Read": FileRead,
    "File_Write": FileWrite,
    "Has_Changed": HasChanged,
    "Text_Cleaner": TextCleaner,
    "JSON_Cleaner": JSONCleaner,
    "JSON_Count_keys": JSONCountKeys,
    "JSON_Read": JSONRead,
    "YAML_Read": YAMLRead,
    "YAML_To_JSON": YAMLToJSON,
    "JSON_To_YAML": JSONToYAML,
    "JSON_TO_Markdown": JSONToMarkdown,
    "Markdown_TO_JSON": MarkdownToJSON,
    "String_To_Escaped_JSON": StringToEscapedJSON,
    "Escaped_JSON_To_String": EscapedJSONToString,
    "JSON_Append": JSONAppend,
    "JSON_Edit": JSONEdit,
    "JSON_Find_First_Last": JSONFindFirstLast,
    "JSON_insert_key": JSONInsertKey,
    "JSON_Mass_Math": JSONMassMath,
    "JSON_Mass_Math_Keys": JSONMassMathKeys,
    "JSON_Mass_Remove": JSONMassRemove,
    "JSON_Remove_Entry": JSONRemoveEntry,
    "JSON_Tally_Found_Keys": JSONTallyFoundKeys,
    "JSON_to_outputs": JSONToOutputs,
    "Embedding_Query_To_JSON": EmbeddingQueryToJSON,
    "Chunk_Splitter": ChunkSplitter,
    "Load_Embedding_Model": LoadEmbeddingModel,
    "Load_Embedding_API": LoadEmbeddingAPI,
    "Embedding": Embedding,
    "Embedding_Bundle_To_JSON": EmbeddingBundleToJSON,
    "Embedding_Query": EmbeddingQuery,
    "LLM_API_Loader": LLMAPILoader,
    "LLM_Model_Loader": LLMModelLoader,
    "LLMCall": LLMCall,
    "Token_Estimator": TokenEstimator,
    "Timestamp": Timestamp,
    "Preview_Any_As_Text": PreviewAnyAsText,
    "Random_from_List": RandomFromList,
    "Timer_Node": TimerNode,
    "Tool_Caller": ToolCaller,
    "Trigger": Trigger,
    "MCP_Server_Loader": MCPServerLoader,
    "MCP_List_Tools": MCPListTools,
    "MCP_Call": MCPCall,
    "Exec": Exec,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Boolean_Output_Switch": "Boolean_Output_Switch",
    "Or_And": "Or_And",
    "Prompt_Combine": "Prompt_Combine",
    "Text_Gate": "Text_Gate",
    "Route": "Route",
    "String_Find_Replace": "String_Find_Replace",
    "Any_To_Something": "Any_To_Something",
    "File_Read": "File_Read",
    "File_Write": "File_Write",
    "Has_Changed": "Has_Changed",
    "Text_Cleaner": "Text_Cleaner",
    "JSON_Cleaner": "JSON_Cleaner",
    "JSON_Count_keys": "JSON_Count_keys",
    "JSON_Read": "JSON_Read",
    "YAML_Read": "YAML_Read",
    "YAML_To_JSON": "YAML_To_JSON",
    "JSON_To_YAML": "JSON_To_YAML",
    "JSON_TO_Markdown": "JSON_TO_Markdown",
    "Markdown_TO_JSON": "Markdown_TO_JSON",
    "String_To_Escaped_JSON": "String_To_Escaped_JSON",
    "Escaped_JSON_To_String": "Escaped_JSON_To_String",
    "JSON_Append": "JSON_Append",
    "JSON_Edit": "JSON_Edit",
    "JSON_Find_First_Last": "JSON_Find_First_Last",
    "JSON_insert_key": "JSON_insert_key",
    "JSON_Mass_Math": "JSON_Mass_Math",
    "JSON_Mass_Math_Keys": "JSON_Mass_Math_Keys",
    "JSON_Mass_Remove": "JSON_Mass_Remove",
    "JSON_Remove_Entry": "JSON_Remove_Entry",
    "JSON_Tally_Found_Keys": "JSON_Tally_Found_Keys",
    "JSON_to_outputs": "JSON_to_outputs",
    "Embedding_Query_To_JSON": "Embedding_Query_To_JSON",
    "Chunk_Splitter": "Chunk_Splitter",
    "Load_Embedding_Model": "Load_Embedding_Model",
    "Load_Embedding_API": "Load_Embedding_API",
    "Embedding": "Embedding",
    "Embedding_Bundle_To_JSON": "Embedding_Bundle_To_JSON",
    "Embedding_Query": "Embedding_Query",
    "LLM_API_Loader": "LLM_API_Loader",
    "LLM_Model_Loader": "LLM_Model_Loader",
    "LLMCall": "LLMCall",
    "Token_Estimator": "Token_Estimator",
    "Timestamp": "Timestamp",
    "Preview_Any_As_Text": "Preview_Any_As_Text",
    "Random_from_List": "Random_from_List",
    "Timer_Node": "Timer_Node",
    "Tool_Caller": "Tool_Caller",
    "Trigger": "Trigger",
    "MCP_Server_Loader": "MCP_Server_Loader",
    "MCP_List_Tools": "MCP_List_Tools",
    "MCP_Call": "MCP_Call",
    "Exec": "Exec",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
