import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";
import { setWidgetConfig } from "../../extensions/core/widgetInputs.js";

const MATCH_TYPES = ["contains", "equals", "starts_with", "ends_with"];

const NODE_CONFIGS = {
  Prompt_Combine: {
    groups: [
      {
        key: "texts",
        kind: "text",
        prefix: "text_",
        startIndex: 2,
        addLabel: "+ Add Text",
        afterName: "text_1",
        useComfyStringWidget: true,
        multiline: true,
        attachInputSlot: true,
        defaultItems: [{ value: "" }],
      },
    ],
  },
  Text_Gate: {
    groups: [
      {
        key: "rules",
        kind: "pair",
        prefix: "rule_",
        startIndex: 1,
        addLabel: "+ Add Rule",
        afterName: "use_override",
        leftSuffix: "type",
        rightSuffix: "text",
        leftValues: MATCH_TYPES,
        leftDefault: "contains",
        rightUseComfyStringWidget: true,
        rightMultiline: true,
        attachRightInputSlot: true,
        defaultItems: [],
      },
    ],
  },
  Route: {
    groups: [
      {
        key: "branches",
        kind: "pair",
        prefix: "branch_",
        startIndex: 1,
        addLabel: "+ Add Branch",
        afterName: "block_mode",
        leftSuffix: "type",
        rightSuffix: "rule",
        leftValues: MATCH_TYPES,
        leftDefault: "contains",
        rightUseComfyStringWidget: true,
        rightMultiline: true,
        attachRightInputSlot: true,
        defaultItems: [{ left: "contains", right: "" }],
      },
    ],
  },
  Random_from_List: {
    groups: [
      {
        key: "texts",
        kind: "text",
        prefix: "text_",
        startIndex: 2,
        addLabel: "+ Add Text",
        beforeName: "seed",
        useComfyStringWidget: true,
        multiline: true,
        attachInputSlot: true,
        defaultItems: [{ value: "" }],
      },
    ],
  },
  Or_And: {
    groups: [
      {
        key: "inputs",
        kind: "boolean",
        prefix: "input_",
        startIndex: 1,
        addLabel: "+ Add Input",
        afterName: "operation",
        attachInputSlot: true,
        defaultItems: [{ value: false }],
      },
    ],
  },
};

function cloneItems(items) {
  return (items || []).map((item) => ({ ...item }));
}

function ensureNodeState(node) {
  node.properties = node.properties || {};
  if (!node.properties.comfyclaw_dynamic_state || typeof node.properties.comfyclaw_dynamic_state !== "object") {
    node.properties.comfyclaw_dynamic_state = {};
  }
  return node.properties.comfyclaw_dynamic_state;
}

function ensureGroupState(node, group) {
  const state = ensureNodeState(node);
  if (!Array.isArray(state[group.key])) {
    state[group.key] = cloneItems(group.defaultItems);
  }
  return state[group.key];
}

function removeArrayItem(items, item) {
  const index = items.indexOf(item);
  if (index !== -1) {
    items.splice(index, 1);
  }
}

function removeNodeWidget(node, widget) {
  if (!widget) {
    return;
  }
  if (typeof node.removeWidget === "function") {
    try {
      node.removeWidget(widget);
      return;
    } catch (_error) {
      const index = (node.widgets || []).indexOf(widget);
      if (index !== -1) {
        node.widgets.splice(index, 1);
      }
      return;
    }
  }

  const index = (node.widgets || []).indexOf(widget);
  if (index !== -1) {
    node.widgets.splice(index, 1);
  }
}

function removeNodeInput(node, index) {
  if (index < 0 || !node.inputs?.[index]) {
    return;
  }
  if (typeof node.removeInput === "function") {
    node.removeInput(index);
  } else {
    node.inputs.splice(index, 1);
  }
}

