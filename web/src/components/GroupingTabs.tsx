import type { GroupingMode } from "../lib/types";

interface GroupingTabsProps {
  mode: GroupingMode;
  onModeChange: (mode: GroupingMode) => void;
}

export function GroupingTabs({ mode, onModeChange }: GroupingTabsProps) {
  return (
    <div className="grouping-tabs" role="tablist" aria-label="文档分组方式">
      <button
        type="button"
        role="tab"
        aria-selected={mode === "time"}
        className={`grouping-tab${mode === "time" ? " is-active" : ""}`}
        onClick={() => onModeChange("time")}
      >
        按时间
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === "industry"}
        className={`grouping-tab${mode === "industry" ? " is-active" : ""}`}
        onClick={() => onModeChange("industry")}
      >
        按行业
      </button>
    </div>
  );
}
