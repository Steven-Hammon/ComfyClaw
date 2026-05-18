import { app } from "../../scripts/app.js";

const NODE_NAME = "JSON_to_outputs";
const OUTPUT_MODES = ["key", "value", "key/value"];
const MAX_OUTPUTS = 20;

function removeArrayItem(items, item) {
  const index = items.indexOf(item);
  if (index !== -1) {
    items.splice(index, 1);
  }
}

function moveArrayItem(items, fromIndex, toIndex) {
  if (
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= items.length ||
    toIndex >= items.length ||
    fromIndex === toIndex
  ) {
    return;
  }
  const [item] = items.splice(fromIndex, 1);
  items.splice(toIndex, 0, item);
}

function removeNodeWidget(node, widget) {
  if (!widget) {
    return;
  }
  if (typeof node.removeWidget === "function") {
    const index = (node.widgets || []).indexOf(widget);
    if (index !== -1) {
      try {
        node.removeWidget(index);
        return;
      } catch (_error) {
        // Fall through to array removal below.
      }
    }
  }

  const index = (node.widgets || []).indexOf(widget);
  if (index !== -1) {
    node.widgets.splice(index, 1);
  }
}

function resizeNode(node) {
  const [width, height] = node.computeSize();
  node.size = node.size || [width, height];
  node.size[0] = Math.max(node.size[0], width);
  node.size[1] = height;
  node.setDirtyCanvas?.(true, true);
}

function findManagedWidgets(node) {
  return (node.widgets || []).filter((widget) => widget?._jsonToOutputsManaged);
}

function clearManagedWidgets(node) {
  for (const widget of [...findManagedWidgets(node)]) {
    removeNodeWidget(node, widget);
  }
}

function ensureState(node) {
  node.properties = node.properties || {};
  if (!Array.isArray(node.properties.comfyclaw_json_to_outputs_modes)) {
    node.properties.comfyclaw_json_to_outputs_modes = ["value"];
  }
  return node.properties.comfyclaw_json_to_outputs_modes;
}

function syncStateFromWidgets(node) {
  const modes = findManagedWidgets(node)
    .filter((widget) => widget._jsonToOutputsRole === "mode")
    .sort((left, right) => left._jsonToOutputsIndex - right._jsonToOutputsIndex)
    .map((widget) => widget.value ?? "value");
  node.properties.comfyclaw_json_to_outputs_modes = modes.length ? modes : ["value"];
}

function isModeWidget(widget) {
  return Boolean(widget?._jsonToOutputsManaged && widget?._jsonToOutputsRole === "mode");
}

function moveWidgetBeforeButton(node, widget) {
  const widgets = node.widgets || [];
  removeArrayItem(widgets, widget);
  const button = widgets.find((candidate) => candidate?._jsonToOutputsRole === "button");
  const buttonIndex = button ? widgets.indexOf(button) : widgets.length;
  widgets.splice(buttonIndex, 0, widget);
}

function addModeWidget(node, index, value = "value") {
  const widget = node.addWidget(
    "combo",
    `output_${index}_mode`,
    value,
    (selected) => {
      widget.value = selected;
      syncStateFromWidgets(node);
      node.setDirtyCanvas?.(true, true);
    },
    { values: [...OUTPUT_MODES] },
  );
  widget.serializeValue = () => widget.value;
  widget._jsonToOutputsManaged = true;
  widget._jsonToOutputsRole = "mode";
  widget._jsonToOutputsIndex = index;
  moveWidgetBeforeButton(node, widget);
  return widget;
}

function addButtonWidget(node) {
  const button = node.addWidget(
    "button",
    "+ Add Output",
    null,
    () => {
      const modes = ensureState(node);
      if (modes.length >= MAX_OUTPUTS) {
        return true;
      }
      modes.push("value");
      addModeWidget(node, modes.length - 1, "value");
      syncStateFromWidgets(node);
      resizeNode(node);
      return true;
    },
    { serialize: false },
  );
  button.serialize = false;
  button._jsonToOutputsManaged = true;
  button._jsonToOutputsRole = "button";
}

