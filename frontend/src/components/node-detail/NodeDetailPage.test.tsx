import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { NodeDetailPage } from "./NodeDetailPage";
import { linearWorkflow } from "@/test/fixtures/artifacts";

describe("NodeDetailPage", () => {
  it("loads execution results from the (mocked) API and renders them", async () => {
    render(
      <MemoryRouter initialEntries={["/node/wf-linear-0001?tab=executions"]}>
        <NodeDetailPage node={linearWorkflow} />
      </MemoryRouter>,
    );

    // header renders from the node prop
    expect(screen.getByText("linear")).toBeInTheDocument();

    // executions tab badge resolves once MSW responds and Zod parsing in api.ts succeeds
    const executionsTab = await screen.findByRole("tab", { name: /executions/i });
    expect(executionsTab).toHaveTextContent("3");
    expect(await screen.findByText(/of 3 executions/)).toBeInTheDocument();
  });
});
