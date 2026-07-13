import React, { useState } from "react";
import { ChevronRightIcon, ChevronDownIcon } from "lucide-react";

interface CategoryTreeProps {
  category: string;
  categoryOptions: Record<string, string[]>;
  onSelect: (category: string) => void;
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
      role="button"
      tabIndex={0}
      title={label}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      style={{ paddingLeft: `${8 + depth * 14}px` }}
      className={`flex w-full items-center gap-1.5 rounded-md py-1.5 pr-2 text-left text-sm transition-colors cursor-pointer ${
        selected
          ? "bg-primary/10 font-medium text-primary shadow-[inset_3px_0_0_var(--primary)]"
          : hasChildren
            ? "font-medium text-foreground hover:bg-muted"
            : "text-muted-foreground hover:bg-muted"
      }`}
    >
      <span className="flex size-3 shrink-0 items-center justify-center">
        {hasChildren && (
          <button
            type="button"
            aria-label={expanded ? `Collapse ${label}` : `Expand ${label}`}
            aria-expanded={expanded}
            onClick={(e) => {
              e.stopPropagation();
              onToggle?.();
            }}
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
      <span className="truncate">{label}</span>
    </div>
  );
}

export const CategoryTree: React.FC<CategoryTreeProps> = ({
  category,
  categoryOptions,
  onSelect,
}) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  React.useEffect(() => {
    if (!category) return;
    setExpanded((prev) => {
      const next = { ...prev };
      const parts = category.split(">");
      for (let i = 1; i <= parts.length; i += 1) {
        next[parts.slice(0, i).join(">")] = true;
      }
      return next;
    });
  }, [category]);

  const toggle = (path: string) => {
    setExpanded((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const selectPath = (path: string) => {
    onSelect(path);
    if (!path) return;
    setExpanded((prev) => {
      const next = { ...prev };
      const parts = path.split(">");
      for (let i = 1; i <= parts.length; i += 1) {
        next[parts.slice(0, i).join(">")] = true;
      }
      return next;
    });
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