function getGroupMatch(group, name) {
  if (!name || typeof name !== "string") {
    return null;
  }

  if (group.kind === "pair") {
    const leftName = `_${group.leftSuffix}`;
    const rightName = `_${group.rightSuffix}`;
    let role = null;
    let numberText = "";

    if (name.startsWith(group.prefix) && name.endsWith(leftName)) {
      role = "left";
      numberText = name.slice(group.prefix.length, -leftName.length);
    } else if (name.startsWith(group.prefix) && name.endsWith(rightName)) {
      role = "right";
      numberText = name.slice(group.prefix.length, -rightName.length);
    } else {
      return null;
    }

    if (!/^\d+$/.test(numberText)) {
      return null;
    }

    const number = Number(numberText);
    if (number < group.startIndex) {
      return null;
    }

    return {
      itemIndex: number - group.startIndex,
      role,
      name,
    };
  }

  if (!name.startsWith(group.prefix)) {
    return null;
  }

  const numberText = name.slice(group.prefix.length);
  if (!/^\d+$/.test(numberText)) {
    return null;
  }

  const number = Number(numberText);
  if (number < group.startIndex) {
    return null;
  }

  return {
    itemIndex: number - group.startIndex,
    role: "value",
    name,
  };
}

function matchesDynamicGroupItem(group, item) {
  return Boolean(getGroupMatch(group, item?.name));
}

function removeDynamicWidgets(node) {
  const config = node._comfyclawConfig;
  if (!config || !node.widgets) {
    return;
  }

  for (let index = node.widgets.length - 1; index >= 0; index -= 1) {
    const widget = node.widgets[index];
    const shouldRemove =
      widget?._comfyclawManaged ||
      config.groups.some((group) => matchesDynamicGroupItem(group, widget));
    if (!shouldRemove) {
      continue;
    }
    removeNodeWidget(node, widget);
  }
}

function dedupeDynamicInputs(node) {
  const config = node._comfyclawConfig;
  if (!config || !node.inputs) {
    return;
  }

  const matchesByName = new Map();
  for (let index = 0; index < node.inputs.length; index += 1) {
    const input = node.inputs[index];
    const matchedGroup = config.groups.find((group) => matchesDynamicGroupItem(group, input));
    if (!matchedGroup) {
      continue;
    }
    const list = matchesByName.get(input.name) || [];
    list.push({ index, input });
    matchesByName.set(input.name, list);
  }

  const indexesToRemove = [];
  for (const entries of matchesByName.values()) {
    if (entries.length <= 1) {
      continue;
    }

    entries.sort((left, right) => {
      const leftScore = left.input?.link != null ? 1 : 0;
      const rightScore = right.input?.link != null ? 1 : 0;
      return rightScore - leftScore;
    });

    for (const entry of entries.slice(1)) {
      indexesToRemove.push(entry.index);
    }
  }

  indexesToRemove.sort((left, right) => right - left);
  for (const index of indexesToRemove) {
    removeNodeInput(node, index);
  }
}

function removeDisabledDynamicInputs(node) {
  const config = node._comfyclawConfig;
  if (!config || !node.inputs) {
    return;
  }

  for (let index = node.inputs.length - 1; index >= 0; index -= 1) {
    const input = node.inputs[index];
    const group = config.groups.find((group) => {
      const match = getGroupMatch(group, input?.name);
      return match && !shouldAttachInputSlot(group, match.role);
    });
    if (group) {
      removeNodeInput(node, index);
    }
  }
}

function hydrateGroupState(node, group) {
  const items = ensureGroupState(node, group);
  let maxItems = items.length;

  for (const input of node.inputs || []) {
    const match = getGroupMatch(group, input?.name);
    if (!match) {
      continue;
    }
    maxItems = Math.max(maxItems, match.itemIndex + 1);
  }

  for (const widget of node.widgets || []) {
    const match = getGroupMatch(group, widget?.name);
    if (!match) {
      continue;
    }
    maxItems = Math.max(maxItems, match.itemIndex + 1);
    while (items.length <= match.itemIndex) {
      items.push(createDefaultGroupItem(group));
    }

    if (group.kind === "pair") {
      if (match.role === "left") {
        items[match.itemIndex].left = widget.value ?? group.leftDefault;
      } else if (match.role === "right") {
        items[match.itemIndex].right = widget.value ?? "";
      }
    } else {
      items[match.itemIndex].value = widget.value ?? "";
    }
  }

  while (items.length < maxItems) {
    items.push(createDefaultGroupItem(group));
  }

  ensureNodeState(node)[group.key] = items;
}

