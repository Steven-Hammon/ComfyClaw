"""Smoke tests for the ComfyClaw custom node package."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import pathlib
import sys
import unittest
import uuid


ROOT = pathlib.Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "test_artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)
SPEC = importlib.util.spec_from_file_location("ComfyClaw", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["ComfyClaw"] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ComfyClawSmokeTests(unittest.TestCase):
    def test_prompt_combine(self):
        node = MODULE.PromptCombine()
        combined, error = node.combine("Hello", text_2=" ", text_3="world")
        self.assertEqual(combined, "Hello world")
        self.assertEqual(error, "")

    def test_json_to_outputs(self):
        node = MODULE.JSONToOutputs()
        json_text = json.dumps(
            {
                "tool_call": {
                    "tool": "fetch",
                    "action": "get",
                    "arguments": {
                        "url": "https://example.com",
                        "out": "page.html",
                    },
                }
            }
        )
        outputs = node.json_to_outputs(
            json_text,
            output_0_mode="key",
            output_1_mode="value",
            output_2_mode="value",
            output_3_mode="key",
            output_4_mode="key/value",
            output_5_mode="key/value",
            output_6_mode="key",
        )
        self.assertEqual(outputs[0], "tool_call")
        self.assertEqual(outputs[1], "fetch")
        self.assertEqual(outputs[2], "get")
        self.assertEqual(outputs[3], "arguments")
        self.assertEqual(outputs[4], "url https://example.com")
        self.assertEqual(outputs[5], "out page.html")
        self.assertEqual(outputs[6], "")
        self.assertEqual(outputs[-1], "")

        invalid_outputs = node.json_to_outputs("{", output_0_mode="key")
        self.assertTrue(all(output == "" for output in invalid_outputs[:-1]))
        self.assertTrue(invalid_outputs[-1].startswith("Invalid JSON input: "))

        non_string_outputs = node.json_to_outputs({"not": "a string"}, output_0_mode="key")
        self.assertTrue(all(output == "" for output in non_string_outputs[:-1]))
        self.assertEqual(non_string_outputs[-1], "json_input must be a string.")

    def test_text_gate(self):
        node = MODULE.TextGate()
        result, error, is_match = node.gate("safe text", mode=False, override_text="", use_override=False, rule_1_text="rm")
        self.assertEqual(result, "safe text")
        self.assertEqual(error, "")
        self.assertFalse(is_match)
        blocked, blocked_error, blocked_match = node.gate("rm -rf /", mode=False, override_text="", use_override=False, rule_1_text="rm")
        self.assertEqual(blocked, "")
        self.assertEqual(blocked_error, "")
        self.assertTrue(blocked_match)

        blocked_override, blocked_override_error, blocked_override_match = node.gate(
            "rm -rf /",
            mode=False,
            override_text="No bad commands detected",
            use_override=True,
            rule_1_text="rm",
        )
        self.assertEqual(blocked_override, "")
        self.assertEqual(blocked_override_error, "")
        self.assertTrue(blocked_override_match)

        deny_pass_override, deny_pass_override_error, deny_pass_override_match = node.gate(
            "safe text",
            mode=False,
            override_text="No bad commands detected",
            use_override=True,
            rule_1_text="rm",
        )
        self.assertEqual(deny_pass_override, "No bad commands detected")
        self.assertEqual(deny_pass_override_error, "")
        self.assertFalse(deny_pass_override_match)

        allow_override, allow_override_error, allow_override_match = node.gate(
            "safe",
            mode=True,
            override_text="No bad commands detected",
            use_override=True,
            rule_1_text="safe",
        )
        self.assertEqual(allow_override, "No bad commands detected")
        self.assertEqual(allow_override_error, "")
        self.assertTrue(allow_override_match)

        empty_output, empty_error, empty_match = node.gate("", mode=True, override_text="override", use_override=True, rule_1_text="")
        self.assertEqual(empty_output, "override")
        self.assertEqual(empty_error, "")
        self.assertTrue(empty_match)

        non_empty_output, non_empty_error, non_empty_match = node.gate("A", mode=True, override_text="override", use_override=True, rule_1_text="")
        self.assertEqual(non_empty_output, "")
        self.assertEqual(non_empty_error, "")
        self.assertFalse(non_empty_match)

    def test_route_default_branch(self):
        node = MODULE.Route()
        outputs = node.route("hello", default_branch=2, branch_1_rule="bye")
        self.assertEqual(outputs[1], "hello")
        self.assertEqual(outputs[-2], 2)
        self.assertEqual(outputs[-1], "")

        outputs = node.route("hello world", branch_1_rule="hello", branch_3_rule="world")
        self.assertEqual(outputs[0], "hello world")
        self.assertEqual(outputs[2], "hello world")
        self.assertEqual(outputs[-2], 1)
        self.assertEqual(outputs[-1], "")

        outputs = node.route("hello", branch_1_rule="bye")
        self.assertEqual(outputs[-2], 0)
        self.assertEqual(outputs[-1], "")

        route_module = sys.modules["ComfyClaw.route"]
        outputs = node.route("hello world", block_mode="block", branch_1_rule="hello", branch_2_rule="bye")
        self.assertEqual(outputs[0], "hello world")
        self.assertIsInstance(outputs[1], route_module.ExecutionBlocker)
        self.assertEqual(outputs[-2], 1)
        self.assertEqual(outputs[-1], "")

    def test_boolean_output_switch(self):
        node = MODULE.BooleanOutputSwitch()
        switch_module = sys.modules["ComfyClaw.boolean_output_switch"]

        on_true, on_false, index, error = node.switch_output({"payload": 1}, False)
        self.assertIsInstance(on_true, switch_module.ExecutionBlocker)
        self.assertEqual(on_false, {"payload": 1})
        self.assertEqual(index, 1)
        self.assertEqual(error, "")

        on_true, on_false, index, error = node.switch_output(["payload"], True)
        self.assertEqual(on_true, ["payload"])
        self.assertIsInstance(on_false, switch_module.ExecutionBlocker)
        self.assertEqual(index, 0)
        self.assertEqual(error, "")

        on_true, on_false, index, error = node.switch_output("payload", "True")
        self.assertIsInstance(on_true, switch_module.ExecutionBlocker)
        self.assertIsInstance(on_false, switch_module.ExecutionBlocker)
        self.assertIsInstance(index, switch_module.ExecutionBlocker)
        self.assertEqual(error, "boolean must be a boolean.")

    def test_or_and(self):
        node = MODULE.OrAnd()

        output, error = node.evaluate_logic("And", input_1=True, input_2=True, input_3=True)
        self.assertTrue(output)
        self.assertEqual(error, "")

        output, error = node.evaluate_logic("And", input_1=True, input_2=False, input_3=True)
        self.assertFalse(output)
        self.assertEqual(error, "")

        output, error = node.evaluate_logic("Or", input_1=False, input_2=False, input_3=True)
        self.assertTrue(output)
        self.assertEqual(error, "")

        output, error = node.evaluate_logic("Or", input_1=False, input_2=False)
        self.assertFalse(output)
        self.assertEqual(error, "")

        output, error = node.evaluate_logic("Or", input_1=True, input_2="true")
        self.assertFalse(output)
        self.assertEqual(error, "input_2 must be a boolean.")

        output, error = node.evaluate_logic("Or", input_3="true")
        self.assertFalse(output)
        self.assertEqual(error, "input_3 must be a boolean.")

        output, error = node.evaluate_logic("Neither", input_1=True)
        self.assertFalse(output)
        self.assertEqual(error, "operation must be Or or And.")

    def test_trigger(self):
        node = MODULE.Trigger()
        self.assertEqual(node.trigger("ready"), ("", True))
        self.assertEqual(node.trigger({"payload": 1}), ("", True))
        self.assertEqual(node.trigger(False), ("", True))
        self.assertEqual(node.trigger(""), ("", False))
        self.assertEqual(node.trigger(None), ("", False))

    def test_file_read_write_roundtrip(self):
        writer = MODULE.FileWrite()
        reader = MODULE.FileRead()
        path = ARTIFACTS_DIR / f"sample_{uuid.uuid4().hex}.txt"
        output_text, error = writer.write_file(str(path), "saved", "overwrite", "done")
        self.assertEqual(output_text, "done")
        self.assertEqual(error, "")
        file_text, read_error = reader.read_file(str(path))
        self.assertEqual(file_text, "saved")
        self.assertEqual(read_error, "")

    def test_file_read_is_always_changed(self):
        self.assertTrue(math.isnan(MODULE.FileRead.IS_CHANGED("same_path.txt")))

    def test_has_changed_tracks_file_modified_date(self):
        node = MODULE.HasChanged()
        data_file = ARTIFACTS_DIR / f"has_changed_{uuid.uuid4().hex}.json"
        file_to_check = ARTIFACTS_DIR / f"watched_{uuid.uuid4().hex}.txt"
        data_file.write_text("{}", encoding="utf-8")
        file_to_check.write_text("first", encoding="utf-8")
        os.utime(file_to_check, (1_700_000_000.123456, 1_700_000_000.123456))

        has_changed, last_modified, error = node.check_has_changed(str(data_file), str(file_to_check))
        self.assertTrue(has_changed)
        self.assertTrue(last_modified)
        self.assertEqual(error, "")

        store = json.loads(data_file.read_text(encoding="utf-8"))
        file_key = file_to_check.resolve().as_posix()
        self.assertEqual(store["FILE_MODIFY_DATES"][file_key], last_modified)

        has_changed, same_last_modified, error = node.check_has_changed(str(data_file), str(file_to_check))
        self.assertFalse(has_changed)
        self.assertEqual(same_last_modified, last_modified)
        self.assertEqual(error, "")

        os.utime(file_to_check, (1_700_000_060.654321, 1_700_000_060.654321))
        has_changed, updated_last_modified, error = node.check_has_changed(str(data_file), str(file_to_check))
        self.assertTrue(has_changed)
        self.assertNotEqual(updated_last_modified, last_modified)
        self.assertEqual(error, "")

        updated_store = json.loads(data_file.read_text(encoding="utf-8"))
        self.assertEqual(updated_store["FILE_MODIFY_DATES"][file_key], updated_last_modified)

    def test_has_changed_errors(self):
        node = MODULE.HasChanged()
        data_file = ARTIFACTS_DIR / f"has_changed_errors_{uuid.uuid4().hex}.json"
        file_to_check = ARTIFACTS_DIR / f"watched_errors_{uuid.uuid4().hex}.txt"
        data_file.write_text("{}", encoding="utf-8")
        file_to_check.write_text("first", encoding="utf-8")

        has_changed, last_modified, error = node.check_has_changed(str(data_file.with_suffix(".missing")), str(file_to_check))
        self.assertFalse(has_changed)
        self.assertEqual(last_modified, "")
        self.assertIn("File not found:", error)

        has_changed, last_modified, error = node.check_has_changed(str(data_file), str(file_to_check.with_suffix(".missing")))
        self.assertFalse(has_changed)
        self.assertEqual(last_modified, "")
        self.assertIn("File not found:", error)

        invalid_data_file = ARTIFACTS_DIR / f"has_changed_invalid_{uuid.uuid4().hex}.json"
        invalid_data_file.write_text("{", encoding="utf-8")
        has_changed, last_modified, error = node.check_has_changed(str(invalid_data_file), str(file_to_check))
        self.assertFalse(has_changed)
        self.assertEqual(last_modified, "")
        self.assertTrue(error.startswith("Invalid JSON file: "))

    def test_text_cleaner_only_applies_matching_markers(self):
        node = MODULE.TextCleaner()
        output, error = node.clean_text("middle", "START", "END")
        self.assertEqual(output, "middle")
        self.assertIn("start_text was not found.", error)
        self.assertIn("end_text was not found.", error)
        trimmed_output, trimmed_error = node.clean_text("STARTmiddleEND", "START", "END", include_start_end=False)
        self.assertEqual(trimmed_output, "middle")
        self.assertEqual(trimmed_error, "")
        newline_output, newline_error = node.clean_text("A\nB\nC", "A\\n", "\\nC")
        self.assertEqual(newline_output, "A\nB\nC")
        self.assertEqual(newline_error, "")

        missing_start_output, missing_start_error = node.clean_text("<TOOL>: FILE_LIST", "```markdown", "", include_start_end=False)
        self.assertEqual(missing_start_output, "<TOOL>: FILE_LIST")
        self.assertEqual(missing_start_error, "start_text was not found.")

        include_missing_start_output, include_missing_start_error = node.clean_text(
            "<TOOL>: FILE_LIST\n```",
            "```markdown",
            "```",
            include_start_end=True,
        )
        self.assertEqual(include_missing_start_output, "<TOOL>: FILE_LIST\n```")
        self.assertEqual(include_missing_start_error, "start_text was not found.")

        exclude_missing_start_output, exclude_missing_start_error = node.clean_text(
            "<TOOL>: FILE_LIST\n```",
            "```markdown",
            "```",
            include_start_end=False,
        )
        self.assertEqual(exclude_missing_start_output, "<TOOL>: FILE_LIST\n")
        self.assertEqual(exclude_missing_start_error, "start_text was not found.")

    def test_string_find_replace(self):
        node = MODULE.StringFindReplace()
        replaced, error = node.replace_text("Hello world", "world", "there")
        self.assertEqual(replaced, "Hello there")
        self.assertEqual(error, "")

        removed_newline, newline_error = node.replace_text("line 1\nline 2", "\\n", " ")
        self.assertEqual(removed_newline, "line 1 line 2")
        self.assertEqual(newline_error, "")

        inserted_newline, inserted_error = node.replace_text("alpha--beta", "--", "\\n")
        self.assertEqual(inserted_newline, "alpha\nbeta")
        self.assertEqual(inserted_error, "")

    def test_any_to_something(self):
        node = MODULE.AnyToSomething()

        self.assertEqual(node.convert_any("TRUE"), ("TRUE", "", "", True, ""))
        self.assertEqual(node.convert_any("false"), ("false", "", "", False, ""))
        self.assertEqual(node.convert_any(1.5), ("1.5", 2, 1.5, "", ""))
        self.assertEqual(node.convert_any("1.5"), ("1.5", 2, 1.5, "", ""))
        self.assertEqual(node.convert_any(1.5, "floor"), ("1.5", 1, 1.5, "", ""))
        self.assertEqual(node.convert_any("1.50", "round half-up"), ("1.50", 2, 1.5, "", ""))
        self.assertEqual(node.convert_any("1.50", "round half-down"), ("1.50", 1, 1.5, "", ""))
        self.assertEqual(node.convert_any(7), ("7", 7, 7.0, "", ""))
        self.assertEqual(node.convert_any("hello"), ("hello", "", "", "", ""))

    def test_large_input_widget_limits(self):
        chunk_inputs = MODULE.ChunkSplitter.INPUT_TYPES()["required"]
        self.assertEqual(chunk_inputs["main_chunk_min"][1]["max"], 999999)
        self.assertEqual(chunk_inputs["chunk_limit_min"][1]["max"], 999999)
        self.assertEqual(chunk_inputs["chunk_limit_max"][1]["max"], 999999)
        self.assertEqual(chunk_inputs["chunk_overlap_min"][1]["max"], 999999)

        llm_inputs = MODULE.LLMCall.INPUT_TYPES()["required"]
        self.assertEqual(llm_inputs["max_output_tokens"][1]["max"], 999999)

        random_inputs = MODULE.RandomFromList.INPUT_TYPES()["required"]
        self.assertEqual(random_inputs["seed"][1]["max"], 999999999999999)

    def test_node_categories_and_names(self):
        self.assertIn("Chunk_Splitter", MODULE.NODE_CLASS_MAPPINGS)
        self.assertIn("YAML_Read", MODULE.NODE_CLASS_MAPPINGS)
        self.assertIn("YAML_To_JSON", MODULE.NODE_CLASS_MAPPINGS)
        self.assertIn("JSON_To_YAML", MODULE.NODE_CLASS_MAPPINGS)
        self.assertIn("JSON_TO_Markdown", MODULE.NODE_CLASS_MAPPINGS)
        self.assertIn("Markdown_TO_JSON", MODULE.NODE_CLASS_MAPPINGS)
        self.assertIn("String_To_Escaped_JSON", MODULE.NODE_CLASS_MAPPINGS)
        self.assertIn("Escaped_JSON_To_String", MODULE.NODE_CLASS_MAPPINGS)
        self.assertIn("Tool_Caller", MODULE.NODE_CLASS_MAPPINGS)
        self.assertNotIn("CC_ChunkSplitter", MODULE.NODE_CLASS_MAPPINGS)
        self.assertEqual(MODULE.ChunkSplitter.CATEGORY, "ComfyClaw/Embedding")
        self.assertEqual(MODULE.JSONRead.CATEGORY, "ComfyClaw/JSON")
        self.assertEqual(MODULE.YAMLRead.CATEGORY, "ComfyClaw/YAML")
        self.assertEqual(MODULE.YAMLToJSON.CATEGORY, "ComfyClaw/YAML")
        self.assertEqual(MODULE.JSONToYAML.CATEGORY, "ComfyClaw/YAML")
        self.assertEqual(MODULE.JSONToMarkdown.CATEGORY, "ComfyClaw/JSON")
        self.assertEqual(MODULE.MarkdownToJSON.CATEGORY, "ComfyClaw/JSON")
        self.assertEqual(MODULE.StringToEscapedJSON.CATEGORY, "ComfyClaw/JSON")
        self.assertEqual(MODULE.EscapedJSONToString.CATEGORY, "ComfyClaw/JSON")
        self.assertEqual(MODULE.EmbeddingBundleToJSON.CATEGORY, "ComfyClaw/JSON")
        self.assertEqual(MODULE.EmbeddingQueryToJSON.CATEGORY, "ComfyClaw/JSON")
        self.assertEqual(MODULE.BooleanOutputSwitch.CATEGORY, "ComfyClaw/Utility")
        self.assertEqual(MODULE.OrAnd.CATEGORY, "ComfyClaw/Utility")
        self.assertEqual(MODULE.Trigger.CATEGORY, "ComfyClaw/Utility")
        self.assertEqual(MODULE.AnyToSomething.CATEGORY, "ComfyClaw/Utility")
        self.assertEqual(MODULE.PreviewAnyAsText.CATEGORY, "ComfyClaw/Utility")
        self.assertEqual(MODULE.RandomFromList.CATEGORY, "ComfyClaw/Core")
        self.assertEqual(MODULE.ToolCaller.CATEGORY, "ComfyClaw/System")

    def test_preview_any_as_text(self):
        node = MODULE.PreviewAnyAsText()
        result = node.preview("", 2)
        self.assertEqual(result["result"], ())
        self.assertEqual(result["ui"]["preview_text"], ['""'])
        self.assertEqual(result["ui"]["display_time"], [2])
        self.assertEqual(result["ui"]["default_text"], ["Waiting for trigger"])

        result = node.preview({"payload": 1}, -5)
        self.assertEqual(json.loads(result["ui"]["preview_text"][0]), {"payload": 1})
        self.assertEqual(result["ui"]["display_time"], [0])

        result = node.preview("ready", "soon")
        self.assertEqual(result["ui"]["preview_text"], ["ready"])
        self.assertEqual(result["ui"]["display_time"], [3])

    def test_json_nodes(self):
        cleaner = MODULE.JSONCleaner()
        cleaned, error = cleaner.clean_json("prefix {\"a\": [1]} suffix")
        self.assertEqual(error, "")

        reader = MODULE.JSONRead()
        key, value_text, value_json, key_value_json, read_error = reader.read_value(cleaned, "a.0", 0, "key_path")
        self.assertEqual((key, value_text, value_json, json.loads(key_value_json), read_error), ("0", "1", "1", {"0": 1}, ""))

        object_json = json.dumps({"first_word": "Hello", "second_word": ["World"], "third_word": "!!!!"})
        counter = MODULE.JSONCountKeys()
        key_count, count_error = counter.count_keys(object_json, "", "Root")
        self.assertEqual((key_count, count_error), (3, ""))

        nested_json = json.dumps(
            {
                "tool_call": {
                    "tool": "fetch",
                    "action": "get",
                    "arguments": {
                        "url": "https://example.com",
                        "out": "page.html",
                    },
                }
            }
        )
        root_count, root_count_error = counter.count_keys(nested_json, "", "Root")
        self.assertEqual((root_count, root_count_error), (1, ""))
        all_count, all_count_error = counter.count_keys(nested_json, "", "All")
        self.assertEqual((all_count, all_count_error), (6, ""))

        tool_call_root_count, tool_call_root_error = counter.count_keys(nested_json, "tool_call", "Root")
        self.assertEqual((tool_call_root_count, tool_call_root_error), (3, ""))
        tool_call_all_count, tool_call_all_error = counter.count_keys(nested_json, "tool_call", "All")
        self.assertEqual((tool_call_all_count, tool_call_all_error), (5, ""))

        arguments_root_count, arguments_root_error = counter.count_keys(nested_json, "tool_call.arguments", "Root")
        self.assertEqual((arguments_root_count, arguments_root_error), (2, ""))
        arguments_all_count, arguments_all_error = counter.count_keys(nested_json, "tool_call.arguments", "All")
        self.assertEqual((arguments_all_count, arguments_all_error), (2, ""))

        object_key, object_text, object_value_json, object_key_value_json, object_read_error = reader.read_value(
            object_json, "", key_count - 1, "index"
        )
        self.assertEqual(object_read_error, "")
        self.assertEqual(object_key, "third_word")
        self.assertEqual(object_text, "!!!!")
        self.assertEqual(json.loads(object_value_json), "!!!!")
        self.assertEqual(json.loads(object_key_value_json), {"third_word": "!!!!"})

        first_object_key, first_object_text, first_object_value_json, _, first_object_read_error = reader.read_value(
            object_json, "", 0, "index"
        )
        self.assertEqual(first_object_read_error, "")
        self.assertEqual(first_object_key, "first_word")
        self.assertEqual(first_object_text, "Hello")
        self.assertEqual(json.loads(first_object_value_json), "Hello")
        _, _, _, _, missing_index_error = reader.read_value(object_json, "", 9, "index")
        self.assertEqual(missing_index_error, "Key path not found: ")

        read_sample = json.dumps(
            {
                "TASK0": {"ONE": "151", "TWO": "152"},
                "TASK1": {"ONE": "251", "TWO": "252"},
                "TASK2": "351",
                "TASK3": "352",
            }
        )
        task_key, task_text, task_json, task_key_value_json, task_error = reader.read_value(read_sample, "TASK2", 99, "key_path")
        self.assertEqual((task_key, task_text, json.loads(task_json), task_error), ("TASK2", "351", "351", ""))
        self.assertEqual(json.loads(task_key_value_json), {"TASK2": "351"})
        task_key, task_text, task_json, _, task_error = reader.read_value(read_sample, "", 3, "index", "root")
        self.assertEqual((task_key, task_text, json.loads(task_json), task_error), ("TASK3", "352", "352", ""))
        task_key, task_text, task_json, _, task_error = reader.read_value(read_sample, "TASK0", 1, "index", "root")
        self.assertEqual((task_key, task_text, json.loads(task_json), task_error), ("TWO", "152", "152", ""))
        task_key, task_text, task_json, _, task_error = reader.read_value(read_sample, "", 0, "index", "leaves")
        self.assertEqual((task_key, task_text, json.loads(task_json), task_error), ("ONE", "151", "151", ""))

        deep_read_sample = json.dumps(
            {
                "TASK0": {
                    "ONE": {"Num1": "151", "Num2": "161"},
                    "TWO": {"Num1": "152", "Num2": "162"},
                },
                "TASK1": "88",
            }
        )
        deep_key, deep_text, deep_json, _, deep_error = reader.read_value(deep_read_sample, "TASK0", 1, "index", "root")
        self.assertEqual(deep_error, "")
        self.assertEqual(deep_key, "TWO")
        self.assertEqual(json.loads(deep_text), {"Num1": "152", "Num2": "162"})
        self.assertEqual(json.loads(deep_json), {"Num1": "152", "Num2": "162"})
        deep_key, deep_text, deep_json, _, deep_error = reader.read_value(deep_read_sample, "TASK0", 0, "index", "leaves")
        self.assertEqual((deep_key, deep_text, json.loads(deep_json), deep_error), ("Num1", "151", "151", ""))

        all_index_sample = json.dumps(
            {
                "ROOT0": {
                    "BRANCH1": {
                        "BRANCH2": {
                            "LEAF3": "A151",
                            "LEAF4": "B151",
                        }
                    }
                },
                "ROOT5": "C1",
            }
        )
        all_key, all_text, all_json, _, all_error = reader.read_value(all_index_sample, "", 2, "index", "all")
        self.assertEqual(all_error, "")
        self.assertEqual(all_key, "BRANCH2")
        self.assertEqual(json.loads(all_text), {"LEAF3": "A151", "LEAF4": "B151"})
        self.assertEqual(json.loads(all_json), {"LEAF3": "A151", "LEAF4": "B151"})
        all_key, all_text, all_json, _, all_error = reader.read_value(all_index_sample, "", 3, "index", "all")
        self.assertEqual((all_key, all_text, json.loads(all_json), all_error), ("LEAF3", "A151", "A151", ""))

        path_all_sample = json.dumps(
            {
                "TASKA": {
                    "ROOT0": {
                        "BRANCH1": {
                            "LEAF2": "A151",
                            "LEAF3": "B151",
                        }
                    }
                },
                "TASKB": "C1",
            }
        )
        path_all_key, path_all_text, path_all_json, _, path_all_error = reader.read_value(path_all_sample, "TASKA", 0, "index", "all")
        self.assertEqual(path_all_error, "")
        self.assertEqual(path_all_key, "ROOT0")
        self.assertEqual(json.loads(path_all_text), {"BRANCH1": {"LEAF2": "A151", "LEAF3": "B151"}})
        self.assertEqual(json.loads(path_all_json), {"BRANCH1": {"LEAF2": "A151", "LEAF3": "B151"}})

        finder = MODULE.JSONFindFirstLast()
        found_key, found_value, find_error = finder.find_pair(
            json.dumps({"step_1": "123-start", "step_2": "almost <COMPLETE>", "step_3": "done <COMPLETE>"}),
            "Last",
            "Value",
            "Does",
            "Contains",
            "<COMPLETE>",
        )
        self.assertEqual((found_key, found_value, find_error), ("step_3", "done <COMPLETE>", ""))

        not_prefix_key, not_prefix_value, not_prefix_error = finder.find_pair(
            json.dumps({"step_1": "123-start", "step_2": "123-middle", "step_3": "done"}),
            "Last",
            "Value",
            "Doesn't",
            "Starts With",
            "123",
        )
        self.assertEqual((not_prefix_key, not_prefix_value, not_prefix_error), ("step_3", "done", ""))

        first_key_match, first_key_value, first_key_error = finder.find_pair(
            json.dumps({"alpha": "A", "beta": "B", "alphabet": "C"}),
            "First",
            "Key",
            "Does",
            "Starts With",
            "alph",
        )
        self.assertEqual((first_key_match, first_key_value, first_key_error), ("alpha", "A", ""))

        _, _, no_match_error = finder.find_pair(object_json, "First", "Value", "Does", "Equals", "missing")
        self.assertEqual(no_match_error, "No matching root key/value pair found.")

        inserter = MODULE.JSONInsertKey()
        inserted, insert_error = inserter.insert_key(
            json.dumps({"first_word": "Hello", "third_word": "!!!!"}),
            "",
            1,
            "second_word",
            '["World"]',
            "before",
            "index",
        )
        self.assertEqual(insert_error, "")
        self.assertEqual(list(json.loads(inserted).keys()), ["first_word", "second_word", "third_word"])
        self.assertEqual(json.loads(inserted)["second_word"], ["World"])

        inserted_numeric_key, inserted_numeric_key_error = inserter.insert_key(
            json.dumps({"first_word": "Hello"}),
            "first_word",
            0,
            "1775386472",
            '"World"',
            "after",
            "key_path",
        )
        self.assertEqual(inserted_numeric_key_error, "")
        self.assertEqual(list(json.loads(inserted_numeric_key).keys()), ["first_word", "1775386472"])
        self.assertEqual(json.loads(inserted_numeric_key)["1775386472"], "World")

        nested_inserted, nested_insert_error = inserter.insert_key(
            json.dumps({"scene": {"word_3": "A"}, "sequence": {"word_3": "B"}}),
            "sequence.word_3",
            0,
            "chapter.word_1",
            '"Start"',
            "after",
            "key_path",
        )
        self.assertEqual(nested_insert_error, "")
        self.assertEqual(list(json.loads(nested_inserted).keys()), ["scene", "sequence"])
        self.assertEqual(list(json.loads(nested_inserted)["sequence"].keys()), ["word_3", "chapter"])
        self.assertEqual(json.loads(nested_inserted)["sequence"]["chapter"], {"word_1": "Start"})

        _, duplicate_insert_error = inserter.insert_key(
            json.dumps({"scene": {"word_3": "A"}, "sequence": {"word_3": "B"}}),
            "sequence.word_3",
            0,
            "word_3",
            '"C"',
            "after",
            "key_path",
        )
        self.assertEqual(duplicate_insert_error, "Key already exists at target path: word_3")

        path_inserted, path_insert_error = inserter.insert_key(
            json.dumps(
                {
                    "TASK0": {
                        "ONE": {"Num1": "151", "Num2": "161"},
                        "TWO": {"Num1": "152", "Num2": "162"},
                    },
                    "TASK1": "88",
                }
            ),
            "TASK0.ONE",
            1,
            "AA",
            "BB",
            "after",
            "index",
        )
        self.assertEqual(path_insert_error, "")
        self.assertEqual(list(json.loads(path_inserted)["TASK0"]["ONE"].keys()), ["Num1", "Num2", "AA"])
        self.assertEqual(json.loads(path_inserted)["TASK0"]["ONE"]["AA"], "BB")

        before_nested_inserted, before_nested_insert_error = inserter.insert_key(
            json.dumps(
                {
                    "TASK0": {
                        "ONE": {
                            "Num1": {"A": "A151", "B": "B151"},
                            "Num2": {"A": "A161", "B": "B161"},
                        }
                    }
                }
            ),
            "TASK0.ONE.Num2",
            0,
            "AA",
            "BB",
            "before",
            "key_path",
        )
        self.assertEqual(before_nested_insert_error, "")
        self.assertEqual(list(json.loads(before_nested_inserted)["TASK0"]["ONE"].keys()), ["Num1", "AA", "Num2"])
        self.assertEqual(json.loads(before_nested_inserted)["TASK0"]["ONE"]["AA"], "BB")

        appender = MODULE.JSONAppend()
        appended, append_error = appender.append_value(
            json.dumps({"Okay": "Working"}),
            "<EVENT>1776180872",
            '{"hmmm": "Working?"}',
        )
        self.assertEqual(append_error, "")
        self.assertEqual(
            json.loads(appended),
            {"Okay": "Working", "<EVENT>1776180872": {"hmmm": "Working?"}},
        )

        numeric_key_appended, numeric_key_append_error = appender.append_value("{}", "1775386472", "2")
        self.assertEqual(numeric_key_append_error, "")
        self.assertEqual(json.loads(numeric_key_appended), {"1775386472": 2})

        array_appended, array_append_error = appender.append_value("{}", "Maybe", '["Okay"]')
        self.assertEqual(array_append_error, "")
        self.assertEqual(json.loads(array_appended), {"Maybe": ["Okay"]})

        nested_appended, nested_append_error = appender.append_value("{}", "chapter.word_1", '"Start"')
        self.assertEqual(nested_append_error, "")
        self.assertEqual(json.loads(nested_appended), {"chapter": {"word_1": "Start"}})

        path_appended, path_append_error = appender.append_value(
            json.dumps(
                {
                    "TASK0": {
                        "ONE": {"Num1": "151", "Num2": "161"},
                        "TWO": {"Num1": "152", "Num2": "162"},
                    },
                    "TASK1": "88",
                }
            ),
            "TASK0.new",
            "BB",
        )
        self.assertEqual(path_append_error, "")
        self.assertEqual(list(json.loads(path_appended)["TASK0"].keys()), ["ONE", "TWO", "new"])
        self.assertEqual(json.loads(path_appended)["TASK0"]["new"], "BB")

        _, duplicate_append_error = appender.append_value(json.dumps({"Okay": "Working"}), "Okay.next", '"Nope"')
        self.assertEqual(duplicate_append_error, "Value at key_path is not a JSON object: Okay")

        editor = MODULE.JSONEdit()
        edited, edit_error = editor.edit_value(cleaned, "a.0", "9")
        self.assertEqual(edit_error, "")

        remover = MODULE.JSONRemoveEntry()
        removed, remove_error = remover.remove_entry(edited, "a.0", 0, "key_path")
        self.assertEqual(remove_error, "")
        self.assertEqual(json.loads(removed), {"a": []})

        object_json = json.dumps({"first_word": "Hello", "second_word": ["World"], "third_word": "!!!!"})
        removed_object, remove_object_error = remover.remove_entry(object_json, "", 0, "index")
        self.assertEqual(remove_object_error, "")
        self.assertEqual(json.loads(removed_object), {"second_word": ["World"], "third_word": "!!!!"})
        _, missing_remove_error = remover.remove_entry(object_json, "", 9, "index")
        self.assertEqual(missing_remove_error, "Key path not found: ")

    def test_yaml_nodes(self):
        yaml_common = sys.modules["ComfyClaw.yaml_common"]
        if yaml_common.yaml is None:
            self.skipTest("PyYAML is not installed")

        yaml_text = "KEY1:\n  SUBKEY: |-\n    Hello\n"
        reader = MODULE.YAMLRead()
        key, value_text, value_yaml, key_value_yaml, read_error = reader.read_value(yaml_text, "KEY1.SUBKEY", 0, "key_path")
        self.assertEqual((key, value_text, read_error), ("SUBKEY", "Hello", ""))
        self.assertEqual(value_yaml, "Hello\n")
        self.assertIn("SUBKEY: Hello", key_value_yaml)

        key, value_text, value_yaml, key_value_yaml, read_error = reader.read_value(yaml_text, "KEY1", 0, "key_path")
        self.assertEqual((key, read_error), ("KEY1", ""))
        self.assertEqual(json.loads(value_text), {"SUBKEY": "Hello"})
        self.assertIn("KEY1:", key_value_yaml)
        self.assertIn("SUBKEY: Hello", key_value_yaml)

        yaml_to_json = MODULE.YAMLToJSON()
        json_output, yaml_to_json_error = yaml_to_json.convert_yaml(yaml_text)
        self.assertEqual(yaml_to_json_error, "")
        self.assertEqual(json.loads(json_output), {"KEY1": {"SUBKEY": "Hello"}})

        original = {"KEY1": {"SUBKEY": 'Hello,\nHow is the "C:\\Workspace" directory going?'}}
        yaml_output, json_to_yaml_error = MODULE.JSONToYAML().convert_json(json.dumps(original))
        self.assertEqual(json_to_yaml_error, "")
        self.assertIn("SUBKEY: |", yaml_output)
        roundtrip_json, roundtrip_error = yaml_to_json.convert_yaml(yaml_output)
        self.assertEqual(roundtrip_error, "")
        self.assertEqual(json.loads(roundtrip_json), original)

    def test_markdown_json_nodes(self):
        json_input = (
            "{\n"
            '  "#FILE_WRITE-OVERWRITE": {\n'
            '    "CONTENT_(args):": "`--path` required.",\n'
            '    "SUMMARY:": "Replaces entire file.",\n'
            '    "```markdown": "",\n'
            '    "<TOOL>:": "FILE_WRITE-OVERWRITE",\n'
            '    "<CONTENT>:": "--path C:\\\\Claw\\\\Workspace\\\\report.txt --content Full report content.\\nExtra \\"Information\\".",\n'
            '    "```": ""\n'
            "  },\n"
            '  "#---": "",\n'
            '  "#SLEEP": {\n'
            '    "CONTENT_(args):": "empty string, nothing.",\n'
            '    "##EXAMPLE:": {\n'
            '      "```markdown": "",\n'
            '      "<TOOL>:": "SLEEP",\n'
            '      "<CONTENT>:": "",\n'
            '      "```": ""\n'
            "    }\n"
            "  },\n"
            '  "#---": ""\n'
            "}\n"
        )
        markdown_output, markdown_error = MODULE.JSONToMarkdown().convert_json(json_input)
        self.assertEqual(markdown_error, "")
        self.assertEqual(
            markdown_output,
            "#FILE_WRITE-OVERWRITE\n"
            "CONTENT_(args): `--path` required.\n"
            "SUMMARY: Replaces entire file.\n"
            "```markdown\n"
            "<TOOL>: FILE_WRITE-OVERWRITE\n"
            "<CONTENT>: --path C:\\\\Claw\\\\Workspace\\\\report.txt --content Full report content.\\nExtra \\\"Information\\\".\n"
            "```\n"
            "\n"
            "#---\n"
            "\n"
            "#SLEEP\n"
            "CONTENT_(args): empty string, nothing.\n"
            "\n"
            "##EXAMPLE:\n"
            "```markdown\n"
            "<TOOL>: SLEEP\n"
            "<CONTENT>:\n"
            "```\n"
            "\n"
            "#---\n",
        )

        markdown_input = (
            "#SLEEP\n"
            "CONTENT_(args): empty string, nothing.\n"
            "SUMMARY: This allows you to wait for instructions.\n"
            "ESCAPED: Hello\\n\\\"There\\\"\n"
            "###EXAMPLE:\n"
            "```markdown\n"
            "<TOOL>: SLEEP\n"
            "<CONTENT>:\n"
            "```\n"
            "\n"
            "#---\n"
            "#---\n"
        )
        json_output, json_error = MODULE.MarkdownToJSON().convert_markdown(markdown_input)
        self.assertEqual(json_error, "")
        self.assertEqual(json_output.count('"#---": ""'), 2)
        self.assertEqual(
            json.loads(json_output),
            {
                "#SLEEP": {
                    "CONTENT_(args):": "empty string, nothing.",
                    "SUMMARY:": "This allows you to wait for instructions.",
                    "ESCAPED:": 'Hello\n"There"',
                    "###EXAMPLE:": {
                        "```markdown": "",
                        "<TOOL>:": "SLEEP",
                        "<CONTENT>:": "",
                        "```": "",
                    },
                },
                "#---": "",
            },
        )

    def test_escaped_json_string_nodes(self):
        story = 'Hello,\nHow is the "C:\\Workspace" directory going?'
        escaped, escape_error = MODULE.StringToEscapedJSON().escape_string(story)
        self.assertEqual(escape_error, "")
        self.assertEqual(escaped, 'Hello,\\nHow is the \\"C:\\\\Workspace\\" directory going?')

        plain, unescape_error = MODULE.EscapedJSONToString().unescape_json(escaped)
        self.assertEqual(unescape_error, "")
        self.assertEqual(plain, story)

        quoted_plain, quoted_unescape_error = MODULE.EscapedJSONToString().unescape_json(f'"{escaped}"')
        self.assertEqual(quoted_unescape_error, "")
        self.assertEqual(quoted_plain, story)

    def test_json_cleaner_repairs_common_jsonish_input(self):
        cleaner = MODULE.JSONCleaner()
        jsonish = """```json
        {
          foo: 'bar',
          active: True,
          empty: None,
          // upstream comment
          values: [1, 2,],
          path: "C:\\agents\\Tools.md",
        """
        cleaned, error = cleaner.clean_json(jsonish)
        parsed = json.loads(cleaned)

        self.assertEqual(
            parsed,
            {
                "foo": "bar",
                "active": True,
                "empty": None,
                "values": [1, 2],
                "path": r"C:\agents\Tools.md",
            },
        )
        self.assertIn("JSON repaired:", error)
        self.assertIn("quoted unquoted keys", error)
        self.assertIn("balanced brackets", error)

    def test_json_cleaner_salvages_valid_prefix(self):
        cleaner = MODULE.JSONCleaner()
        cleaned, error = cleaner.clean_json('{"good": {"value": 1}, "broken": nope')
        parsed = json.loads(cleaned)

        self.assertEqual(parsed, {"good": {"value": 1}})
        self.assertIn("partially salvaged JSON", error)

    def test_json_cleaner_always_returns_valid_json(self):
        cleaner = MODULE.JSONCleaner()
        null_cleaned, null_error = cleaner.clean_json("null")
        self.assertIsNone(json.loads(null_cleaned))
        self.assertEqual(null_error, "")

        cleaned, error = cleaner.clean_json("there is no json here")

        self.assertEqual(json.loads(cleaned), {})
        self.assertIn("returned empty JSON object", error)

    def test_json_mass_nodes(self):
        sample = json.dumps(
            {
                "1234": {"NUMKEY": "1"},
                "2345": {"NUMKEY": "5"},
                "INDENT": {"3456": {"NUMKEY": "8"}},
            }
        )

        mass_math = MODULE.JSONMassMath()
        json_output, lowest_value, error = mass_math.mass_math(sample, "NUMKEY", "add", 5, 0, 999)
        self.assertEqual(error, "")
        self.assertEqual(lowest_value, 6)
        self.assertEqual(
            json.loads(json_output),
            {
                "1234": {"NUMKEY": "6"},
                "2345": {"NUMKEY": "10"},
                "INDENT": {"3456": {"NUMKEY": "13"}},
            },
        )

        mass_math_keys = MODULE.JSONMassMathKeys()
        source = json.dumps(
            {
                "1234": {"NUMKEY": "4"},
                "INDENT": {"3456": {"NUMKEY": "2"}},
            }
        )
        keyed_output, keyed_error = mass_math_keys.mass_math_keys(sample, "subtract", source, 0, 4)
        self.assertEqual(keyed_error, "")
        self.assertEqual(
            json.loads(keyed_output),
            {
                "1234": {"NUMKEY": "0"},
                "2345": {"NUMKEY": "5"},
                "INDENT": {"3456": {"NUMKEY": "4"}},
            },
        )

        mass_remove = MODULE.JSONMassRemove()
        remove_sample = json.dumps(
            {
                "1234": {"NUMKEY": "6"},
                "2345": {"NUMKEY": "10"},
                "INDENT": {"3456": {"NUMKEY": "13"}},
            }
        )
        removed_output, remove_error = mass_remove.mass_remove(remove_sample, 2, "NUMKEY", "<", 11)
        self.assertEqual(remove_error, "")
        self.assertEqual(list(json.loads(removed_output).keys()), ["2345", "INDENT"])

        removed_output, remove_error = mass_remove.mass_remove(remove_sample, 1, "NUMKEY", ">", 9)
        self.assertEqual(remove_error, "")
        self.assertEqual(json.loads(removed_output), {"1234": {"NUMKEY": "6"}})

        _, _, invalid_math_error = mass_math.mass_math("{", "NUMKEY", "add", 1, 0, 10)
        self.assertTrue(invalid_math_error.startswith("Invalid JSON input: "))
        _, remove_root_error = mass_remove.mass_remove("[]", 1, "NUMKEY", "<", 10)
        self.assertEqual(remove_root_error, "Root JSON is not a JSON object.")

    def test_json_tally_found_keys(self):
        node = MODULE.JSONTallyFoundKeys()
        source = json.dumps(
            {
                "1234": {"irrelevant": "", "also_irrelevant": ""},
                "2345": {"irrelevant": "", "also_irrelevant": ""},
            }
        )
        destination = json.dumps(
            {
                "5432": {"NUMKEY": "7"},
                "2345": {"NUMKEY": "5"},
            }
        )

        output, error = node.tally_found_keys(source, destination, "NUMKEY")
        self.assertEqual(error, "")
        self.assertEqual(
            json.loads(output),
            {
                "5432": {"NUMKEY": "7"},
                "2345": {"NUMKEY": "6"},
                "1234": {"NUMKEY": "1"},
            },
        )

        nested_destination = json.dumps({"1234": {"stats": {"NUMKEY": "1"}}, "2345": {}})
        nested_output, nested_error = node.tally_found_keys(source, nested_destination, "stats.NUMKEY")
        self.assertEqual(nested_error, "")
        self.assertEqual(
            json.loads(nested_output),
            {
                "1234": {"stats": {"NUMKEY": "2"}},
                "2345": {"stats": {"NUMKEY": "1"}},
            },
        )

        _, invalid_error = node.tally_found_keys(source, json.dumps({"1234": {"NUMKEY": "five"}}), "NUMKEY")
        self.assertEqual(invalid_error, "Value at 1234.NUMKEY must be an integer.")

    def test_embedding_query_to_json(self):
        node = MODULE.EmbeddingQueryToJSON()
        query_result = json.dumps(
            {
                "query_text": "Black holes",
                "results": [
                    {
                        "rank": 1,
                        "chunk_index": 0,
                        "score": 0.486509,
                        "chunk_text": json.dumps(
                            {
                                "<MEM>1777888748": {
                                    "SUMMARY": "Paper list found.",
                                    "MEMORY_IMPORTANCE": "55",
                                }
                            }
                        ),
                    },
                    {
                        "rank": 2,
                        "chunk_index": 9,
                        "score": 0.444009,
                        "chunk_text": json.dumps(
                            {
                                "<MEM>1777889288": {
                                    "SUMMARY": "Third paper downloaded.",
                                    "MEMORY_IMPORTANCE": "44",
                                }
                            }
                        ),
                    },
                ],
            }
        )

        json_output, error = node.convert_query(query_result)
        self.assertEqual(error, "")
        self.assertEqual(
            json.loads(json_output),
            {
                "<MEM>1777888748": {
                    "SUMMARY": "Paper list found.",
                    "MEMORY_IMPORTANCE": "55",
                },
                "<MEM>1777889288": {
                    "SUMMARY": "Third paper downloaded.",
                    "MEMORY_IMPORTANCE": "44",
                },
            },
        )

        duplicate_result = json.loads(query_result)
        duplicate_result["results"][1]["chunk_text"] = duplicate_result["results"][0]["chunk_text"]
        _, duplicate_error = node.convert_query(json.dumps(duplicate_result))
        self.assertEqual(duplicate_error, "Duplicate root key found in result 1: <MEM>1777888748")

    def test_chunk_splitter(self):
        node = MODULE.ChunkSplitter()

        paragraph_text = "One.\n\nTwo.\n\nThree."
        paragraph_chunks_text, paragraph_chunks_json, paragraph_error = node.split_text(
            paragraph_text,
            main_chunk_min=1,
            main_chunk_split_type="paragraphs",
            chunk_limit_min=1,
            chunk_limit_max=2,
            chunk_limit_split_type="paragraphs",
            chunk_overlap_min=0,
            chunk_overlap_split_type="paragraphs",
        )
        paragraph_chunks = json.loads(paragraph_chunks_json)
        self.assertEqual(paragraph_error, "")
        self.assertEqual(len(paragraph_chunks), 3)
        self.assertEqual(paragraph_chunks[1].strip(), "Two.")
        self.assertIn("---CHUNK_BREAK---", paragraph_chunks_text)

        custom_text = "INT. HOUSE\nAction A\nEXT. STREET\nAction B\nINT. CAR\nAction C"
        custom_chunks_text, custom_chunks_json, custom_error = node.split_text(
            custom_text,
            main_chunk_min=1,
            main_chunk_split_type="custom",
            main_chunk_marker_1="INT. ",
            main_chunk_marker_2="EXT. ",
            chunk_limit_min=1,
            chunk_limit_max=500,
            chunk_limit_split_type="characters",
            chunk_overlap_min=1,
            chunk_overlap_split_type="custom",
            chunk_overlap_marker_1="INT. ",
            chunk_overlap_marker_2="EXT. ",
        )
        custom_chunks = json.loads(custom_chunks_json)
        self.assertEqual(custom_error, "")
        self.assertEqual(len(custom_chunks), 3)
        self.assertTrue(custom_chunks[0].startswith("INT. HOUSE"))
        self.assertIn("EXT. STREET", custom_chunks[0])
        self.assertNotIn("INT. CAR", custom_chunks[0])
        self.assertTrue(custom_chunks[1].startswith("EXT. STREET"))
        self.assertIn("INT. CAR", custom_chunks[1])
        self.assertEqual(custom_chunks[2], "INT. CAR\nAction C")
        self.assertIn("---CHUNK_BREAK---", custom_chunks_text)

        word_text = "one two three four five six"
        limited_chunks_text, limited_chunks_json, limited_error = node.split_text(
            word_text,
            main_chunk_min=3,
            main_chunk_split_type="words",
            chunk_limit_min=1,
            chunk_limit_max=2,
            chunk_limit_split_type="words",
            chunk_overlap_min=0,
            chunk_overlap_split_type="words",
        )
        limited_chunks = json.loads(limited_chunks_json)
        self.assertEqual(limited_error, "")
        self.assertEqual([chunk.split() for chunk in limited_chunks], [["one", "two"], ["three", "four"], ["five", "six"]])
        self.assertIn("---CHUNK_BREAK---", limited_chunks_text)

    def test_embedding_and_llm_validation(self):
        embedding_node = MODULE.Embedding()
        bundle, embedding_error = embedding_node.embed_chunks(None, "", "json_list")
        self.assertEqual(bundle, "")
        self.assertTrue(embedding_error)

        provider_cls = sys.modules["ComfyClaw.providers"].EmbeddingProvider
        embedding_module = sys.modules["ComfyClaw.embedding"]
        provider = provider_cls("", "", "test-embed-model", "api")
        original_embedder = embedding_module._embed_with_provider
        embed_calls = []

        def fake_embedder(embedding_provider, text, timeout=30.0):
            embed_calls.append(text)
            return [float(len(text)), float(len(embedding_provider.model_name))]

        embedding_module._embed_with_provider = fake_embedder
        try:
            initial_bundle, initial_error = embedding_node.embed_chunks(
                provider,
                json.dumps(["first"]),
                "json_list",
                mode="Overwrite",
            )
            self.assertEqual(initial_error, "")
            self.assertEqual(json.loads(initial_bundle)["chunks"], ["first"])

            appended_bundle, appended_error = embedding_node.embed_chunks(
                provider,
                json.dumps(["second", "first"]),
                "json_list",
                mode="Append",
                embedding_bundle_string=initial_bundle,
            )
            self.assertEqual(appended_error, "")
            appended = json.loads(appended_bundle)
            self.assertEqual(appended["chunks"], ["first", "second", "first"])
            self.assertEqual(len(appended["embeddings"]), 3)

            fresh_append_bundle, fresh_append_error = embedding_node.embed_chunks(
                provider,
                json.dumps(["fresh"]),
                "json_list",
                mode="Append",
                embedding_bundle_string="",
            )
            self.assertEqual(fresh_append_error, "")
            self.assertEqual(json.loads(fresh_append_bundle)["chunks"], ["fresh"])

            object_bundle, object_bundle_error = embedding_node.embed_chunks(
                provider,
                json.dumps(
                    {
                        "<MEM>1776220001": {"SUMMARY": "Paper review"},
                        "<MEM>1776220102": {"SUMMARY": "Target audiences"},
                    }
                ),
                "json_list",
                mode="Overwrite",
            )
            self.assertEqual(object_bundle_error, "")
            object_chunks = json.loads(object_bundle)["chunks"]
            self.assertEqual(len(object_chunks), 2)
            self.assertEqual(json.loads(object_chunks[0]), {"<MEM>1776220001": {"SUMMARY": "Paper review"}})
            self.assertEqual(json.loads(object_chunks[1]), {"<MEM>1776220102": {"SUMMARY": "Target audiences"}})

            incompatible_bundle = json.loads(initial_bundle)
            incompatible_bundle["model_name"] = "other-embed-model"
            calls_before_incompatible = list(embed_calls)
            _, incompatible_error = embedding_node.embed_chunks(
                provider,
                json.dumps(["third"]),
                "json_list",
                mode="Append",
                embedding_bundle_string=json.dumps(incompatible_bundle),
            )
            self.assertEqual(incompatible_error, "Incompatible embedding_provider detected. Expected other-embed-model")
            self.assertEqual(embed_calls, calls_before_incompatible)
        finally:
            embedding_module._embed_with_provider = original_embedder

        bundle_converter = MODULE.EmbeddingBundleToJSON()
        memory_chunk = json.dumps(
            {
                "<MEM>1776221011": {
                    "SUMMARY": "Website structure",
                    "MEMORY_IMPORTANCE": "63",
                    "KEYWORDS": ["Campaign Website", "Press Kit"],
                },
                "<MEM>1776221112": {
                    "SUMMARY": "Explainer video script",
                    "MEMORY_IMPORTANCE": "60",
                    "KEYWORDS": ["Explainer Video", "Tone Strategy"],
                },
            }
        )
        second_memory_chunk = json.dumps(
            {
                "<MEM>1776224838": {
                    "SUMMARY": "Research page lookup",
                    "MEMORY_IMPORTANCE": "22",
                    "KEYWORDS": ["Ethics", "Journalism"],
                }
            }
        )
        bundle_json, bundle_json_error = bundle_converter.convert_bundle(
            json.dumps(
                {
                    "model_name": "qwen3-embedding",
                    "provider_kind": "ollama",
                    "chunks": [memory_chunk, second_memory_chunk],
                    "embeddings": [[0.1], [0.2]],
                }
            )
        )
        self.assertEqual(bundle_json_error, "")
        converted_ltm = json.loads(bundle_json)
        self.assertEqual(list(converted_ltm.keys()), ["<MEM>1776221011", "<MEM>1776221112", "<MEM>1776224838"])
        self.assertEqual(converted_ltm["<MEM>1776221112"]["SUMMARY"], "Explainer video script")

        fragmented_bundle_json, fragmented_bundle_error = bundle_converter.convert_bundle(
            json.dumps(
                {
                    "model_name": "qwen3-embedding",
                    "provider_kind": "ollama",
                    "chunks": [
                        "{\n",
                        '  "<MEM>1776220001": {"SUMMARY": "Paper review"},\n',
                        '  "<MEM>1776220102": {"SUMMARY": "Target audiences"}\n}',
                    ],
                    "embeddings": [[0.1]],
                }
            )
        )
        self.assertEqual(fragmented_bundle_error, "")
        fragmented_ltm = json.loads(fragmented_bundle_json)
        self.assertEqual(list(fragmented_ltm.keys()), ["<MEM>1776220001", "<MEM>1776220102"])
        self.assertEqual(fragmented_ltm["<MEM>1776220102"]["SUMMARY"], "Target audiences")

        _, duplicate_memory_error = bundle_converter.convert_bundle(
            json.dumps(
                {
                    "chunks": [
                        json.dumps({"<MEM>same": {"SUMMARY": "First"}}),
                        json.dumps({"<MEM>same": {"SUMMARY": "Second"}}),
                    ]
                }
            )
        )
        self.assertEqual(duplicate_memory_error, "Duplicate root key found in chunk 1: <MEM>same")

        llm_node = MODULE.LLMCall()
        response, llm_error, thinking_output = llm_node.call_llm(None, "Hello")
        self.assertEqual(response, "")
        self.assertTrue(llm_error)
        self.assertEqual(thinking_output, "")

        llm_provider_cls = sys.modules["ComfyClaw.providers"].LLMProvider
        llm_module = sys.modules["ComfyClaw.llm_call"]
        original_http_post_json = llm_module.http_post_json
        try:
            openai_payloads = []

            def fake_openai_http(url, payload, **kwargs):
                openai_payloads.append(payload)
                return (
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": "Final answer",
                                    "reasoning_content": "Reasoning trace",
                                }
                            }
                        ]
                    },
                    {},
                )

            llm_module.http_post_json = fake_openai_http
            openai_provider = llm_provider_cls("http://example.test", "key", "model", "api")
            response, llm_error, thinking_output = llm_node.call_llm(
                openai_provider,
                "Hello",
                0.1,
                12,
                1,
                "You are concise.",
            )
            self.assertEqual((response, llm_error, thinking_output), ("Final answer", "", "Reasoning trace"))
            self.assertEqual(
                openai_payloads[-1]["messages"],
                [{"role": "system", "content": "You are concise."}, {"role": "user", "content": "Hello"}],
            )

            def fake_ollama_http(url, payload, **kwargs):
                self.assertTrue(url.endswith("/api/chat"))
                return ({"message": {"content": "Done", "thinking": "Ollama thinking"}}, {})

            llm_module.http_post_json = fake_ollama_http
            ollama_provider = llm_provider_cls("http://example.test", "", "model", "ollama")
            response, llm_error, thinking_output = llm_node.call_llm(ollama_provider, "Hello", 0.1, 12, 1)
            self.assertEqual((response, llm_error, thinking_output), ("Done", "", "Ollama thinking"))

            def fake_think_tag_http(url, payload, **kwargs):
                return ({"message": {"content": "<think>Hidden-ish reasoning</think>\nVisible answer"}}, {})

            llm_module.http_post_json = fake_think_tag_http
            response, llm_error, thinking_output = llm_node.call_llm(ollama_provider, "Hello", 0.1, 12, 1)
            self.assertEqual((response, llm_error, thinking_output), ("Visible answer", "", "Hidden-ish reasoning"))

            def fake_plain_http(url, payload, **kwargs):
                return ({"choices": [{"message": {"content": "Plain answer"}}]}, {})

            llm_module.http_post_json = fake_plain_http
            response, llm_error, thinking_output = llm_node.call_llm(openai_provider, "Hello", 0.1, 12, 1)
            self.assertEqual((response, llm_error, thinking_output), ("Plain answer", "", ""))
        finally:
            llm_module.http_post_json = original_http_post_json

    def test_token_estimator(self):
        node = MODULE.TokenEstimator()
        token_count, token_text, word_text, character_count, error = node.estimate_tokens("one two three", 1.5)
        self.assertEqual((token_count, token_text, word_text, character_count, error), (4, "4", "3", 13, ""))

    def test_random_from_list_fixed(self):
        node = MODULE.RandomFromList()
        result, error = node.select_text("a", seed=1, text_2="b")
        self.assertEqual(result, "b")
        self.assertEqual(error, "")

        skipped_empty_result, skipped_empty_error = node.select_text("", seed=1, text_2="b", text_3="", text_4="d")
        self.assertEqual(skipped_empty_result, "d")
        self.assertEqual(skipped_empty_error, "")

        whitespace_result, whitespace_error = node.select_text(" ", seed=0, text_2="b")
        self.assertEqual(whitespace_result, " ")
        self.assertEqual(whitespace_error, "")

        empty_result, empty_error = node.select_text("", seed=0, text_2="")
        self.assertEqual(empty_result, "")
        self.assertEqual(empty_error, "No non-empty input strings were provided.")

    def test_timer_first_run(self):
        node = MODULE.TimerNode()
        state_path = ARTIFACTS_DIR / f"timer_{uuid.uuid4().hex}.json"
        output, error = node.evaluate_timer("tick", "interval", 1, "09:30", 0.5, str(state_path))
        self.assertEqual(output, "tick")
        self.assertEqual(error, "")

    def test_timer_reset_repairs_and_primes_state(self):
        node = MODULE.TimerNode()
        state_path = ARTIFACTS_DIR / f"timer_reset_{uuid.uuid4().hex}" / "state.json"
        reset_output, reset_error = node.evaluate_timer(
            "tick",
            "interval",
            1,
            "09:30",
            0.5,
            str(state_path),
            True,
            "timer-reset-node",
        )
        self.assertEqual(reset_output, "")
        self.assertIn("Timer state was reset.", reset_error)
        self.assertTrue(state_path.exists())

        fired_output, fired_error = node.evaluate_timer(
            "tick",
            "interval",
            1,
            "09:30",
            0.5,
            str(state_path),
            True,
            "timer-reset-node",
        )
        self.assertEqual(fired_output, "tick")
        self.assertEqual(fired_error, "")

    def test_tool_caller(self):
        tool_module = sys.modules["ComfyClaw.tool_caller"]
        tool_script = ARTIFACTS_DIR / f"run_tool_{uuid.uuid4().hex}.py"
        tool_script.write_text(
            "import json\n"
            "import sys\n"
            "import time\n"
            "\n"
            "if '--interactive' not in sys.argv:\n"
            "    print('missing interactive', flush=True)\n"
            "    sys.exit(0)\n"
            "\n"
            "counter = 0\n"
            "for line in sys.stdin:\n"
            "    counter += 1\n"
            "    raw = line.rstrip('\\n')\n"
            "    data = json.loads(raw)\n"
            "    tool = data.get('tool')\n"
            "    if tool == 'SLEEP':\n"
            "        time.sleep(2)\n"
            "        continue\n"
            "    if tool == 'PLAIN':\n"
            "        sys.stdout.write(f'plain text {counter}')\n"
            "        sys.stdout.flush()\n"
            "        continue\n"
            "    if tool == 'FAIL':\n"
            "        sys.stdout.write(json.dumps({'status': 'error', 'result': 'tool reported failure'}))\n"
            "        sys.stdout.flush()\n"
            "        continue\n"
            "    if tool == 'ECHO_RAW':\n"
            "        sys.stdout.write(json.dumps({'status': 'ok', 'result': raw}))\n"
            "        sys.stdout.flush()\n"
            "        continue\n"
            "    result = json.dumps({'counter': counter, 'data': data}, sort_keys=True)\n"
            "    sys.stdout.write(json.dumps({'status': 'ok', 'result': result}))\n"
            "    sys.stdout.flush()\n",
            encoding="utf-8",
        )

        node = MODULE.ToolCaller()
        unique_id = f"tool-caller-test-{uuid.uuid4().hex}"
        try:
            output, error = node.call_tool(
                str(tool_script),
                sys.executable,
                "FILE_WRITE-APPEND: --path C:\\Claw\\Workspace\\ToDo_List.md --content \n## Audit\n- Objective --mode append",
                True,
                5,
                unique_id,
            )
            self.assertEqual(error, "")
            parsed_output = json.loads(output)
            self.assertEqual(parsed_output["counter"], 1)
            self.assertEqual(parsed_output["data"]["tool"], "FILE_WRITE-APPEND")
            self.assertEqual(parsed_output["data"]["args"]["path"], "C:\\Claw\\Workspace\\ToDo_List.md")
            self.assertEqual(parsed_output["data"]["args"]["content"], "\n## Audit\n- Objective")
            self.assertEqual(parsed_output["data"]["args"]["mode"], "append")

            plain_output, plain_error = node.call_tool(str(tool_script), sys.executable, "PLAIN: --anything yes", True, 5, unique_id)
            self.assertEqual(plain_output, "plain text 2")
            self.assertEqual(plain_error, "")

            raw_call = '{"tool": "ECHO_RAW", "args": {"content": "\\nkept as json"}}'
            raw_output, raw_error = node.call_tool(str(tool_script), sys.executable, raw_call, False, 5, unique_id)
            self.assertEqual(raw_output, raw_call)
            self.assertEqual(raw_error, "")

            failure_output, failure_error = node.call_tool(str(tool_script), sys.executable, "FAIL: --why test", True, 5, unique_id)
            self.assertEqual(failure_output, "tool reported failure")
            self.assertEqual(failure_error, "")

            timeout_output, timeout_error = node.call_tool(str(tool_script), sys.executable, "SLEEP: --seconds 2", True, 1, unique_id)
            self.assertEqual(timeout_output, "")
            self.assertIn("tool timed out", timeout_error)
        finally:
            tool_module._close_all_sessions()

    def test_tool_caller_validation(self):
        node = MODULE.ToolCaller()
        missing_output, missing_error = node.call_tool("missing_run_tool.py", sys.executable, "TOOL: --arg value", True, 5, "missing-tool")
        self.assertEqual(missing_output, "")
        self.assertIn("tool_path not found", missing_error)

        empty_output, empty_error = node.call_tool(__file__, sys.executable, "", True, 5, "empty-tool-call")
        self.assertEqual(empty_output, "")
        self.assertEqual(empty_error, "tool_call requires an input.")

        invalid_mode_output, invalid_mode_error = node.call_tool(__file__, sys.executable, "TOOL: --arg value", "true", 5, "bad-mode")
        self.assertEqual(invalid_mode_output, "")
        self.assertEqual(invalid_mode_error, "convert_to_json must be a boolean.")

    def test_exec(self):
        exec_node = MODULE.Exec()
        unique_id = "exec-test-node"
        command_text = "ver" if os.name == "nt" else "echo hello"
        output, error = exec_node.run_command(command_text, "Current Command", 10, unique_id)
        self.assertIn(command_text, output)
        if os.name == "nt":
            self.assertIn("microsoft windows", output.lower())
            cd_output, cd_error = exec_node.run_command("cd \\", "Current Command", 10, unique_id)
            self.assertEqual(cd_error, "")
            self.assertIn(f"{pathlib.Path.cwd().drive}\\>", cd_output)
            set_output, set_error = exec_node.run_command("set COMFYCLAW_PERSIST=hello", "Current Command", 10, unique_id)
            self.assertEqual(set_error, "")
            history_output, history_error = exec_node.run_command("echo %COMFYCLAW_PERSIST%", "Entire Terminal", 10, unique_id)

            activate_path = ARTIFACTS_DIR / f"activate_prompt_{uuid.uuid4().hex}.bat"
            activate_path.write_text(
                "@echo off\n"
                "set COMFYCLAW_FAKE_VENV=active\n"
                "prompt (fakevenv) $P$G\n",
                encoding="utf-8",
            )
            activate_output, activate_error = exec_node.run_command(f'call "{activate_path.with_suffix("")}"', "Current Command", 10, unique_id)
            self.assertEqual(activate_error, "")
            self.assertIn("call", activate_output)
            venv_output, venv_error = exec_node.run_command("echo %COMFYCLAW_FAKE_VENV%", "Current Command", 10, unique_id)
            self.assertEqual(venv_error, "")
            self.assertIn("active", venv_output)
        else:
            self.assertIn("hello", output.lower())
            set_output, set_error = exec_node.run_command("export COMFYCLAW_PERSIST=hello", "Current Command", 10, unique_id)
            self.assertEqual(set_error, "")
            history_output, history_error = exec_node.run_command("printf '%s\\n' \"$COMFYCLAW_PERSIST\"", "Entire Terminal", 10, unique_id)
        self.assertEqual(error, "")
        self.assertIn("COMFYCLAW_PERSIST", set_output)
        self.assertEqual(history_error, "")
        self.assertIn("COMFYCLAW_PERSIST", history_output)
        self.assertIn("hello", history_output.lower())

        closed_output, closed_error = exec_node.run_command("exit", "Current Command", 10, unique_id)
        self.assertEqual(closed_error, "")
        self.assertIn("Shell session closed.", closed_output)

if __name__ == "__main__":
    unittest.main()











