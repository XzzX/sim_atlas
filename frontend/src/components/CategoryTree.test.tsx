import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CategoryTree } from "./CategoryTree";

const CATEGORY_OPTIONS: Record<string, string[]> = {
  "": ["pyiron_workflow", "math"],
  pyiron_workflow: ["node_library"],
  "pyiron_workflow>node_library": ["atomistic"],
};

describe("CategoryTree", () => {
  it("renders roots and 'All nodes', but not unexpanded descendants", () => {
    render(
      <CategoryTree category="" categoryOptions={CATEGORY_OPTIONS} onSelect={vi.fn()} />,
    );

    expect(screen.getByText("All nodes")).toBeInTheDocument();
    expect(screen.getByText("pyiron_workflow")).toBeInTheDocument();
    expect(screen.getByText("math")).toBeInTheDocument();
    expect(screen.queryByText("node_library")).not.toBeInTheDocument();
  });

  it("expands a node to reveal its children without selecting it", async () => {
    const onSelect = vi.fn();
    render(
      <CategoryTree category="" categoryOptions={CATEGORY_OPTIONS} onSelect={onSelect} />,
    );

    await userEvent.click(screen.getByRole("button", { name: /expand pyiron_workflow/i }));

    expect(screen.getByText("node_library")).toBeInTheDocument();
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("selects the full '>'-joined path when a row label is clicked, forcing it expanded", async () => {
    const onSelect = vi.fn();
    render(
      <CategoryTree category="" categoryOptions={CATEGORY_OPTIONS} onSelect={onSelect} />,
    );

    // Clicking a group selects it AND forces it expanded, revealing its children.
    await userEvent.click(screen.getByText("pyiron_workflow"));
    expect(onSelect).toHaveBeenCalledWith("pyiron_workflow");
    expect(screen.getByText("node_library")).toBeInTheDocument();

    await userEvent.click(screen.getByText("node_library"));
    expect(onSelect).toHaveBeenCalledWith("pyiron_workflow>node_library");
  });

  it("clears the selection when 'All nodes' is clicked", async () => {
    const onSelect = vi.fn();
    render(
      <CategoryTree
        category="pyiron_workflow"
        categoryOptions={CATEGORY_OPTIONS}
        onSelect={onSelect}
      />,
    );

    await userEvent.click(screen.getByText("All nodes"));
    expect(onSelect).toHaveBeenCalledWith("");
  });

  it("marks the row matching the selected category as selected", () => {
    render(
      <CategoryTree
        category="pyiron_workflow"
        categoryOptions={CATEGORY_OPTIONS}
        onSelect={vi.fn()}
      />,
    );

    const selectedRow = screen.getByText("pyiron_workflow");
    expect(selectedRow.tagName).toBe("BUTTON");
    expect(selectedRow).toHaveClass("text-primary");
    const allNodesRow = screen.getByText("All nodes");
    expect(allNodesRow.tagName).toBe("BUTTON");
    expect(allNodesRow).not.toHaveClass("text-primary");
  });
});