function primeGroupStateFromInfo(node, group, info) {
  const state = ensureNodeState(node);
  const savedState = info?.properties?.comfyclaw_dynamic_state?.[group.key];
  const items = Array.isArray(savedState) ? cloneItems(savedState) : cloneItems(state[group.key] || group.defaultItems);

  let maxItems = items.length;
  for (const input of info?.inputs || []) {
    const match = getGroupMatch(group, input?.name);
    if (!match) {
      continue;
    }
    maxItems = Math.max(maxItems, match.itemIndex + 1);
  }

  while (items.length < maxItems) {
    items.push(createDefaultGroupItem(group));
  }

  state[group.key] = items;
}

function primeDynamicStateFromInfo(node, info) {
  const config = node._comfyclawConfig;
  if (!config) {
    return;
  }

  for (const group of config.groups) {
    primeGroupStateFromInfo(node, group, info);
  }
}

function removeManagedWidgets(node) {
  if (!node.widgets) {
    return;
  }
  for (let index = node.widgets.length - 1; index >= 0; index -= 1) {
    const widget = node.widgets[index];
    if (!widget?._comfyclawManaged) {
      continue;
    }
    removeNodeWidget(node, widget);
  }
}

function resizeNode(node) {
  const [width, height] = node.computeSize();
  node.size = node.size || [width, height];
  node.size[0] = Math.max(node.size[0], width);
  node.size[1] = height;
  node.setDirtyCanvas(true, true);
}

function scheduleRebuild(node) {
  if (node._comfyclawRebuildScheduled) {
    return;
  }
  node._comfyclawRebuildScheduled = true;
  setTimeout(() => {
    node._comfyclawRebuildScheduled = false;
    rebuildDynamicWidgets(node);
  }, 0);
}

function insertBlock(node, blockWidgets, group) {
  const widgets = node.widgets || [];
  for (const widget of blockWidgets) {
    removeArrayItem(widgets, widget);
  }

  let targetIndex = widgets.length;
  if (group.beforeName) {
    const beforeIndex = widgets.findIndex((widget) => widget?.name === group.beforeName);
    if (beforeIndex !== -1) {
      targetIndex = beforeIndex;
    }
  } else if (group.afterName) {
    const afterIndex = widgets.findIndex((widget) => widget?.name === group.afterName);
    if (afterIndex !== -1) {
      targetIndex = afterIndex + 1;
    }
  }

  widgets.splice(targetIndex, 0, ...blockWidgets);
}

function isManagedWidget(widget) {
  return Boolean(widget?._comfyclawManaged && !widget?._comfyclawIsButton);
}

function findNamedIndex(items, name) {
  return (items || []).findIndex((item) => item?.name === name);
}

function markInput(input, group, itemIndex, role = "value") {
  input._comfyclawManaged = true;
  input._comfyclawGroupKey = group.key;
  input._comfyclawItemIndex = itemIndex;
  input._comfyclawRole = role;
}

function markWidget(widget, group, itemIndex, role, isButton = false) {
  widget._comfyclawManaged = true;
  widget._comfyclawGroupKey = group.key;
  widget._comfyclawItemIndex = itemIndex;
  widget._comfyclawRole = role;
  widget._comfyclawIsButton = isButton;
}

function findInputIndexByName(node, name) {
  const inputs = node.inputs || [];
  for (let index = inputs.length - 1; index >= 0; index -= 1) {
    if (inputs[index]?.name === name) {
      return index;
    }
  }
  return -1;
}

