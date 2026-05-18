import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const NODE_NAME = "Preview_Any_As_Text";
const WIDGET_NAME = "preview";
const DEFAULT_TEXT = "Waiting for trigger";

function getPreviewElement(widget) {
  return widget?.inputEl || widget?.element || widget?.textarea || null;
}

function getUiValue(message, key, fallback) {
  const value = message?.[key] ?? message?.ui?.[key];
  if (Array.isArray(value)) {
    return value.length ? value[0] : fallback;
  }
  return value ?? fallback;
}

function getPreviewWidget(node) {
  return node.widgets?.find((widget) => widget.name === WIDGET_NAME);
}

function markReadonly(widget) {
  const input = getPreviewElement(widget);
  if (!input) {
    return;
  }
  input.readOnly = true;
  input.spellcheck = false;
  input.style.fontFamily = "monospace";
  input.style.resize = "none";
}

function setWidgetText(widget, text) {
  if (!widget) {
    return;
  }
  widget.value = text;
  if (widget.inputEl) {
    widget.inputEl.value = text;
  }
  if (widget.element && "value" in widget.element) {
    widget.element.value = text;
  }
}

function ensurePreviewWidget(node) {
  let widget = getPreviewWidget(node);
  if (widget) {
    markReadonly(widget);
    return widget;
  }

  widget = ComfyWidgets.STRING(node, WIDGET_NAME, ["STRING", { default: DEFAULT_TEXT, multiline: true }], app)?.widget;
  if (!widget) {
    widget = node.addWidget("text", WIDGET_NAME, DEFAULT_TEXT, () => {}, { multiline: true });
  }

  widget.serialize = false;
  widget._comfyclawPreviewAnyAsText = true;
  setWidgetText(widget, DEFAULT_TEXT);
  markReadonly(widget);
  node.setDirtyCanvas?.(true, true);
  return widget;
}

function setPreviewText(node, text) {
  const widget = ensurePreviewWidget(node);
  setWidgetText(widget, text);
  node.setDirtyCanvas?.(true, true);
}

function scheduleReset(node, displayTime, defaultText) {
  if (node._comfyclawPreviewAnyAsTextTimer) {
    clearTimeout(node._comfyclawPreviewAnyAsTextTimer);
  }

  const seconds = Number.isFinite(displayTime) ? Math.max(0, displayTime) : 3;
  node._comfyclawPreviewAnyAsTextTimer = setTimeout(() => {
    setPreviewText(node, defaultText || DEFAULT_TEXT);
    node._comfyclawPreviewAnyAsTextTimer = null;
  }, seconds * 1000);
}

app.registerExtension({
  name: "ComfyClaw.PreviewAnyAsText",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) {
      return;
    }

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      ensurePreviewWidget(this);
      return result;
    };

    const configure = nodeType.prototype.configure;
    nodeType.prototype.configure = function () {
      const result = configure?.apply(this, arguments);
      ensurePreviewWidget(this);
      return result;
    };

    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      const result = onExecuted?.apply(this, arguments);
      const defaultText = String(getUiValue(message, "default_text", DEFAULT_TEXT));
      const previewText = String(getUiValue(message, "preview_text", defaultText));
      const displayTime = Number(getUiValue(message, "display_time", 3));
      setPreviewText(this, previewText);
      scheduleReset(this, displayTime, defaultText);
      return result;
    };
  },
});