function extractModesFromInfo(info) {
  const propertyModes = info?.properties?.comfyclaw_json_to_outputs_modes;
  if (Array.isArray(propertyModes) && propertyModes.length) {
    return propertyModes
      .filter((value) => typeof value === "string" && OUTPUT_MODES.includes(value))
      .slice(0, MAX_OUTPUTS);
  }

  const widgetValues = Array.isArray(info?.widgets_values) ? info.widgets_values.slice(1) : [];
  const savedModes = widgetValues
    .filter((value) => typeof value === "string" && OUTPUT_MODES.includes(value))
    .slice(0, MAX_OUTPUTS);
  return savedModes.length ? savedModes : ["value"];
}

function rebuildWidgets(node, modes = ["value"]) {
  clearManagedWidgets(node);
  node.properties = node.properties || {};
  node.properties.comfyclaw_json_to_outputs_modes = modes.slice(0, MAX_OUTPUTS);

  for (const [index, mode] of node.properties.comfyclaw_json_to_outputs_modes.entries()) {
    addModeWidget(node, index, mode);
  }
  addButtonWidget(node);
  syncStateFromWidgets(node);
  resizeNode(node);
}

function moveMode(node, index, direction) {
  const modes = [...ensureState(node)];
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= modes.length) {
    return;
  }
  moveArrayItem(modes, index, targetIndex);
  rebuildWidgets(node, modes);
}

function removeMode(node, index) {
  const modes = [...ensureState(node)];
  if (modes.length <= 1 || index < 0 || index >= modes.length) {
    return;
  }
  modes.splice(index, 1);
  rebuildWidgets(node, modes);
}

app.registerExtension({
  name: "ComfyClaw.JSONToOutputs",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) {
      return;
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      this.serialize_widgets = true;
      const result = onNodeCreated?.apply(this, arguments);
      rebuildWidgets(this, ["value"]);
      return result;
    };

    const configure = nodeType.prototype.configure;
    nodeType.prototype.configure = function (info) {
      this.serialize_widgets = true;
      const result = configure?.apply(this, arguments);
      rebuildWidgets(this, extractModesFromInfo(info));
      return result;
    };

    const onMouseDown = nodeType.prototype.onMouseDown;
    nodeType.prototype.onMouseDown = function (event) {
      this._jsonToOutputsLastMouseEvent = event;
      return onMouseDown?.apply(this, arguments);
    };

    const onMouseUp = nodeType.prototype.onMouseUp;
    nodeType.prototype.onMouseUp = function (event) {
      this._jsonToOutputsLastMouseEvent = event;
      return onMouseUp?.apply(this, arguments);
    };

    const getSlotInPosition = nodeType.prototype.getSlotInPosition;
    nodeType.prototype.getSlotInPosition = function (canvasX, canvasY) {
      const slot = getSlotInPosition?.apply(this, arguments);
      if (slot) {
        return slot;
      }

      let lastWidget = null;
      for (const widget of this.widgets || []) {
        if (!widget.last_y) {
          return slot;
        }
        if (canvasY > this.pos[1] + widget.last_y) {
          lastWidget = widget;
          continue;
        }
        break;
      }

      if (isModeWidget(lastWidget)) {
        return {
          widget: lastWidget,
          output: { type: "JSON_TO_OUTPUTS_WIDGET" },
        };
      }

      return slot;
    };

    const getSlotMenuOptions = nodeType.prototype.getSlotMenuOptions;
    nodeType.prototype.getSlotMenuOptions = function (slot) {
      if (isModeWidget(slot?.widget)) {
        const widget = slot.widget;
        const index = widget._jsonToOutputsIndex;
        const modes = [...ensureState(this)];
        const canMoveUp = index > 0;
        const canMoveDown = index < modes.length - 1;
        const canRemove = modes.length > 1;

        new LiteGraph.ContextMenu(
          [
            {
              content: "Move Up",
              disabled: !canMoveUp,
              callback: () => moveMode(this, index, -1),
            },
            {
              content: "Move Down",
              disabled: !canMoveDown,
              callback: () => moveMode(this, index, 1),
            },
            {
              content: "Remove",
              disabled: !canRemove,
              callback: () => removeMode(this, index),
            },
          ],
          {
            event: this._jsonToOutputsLastMouseEvent,
            title: "JSON_to_outputs",
          },
        );
        return undefined;
      }

      return getSlotMenuOptions?.apply(this, arguments);
    };
  },
});