function getRoleSortValue(role) {
  if (role === "left") {
    return 0;
  }
  if (role === "right") {
    return 1;
  }
  return 0;
}

function sortManagedWidgets(left, right) {
  if (left._comfyclawItemIndex !== right._comfyclawItemIndex) {
    return left._comfyclawItemIndex - right._comfyclawItemIndex;
  }
  return getRoleSortValue(left._comfyclawRole) - getRoleSortValue(right._comfyclawRole);
}

function shouldUseComfyStringWidget(group, role = "value") {
  if (group.kind === "pair") {
    return role === "right" && Boolean(group.rightUseComfyStringWidget);
  }
  return Boolean(group.useComfyStringWidget);
}

function coerceBoolean(value, fallback = false) {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    return value.trim().toLowerCase() === "true";
  }
  if (typeof value === "number") {
    return value !== 0;
  }
  return fallback;
}

function shouldAttachInputSlot(group, role = "value") {
  if (group.kind === "pair") {
    return role === "right" && Boolean(group.attachRightInputSlot);
  }
  return Boolean(group.attachInputSlot);
}

function buildManagedWidgetName(group, itemIndex, role = "value") {
  const indexNumber = group.startIndex + itemIndex;
  if (group.kind === "pair") {
    const suffix = role === "left" ? group.leftSuffix : group.rightSuffix;
    return `${group.prefix}${indexNumber}_${suffix}`;
  }
  return `${group.prefix}${indexNumber}`;
}

function getGroupItemBlocks(node, group) {
  const blocks = [];
  const groupWidgets = (node.widgets || [])
    .filter((widget) => widget?._comfyclawManaged && widget._comfyclawGroupKey === group.key && !widget._comfyclawIsButton)
    .sort(sortManagedWidgets);

  for (const widget of groupWidgets) {
    const itemIndex = widget._comfyclawItemIndex;
    if (!blocks[itemIndex]) {
      blocks[itemIndex] = { widgets: [], inputs: [] };
    }
    blocks[itemIndex].widgets.push(widget);
  }

  const groupInputs = (node.inputs || [])
    .filter((input) => input?._comfyclawManaged && input._comfyclawGroupKey === group.key)
    .sort((left, right) => left._comfyclawItemIndex - right._comfyclawItemIndex);

  for (const input of groupInputs) {
    const itemIndex = input._comfyclawItemIndex;
    if (!blocks[itemIndex]) {
      blocks[itemIndex] = { widgets: [], inputs: [] };
    }
    blocks[itemIndex].inputs.push(input);
  }

  return blocks.filter(Boolean);
}

function getGroupInputInsertIndex(node, group, inputsToInsert) {
  const inputs = node.inputs || [];
  for (const input of inputsToInsert) {
    removeArrayItem(inputs, input);
  }

  return getGroupInputTargetIndex(inputs, group);
}

function getGroupInputTargetIndex(inputs, group) {
  let targetIndex = inputs.length;
  if (group.beforeName) {
    const beforeIndex = findNamedIndex(inputs, group.beforeName);
    if (beforeIndex !== -1) {
      targetIndex = beforeIndex;
    }
  } else if (group.afterName) {
    const afterIndex = findNamedIndex(inputs, group.afterName);
    if (afterIndex !== -1) {
      targetIndex = afterIndex + 1;
    }
  }
  return targetIndex;
}

function shouldReinsertGroupInputs(node, group, inputItems) {
  if (!inputItems.length) {
    return false;
  }

  const inputs = node.inputs || [];
  const remainingInputs = inputs.filter((input) => !inputItems.includes(input));
  const targetIndex = getGroupInputTargetIndex(remainingInputs, group);

  return inputItems.some((input, itemIndex) => inputs.indexOf(input) !== targetIndex + itemIndex);
}

