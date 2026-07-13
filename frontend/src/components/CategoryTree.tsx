import React, { useState } from "react";
import { ChevronRightIcon, ChevronDownIcon } from "lucide-react";

interface CategoryTreeProps {
  category: string;
  categoryOptions: Record<string, string[]>;
  onSelect: (category: string) => void;
}

function expandAncestors(
  path: string,
  prev: Record<string, boolean>,
): Record<string, boolean> {
  if (!path) return prev;
  const next = { ...prev };
  const parts = path.split(">");
  for (let i = 1; i <= parts.length; i += 1) {
    next[parts.slice(0, i).join(">")] = true;
  }
  return next;
}

interface CategoryRowProps {
  label: string;
  depth: number;
  selected: boolean;
  hasChildren: boolean;
  expanded: boolean;
  onSelect: () => void;
  onToggle?: () => void;
}

function CategoryRow({
  label,
  depth,
  selected,
  hasChildren,
  expanded,
  onSelect,
  onToggle,
}: CategoryRowProps) {
  return (
    <div
      style={{ paddingLeft: `${8 + depth * 14}px` }}
      className={`flex w-full items-center gap-1.5 rounded-md pr-2 text-sm transition-colors ${
        selected ? "bg-primary/10 shadow-[inset_3px_0_0_var(--primary)]" : ""
      }`}
    >
      <span className="flex size-3 shrink-0 items-center justify-center">
        {hasChildren && (
          <button
            type="button"
            aria-label={expanded ? `Collapse ${label}` : `Expand ${label}`}
            aria-expanded={expanded}
            onClick={onToggle}
            className="flex size-3 items-center justify-center text-muted-foreground hover:text-foreground"
          >
            {expanded ? (
              <ChevronDownIcon className="size-3" />
            ) : (
              <ChevronRightIcon className="size-3" />
            )}
          </button>
        )}
      </span>
      <button
        type="button"
        title={label}
        onClick={onSelect}
        className={`flex-1 truncate rounded-md py-1.5 text-left transition-colors ${
          selected
            ? "font-medium text-primary"
            : hasChildren
              ? "font-medium text-foreground hover:bg-muted"
              : "text-muted-foreground hover:bg-muted"
        }`}
      >
        {label}
      </button>
    </div>
  );
}

export const CategoryTree: React.FC<CategoryTreeProps> = ({
  category,
  categoryOptions,
  onSelect,
}) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() =>
    expandAncestors(category, {}),
  );
  const [prevCategory, setPrevCategory] = useState(category);

  if (category !== prevCategory) {
    setPrevCategory(category);
    setExpanded((prev) => expandAncestors(category, prev));
  }

  const toggle = (path: string) => {
    setExpanded((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const selectPath = (path: string) => {
    onSelect(path);
    setExpanded((prev) => expandAncestors(path, prev));
  };
  const renderChildren = (parentPath: string, depth: number): React.ReactNode =>
    (categoryOptions[parentPath] ?? []).map((segment) => {
      const fullPath = parentPath ? `${parentPath}>${segment}` : segment;
      const hasChildren = (categoryOptions[fullPath] ?? []).length > 0;
      const isExpanded = !!expanded[fullPath];

      return (
        <React.Fragment key={fullPath}>
          <CategoryRow
            label={segment}
            depth={depth}
            selected={category === fullPath}
            hasChildren={hasChildren}
            expanded={isExpanded}
            onSelect={() => selectPath(fullPath)}
            onToggle={() => toggle(fullPath)}
          />
          {hasChildren && isExpanded && renderChildren(fullPath, depth + 1)}
        </React.Fragment>
      );
    });

  return (
    <div className="space-y-0.5">
      <CategoryRow
        label="All nodes"
        depth={0}
        selected={category === ""}
        hasChildren={false}
        expanded={false}
        onSelect={() => selectPath("")}
      />
      {renderChildren("", 0)}
    </div>
  );
};
