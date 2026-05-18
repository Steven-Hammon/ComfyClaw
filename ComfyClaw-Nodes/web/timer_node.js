import { app } from "../../scripts/app.js";

function getResetWidget(node) {
  return node.widgets?.find((widget) => widget.name === "reset");
}

function clearResetWidget(node) {
  const resetWidget = getResetWidget(node);
  if (!resetWidget || !resetWidget.value) {
    return;
  }
  resetWidget.value = false;
  node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
  name: "ComfyClaw.TimerNode",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "Timer_Node") {
      return;
    }

    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function () {
      const result = onExecuted?.apply(this, arguments);
      clearResetWidget(this);
      return result;
    };
  },
});