function applyGroupItemBlocks(node, group, blocks) {
  const widgetItems = blocks.flatMap((block) => block.widgets);
  insertWidgetsBeforeButton(node, group, widgetItems);

  const inputItems = blocks.flatMap((block) => block.inputs);
  if (inputItems.length && shouldReinsertGroupInputs(node, group, inputItems)) {
    const inputs = node.inputs || [];
    const targetIndex = getGroupInputInsertIndex(node, group, inputItems);
    inputs.splice(targetIndex, 0, ...inputItems);
  }

  blocks.forEach((block, itemIndex) => {
    block.widgets.sort((left, right) => getRoleSortValue(left._comfyclawRole) - getRoleSortValue(right._comfyclawRole));
    for (const widget of block.widgets) {
      widget._comfyclawItemIndex = itemIndex;
      widget.name = buildManagedWidgetName(group, itemIndex, widget._comfyclawRole);
    }

    for (const input of block.inputs) {
      input._comfyclawItemIndex = itemIndex;
      input.name = buildManagedWidgetName(group, itemIndex, input._comfyclawRole || "value");
      if (input.widget) {
        input.widget.name = input.name;
      }
    }
  });

  syncStateFromWidgets(node);
  resizeNode(node);
}

function createWidgetInputConfig(group, role, value) {
  if (group.kind === "boolean") {
    return [
      "BOOLEAN",
      {
        default: coerceBoolean(value?.value, false),
        label_on: "true",
        label_off: "false",
      },
    ];
  }

  if (shouldUseComfyStringWidget(group, role)) {
    return [
      "STRING",
      {
        default: value?.value ?? "",
        multiline: Boolean(group.kind === "pair" ? group.rightMultiline : group.multiline),
      },
    ];
  }
  return null;
}

function attachWidgetInput(node, group, itemIndex, role, widget, config) {
  if (!shouldAttachInputSlot(group, role) || !widget || typeof node.addInput !== "function") {
    return;
  }

  let inputIndex = findInputIndexByName(node, widget.name);
  if (inputIndex === -1) {
    node.addInput(widget.name, config?.[0] ?? "*");
    inputIndex = findInputIndexByName(node, widget.name);
  }
  if (inputIndex === -1) {
    return;
  }

  const input = node.inputs[inputIndex];
  input.type = config?.[0] ?? input.type ?? "*";
  input.label = widget.name;
  input.localized_name = widget.name;
  // Keep only lightweight widget metadata on the slot.
  // Storing the live DOM widget creates a circular reference:
  // widget -> _node -> inputs -> slot.widget -> widget
  input.widget = { name: widget.name };
  input._widget = widget;
  markInput(input, group, itemIndex, role);
  if (config) {
    try {
      setWidgetConfig(input, config);
    } catch (_error) {
      input.widget.config = config;
    }
  }
}

function createBooleanWidget(node, group, itemIndex, value) {
  const widgetName = `${group.prefix}${group.startIndex + itemIndex}`;
  const boolValue = coerceBoolean(value?.value, false);
  const config = createWidgetInputConfig(group, "value", { value: boolValue });

  const widget = node.addWidget(
    "toggle",
    widgetName,
    boolValue,
    () => {
      syncStateFromWidgets(node);
      node.setDirtyCanvas(true, true);
    },
    { on: "true", off: "false" },
  );
  widget.value = boolValue;

  markWidget(widget, group, itemIndex, "value");
  attachWidgetInput(node, group, itemIndex, "value", widget, config);
  return widget;
}

function createTextWidget(node, group, itemIndex, value) {
  const widgetName = `${group.prefix}${group.startIndex + itemIndex}`;
  const textValue = value?.value ?? "";
  const config = createWidgetInputConfig(group, "value", value);

  let widget = null;
  if (shouldUseComfyStringWidget(group, "value") && ComfyWidgets?.STRING) {
    widget = ComfyWidgets.STRING(node, widgetName, config, app)?.widget ?? null;
    if (widget) {
      widget.value = textValue;
    }
  }

  if (!widget) {
    widget = node.addWidget(
      "text",
      widgetName,
      textValue,
      () => {
        syncStateFromWidgets(node);
        node.setDirtyCanvas(true, true);
      },
      {},
    );
  } else {
    const originalCallback = widget.callback;
    widget.callback = (...args) => {
      const result = originalCallback?.apply(widget, args);
      syncStateFromWidgets(node);
      node.setDirtyCanvas(true, true);
      return result;
    };
  }

  markWidget(widget, group, itemIndex, "value");
  attachWidgetInput(node, group, itemIndex, "value", widget, config);
  return widget;
}

