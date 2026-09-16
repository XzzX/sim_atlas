import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { linearWorkflow } from "../test/fixtures/artifacts";
import type { ScoredSearchResponse } from "../types/index";
import { SearchPage } from "./SearchPage";

const responseWith = (name: string): ScoredSearchResponse => ({
  results: {
    data: [{ score: 1, node: { ...linearWorkflow, id: name, name } }],
    page: 1,
    limit: 10,
    total_items: 1,
    total_pages: 1,
  },
  aggregations: null,
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <SearchPage searchQuery="" setSearchQuery={vi.fn()} />
    </MemoryRouter>,
  );

describe("SearchPage", () => {
  it("ignores a slow response that a newer search has already superseded", async () => {
    // The backend embeds the query for hybrid search, so responses can arrive
    // out of order. Here the first search is held open until after the second
    // has rendered, which is the order that used to clobber fresh results.
    let calls = 0;
    let releaseFirstSearch!: () => void;
    const firstSearchBlocked = new Promise<void>((resolve) => {
      releaseFirstSearch = resolve;
    });

    server.use(
      http.post("/api/v1/search", async () => {
        calls += 1;
        if (calls === 1) {
          await firstSearchBlocked;
          return HttpResponse.json(responseWith("stale_result"));
        }
        return HttpResponse.json(responseWith("fresh_result"));
      }),
    );

    renderPage();

    // Let the on-mount search reach the server before typing, otherwise both
    // searches collapse into a single debounce window and never overlap.
    await waitFor(() => expect(calls).toBe(1));

    await userEvent.type(screen.getByPlaceholderText(/search nodes/i), "x");
    expect(await screen.findByText("fresh_result")).toBeInTheDocument();

    releaseFirstSearch();
    await new Promise((resolve) => setTimeout(resolve, 300));

    expect(screen.getByText("fresh_result")).toBeInTheDocument();
    expect(screen.queryByText("stale_result")).not.toBeInTheDocument();
  });
});