function createValueWidget(node, group, itemIndex, value) {
  if (group.kind === "boolean") {
    return createBooleanWidget(node, group, itemIndex, value);
  }
  return createTextWidget(node, group, itemIndex, value);
}

function createPairRightWidget(node, group, itemIndex, value) {
  const indexNumber = group.startIndex + itemIndex;
  const widgetName = `${group.prefix}${indexNumber}_${group.rightSuffix}`;
  const textValue = value?.right ?? "";
  const config = createWidgetInputConfig(group, "right", { value: textValue });

  let widget = null;
  if (shouldUseComfyStringWidget(group, "right") && ComfyWidgets?.STRING) {
    widget = ComfyWidgets.STRING(node, widgetName, config, app)?.widget ?? null;
    if (widget) {
      widget.value = textValue;
    }
  }

  if (!widget) {
    widget = node.addWidget(
      "text",
      widgetName,
      textValue,
      () => {
        syncStateFromWidgets(node);
        node.setDirtyCanvas(true, true);
      },
      {},
    );
  } else {
    const originalCallback = widget.callback;
    widget.callback = (...args) => {
      const result = originalCallback?.apply(widget, args);
      syncStateFromWidgets(node);
      node.setDirtyCanvas(true, true);
      return result;
    };
  }

  markWidget(widget, group, itemIndex, "right");
  attachWidgetInput(node, group, itemIndex, "right", widget, config);
  return widget;
}

function createPairWidgets(node, group, itemIndex, value) {
  const indexNumber = group.startIndex + itemIndex;
  const leftWidget = node.addWidget(
    "combo",
    `${group.prefix}${indexNumber}_${group.leftSuffix}`,
    value?.left ?? group.leftDefault,
    () => {
      syncStateFromWidgets(node);
      node.setDirtyCanvas(true, true);
    },
    { values: [...group.leftValues] },
  );
  markWidget(leftWidget, group, itemIndex, "left");

  const rightWidget = createPairRightWidget(node, group, itemIndex, value);

  return [leftWidget, rightWidget];
}

function createDefaultGroupItem(group) {
  if (group.kind === "pair") {
    return { left: group.leftDefault, right: "" };
  }
  if (group.kind === "boolean") {
    return { value: false };
  }
  return { value: "" };
}

function findGroupButton(node, group) {
  return (node.widgets || []).find(
    (widget) =>
      widget?._comfyclawManaged &&
      widget._comfyclawGroupKey === group.key &&
      widget._comfyclawIsButton,
  );
}

function insertWidgetsBeforeButton(node, group, widgetsToInsert) {
  const widgets = node.widgets || [];
  for (const widget of widgetsToInsert) {
    removeArrayItem(widgets, widget);
  }

  const button = findGroupButton(node, group);
  let targetIndex = button ? widgets.indexOf(button) : widgets.length;
  if (targetIndex < 0) {
    targetIndex = widgets.length;
  }

  widgets.splice(targetIndex, 0, ...widgetsToInsert);
}

function addGroupItem(node, group) {
  const groupState = ensureGroupState(node, group);
  if (groupState.length >= 20) {
    return false;
  }

  const item = createDefaultGroupItem(group);
  groupState.push(item);
  const itemIndex = groupState.length - 1;
  const widgetsToInsert =
    group.kind === "pair"
      ? createPairWidgets(node, group, itemIndex, item)
      : [createValueWidget(node, group, itemIndex, item)];

  insertWidgetsBeforeButton(node, group, widgetsToInsert);
  applyGroupItemBlocks(node, group, getGroupItemBlocks(node, group));
  return true;
}

function createAddButton(node, group) {
  const button = node.addWidget(
    "button",
    group.addLabel,
    null,
    () => {
      addGroupItem(node, group);
      return true;
    },
    { serialize: false },
  );
  button.serialize = false;
  markWidget(button, group, -1, "button", true);
  return button;
}

function syncStateFromWidgets(node) {
  const config = node._comfyclawConfig;
  if (!config) {
    return;
  }
  const state = ensureNodeState(node);
  for (const group of config.groups) {
    const groupWidgets = (node.widgets || [])
      .filter((widget) => widget?._comfyclawManaged && widget._comfyclawGroupKey === group.key && !widget._comfyclawIsButton)
      .sort((left, right) => {
        if (left._comfyclawItemIndex !== right._comfyclawItemIndex) {
          return left._comfyclawItemIndex - right._comfyclawItemIndex;
        }
        return String(left._comfyclawRole).localeCompare(String(right._comfyclawRole));
      });

    if (group.kind === "pair") {
      const items = [];
      for (const widget of groupWidgets) {
        if (!items[widget._comfyclawItemIndex]) {
          items[widget._comfyclawItemIndex] = { left: group.leftDefault, right: "" };
        }
        if (widget._comfyclawRole === "left") {
          items[widget._comfyclawItemIndex].left = widget.value;
        } else if (widget._comfyclawRole === "right") {
          items[widget._comfyclawItemIndex].right = widget.value;
        }
      }
      state[group.key] = items.filter(Boolean);
    } else {
      state[group.key] = groupWidgets
        .filter((widget) => widget._comfyclawRole === "value")
        .map((widget) => ({ value: widget.value ?? "" }));
    }
  }
}

function rebuildDynamicWidgets(node) {
  const config = node._comfyclawConfig;
  if (!config) {
    return;
  }

  dedupeDynamicInputs(node);
  for (const group of config.groups) {
    hydrateGroupState(node, group);
  }
  removeDisabledDynamicInputs(node);

  // Preserve enabled restored input slots so LiteGraph keeps their saved slot indexes and links.
  removeDynamicWidgets(node);

  for (const group of config.groups) {
    const items = ensureGroupState(node, group);
    const blockWidgets = [];
    items.slice(0, 20).forEach((item, itemIndex) => {
      if (group.kind === "pair") {
        blockWidgets.push(...createPairWidgets(node, group, itemIndex, item));
      } else {
        blockWidgets.push(createValueWidget(node, group, itemIndex, item));
      }
    });
    blockWidgets.push(createAddButton(node, group));
    insertBlock(node, blockWidgets, group);
  }

  for (const group of config.groups) {
    applyGroupItemBlocks(node, group, getGroupItemBlocks(node, group));
  }

  syncStateFromWidgets(node);
  resizeNode(node);
}

function getManagedWidgetAtPosition(node, canvasY) {
  let lastWidget = null;
  for (const widget of node.widgets || []) {
    if (!widget?.last_y) {
      continue;
    }
    if (canvasY > node.pos[1] + widget.last_y) {
      lastWidget = widget;
      continue;
    }
    break;
  }
  return isManagedWidget(lastWidget) ? lastWidget : null;
}

function moveGroupItem(node, widget, direction) {
  const config = node._comfyclawConfig;
  const group = config?.groups.find((item) => item.key === widget._comfyclawGroupKey);
  if (!group) {
    return;
  }
  const blocks = getGroupItemBlocks(node, group);
  const sourceIndex = widget._comfyclawItemIndex;
  const targetIndex = sourceIndex + direction;
  if (targetIndex < 0 || targetIndex >= blocks.length) {
    return;
  }
  const [moved] = blocks.splice(sourceIndex, 1);
  blocks.splice(targetIndex, 0, moved);
  applyGroupItemBlocks(node, group, blocks);
}

function removeGroupItem(node, widget) {
  const config = node._comfyclawConfig;
  const group = config?.groups.find((item) => item.key === widget._comfyclawGroupKey);
  if (!group) {
    return;
  }
  const blocks = getGroupItemBlocks(node, group);
  const itemIndex = widget._comfyclawItemIndex;
  if (itemIndex < 0 || itemIndex >= blocks.length) {
    return;
  }
  const [removed] = blocks.splice(itemIndex, 1);

  for (const input of removed.inputs) {
    const inputIndex = (node.inputs || []).indexOf(input);
    if (inputIndex !== -1) {
      if (typeof node.removeInput === "function") {
        node.removeInput(inputIndex);
      } else {
        node.inputs.splice(inputIndex, 1);
      }
    }
  }

  for (const managedWidget of removed.widgets) {
    removeNodeWidget(node, managedWidget);
  }

  applyGroupItemBlocks(node, group, blocks);
}

app.registerExtension({
  name: "ComfyClaw.DynamicInputs",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    const config = NODE_CONFIGS[nodeData.name];
    if (!config) {
      return;
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      this.serialize_widgets = true;
      this._comfyclawConfig = config;
      const result = onNodeCreated?.apply(this, arguments);
      ensureNodeState(this);
      scheduleRebuild(this);
      return result;
    };

    const configure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      this.serialize_widgets = true;
      this._comfyclawConfig = config;
      ensureNodeState(this);
      primeDynamicStateFromInfo(this, info);
      const result = configure?.apply(this, arguments);
      ensureNodeState(this);
      scheduleRebuild(this);
      return result;
    };

    const onGraphConfigured = nodeType.prototype.onGraphConfigured;
    nodeType.prototype.onGraphConfigured = function () {
      this.serialize_widgets = true;
      this._comfyclawConfig = config;
      ensureNodeState(this);
      rebuildDynamicWidgets(this);
      return onGraphConfigured?.apply(this, arguments);
    };

    const onMouseDown = nodeType.prototype.onMouseDown;
    nodeType.prototype.onMouseDown = function (event) {
      this._comfyclawLastMouseEvent = event;
      return onMouseDown?.apply(this, arguments);
    };

    const onMouseUp = nodeType.prototype.onMouseUp;
    nodeType.prototype.onMouseUp = function (event) {
      this._comfyclawLastMouseEvent = event;
      return onMouseUp?.apply(this, arguments);
    };

    const getSlotInPosition = nodeType.prototype.getSlotInPosition;
    nodeType.prototype.getSlotInPosition = function (canvasX, canvasY) {
      const slot = getSlotInPosition?.apply(this, arguments);
      if (slot) {
        return slot;
      }

      const widget = getManagedWidgetAtPosition(this, canvasY);
      if (widget) {
        return {
          widget,
          output: { type: "COMFYCLAW WIDGET" },
        };
      }

      return slot;
    };

    const getSlotMenuOptions = nodeType.prototype.getSlotMenuOptions;
    nodeType.prototype.getSlotMenuOptions = function (slot) {
      if (isManagedWidget(slot?.widget)) {
        const widget = slot.widget;
        const configForNode = this._comfyclawConfig;
        const group = configForNode?.groups.find((item) => item.key === widget._comfyclawGroupKey);
        const items = group ? ensureGroupState(this, group) : [];
        const canMoveUp = widget._comfyclawItemIndex > 0;
        const canMoveDown = widget._comfyclawItemIndex < items.length - 1;

        new LiteGraph.ContextMenu(
          [
            {
              content: "Move Up",
              disabled: !canMoveUp,
              callback: () => moveGroupItem(this, widget, -1),
            },
            {
              content: "Move Down",
              disabled: !canMoveDown,
              callback: () => moveGroupItem(this, widget, 1),
            },
            {
              content: "Remove",
              callback: () => removeGroupItem(this, widget),
            },
          ],
          {
            event: this._comfyclawLastMouseEvent,
            title: "ComfyClaw Input",
          },
        );
        return undefined;
      }

      return getSlotMenuOptions?.apply(this, arguments);
    };
  },
});

