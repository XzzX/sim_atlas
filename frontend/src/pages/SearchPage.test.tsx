import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route, useLocation } from "react-router";
import { http, HttpResponse } from "msw";
import { server } from "../test/msw/server";
import { linearWorkflow, suggestions } from "../test/fixtures/nodes";
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

function LocationProbe() {
  return <span data-testid="loc">{useLocation().pathname}</span>;
}

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={["/"]}>
      <LocationProbe />
      <Routes>
        <Route path="/" element={<SearchPage searchQuery="" setSearchQuery={vi.fn()} />} />
        <Route path="/node/:id" element={<div>node page</div>} />
      </Routes>
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

  it("fills the dropdown from /suggest while the results table is still loading", async () => {
    // The two paths must be genuinely independent: a slow /search must never
    // hold up the type-ahead dropdown.
    let releaseSearch!: () => void;
    const searchBlocked = new Promise<void>((resolve) => {
      releaseSearch = resolve;
    });
    server.use(
      http.post("/api/v1/search", async () => {
        await searchBlocked;
        return HttpResponse.json(responseWith("fresh_result"));
      }),
    );

    renderPage();
    await screen.findByText("Loading nodes...");

    await userEvent.type(screen.getByPlaceholderText(/search nodes/i), "add");

    expect(await screen.findByText("add")).toBeInTheDocument();
    expect(screen.getByText("Loading nodes...")).toBeInTheDocument();

    releaseSearch();
  });

  it("clicking a suggestion navigates to the node page", async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/search nodes/i), "add");
    const option = await screen.findByText("add");

    await userEvent.click(option);

    await waitFor(() => {
      expect(screen.getByTestId("loc")).toHaveTextContent(`/node/${suggestions[0].id}`);
    });
  });

  it("selecting a suggestion with the keyboard navigates to the node page", async () => {
    renderPage();
    const input = screen.getByPlaceholderText(/search nodes/i);
    await userEvent.type(input, "add");
    await screen.findByText("add");

    await userEvent.keyboard("{ArrowDown}{Enter}");

    await waitFor(() => {
      expect(screen.getByTestId("loc")).toHaveTextContent(`/node/${suggestions[0].id}`);
    });
  });

  it("renders a suggestion the server returned even if its name does not textually contain the query", async () => {
    // Pins filter={null}: the server already did the matching, so the client
    // must not re-filter (and potentially hide) what it returned.
    server.use(http.post("/api/v1/suggest", () => HttpResponse.json(suggestions)));

    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/search nodes/i), "zzz");

    expect(await screen.findByText("add")).toBeInTheDocument();
  });

  it("does not show 'No matches' before the first suggest response for the current query has landed", async () => {
    let releaseSuggest!: () => void;
    const suggestBlocked = new Promise<void>((resolve) => {
      releaseSuggest = resolve;
    });
    server.use(
      http.post("/api/v1/suggest", async () => {
        await suggestBlocked;
        return HttpResponse.json([]);
      }),
    );

    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/search nodes/i), "z");

    // Give the debounce time to fire and the popup time to open before the
    // suggest response lands — this is the window where a flash would show.
    await new Promise((resolve) => setTimeout(resolve, 200));
    expect(screen.queryByText(/no matches/i)).not.toBeInTheDocument();

    releaseSuggest();
    expect(await screen.findByText(/no matches/i)).toBeInTheDocument();
  });

  it("only queries /suggest while there is a query to suggest against", async () => {
    let suggestCalls = 0;
    server.use(
      http.post("/api/v1/suggest", () => {
        suggestCalls += 1;
        return HttpResponse.json(suggestions);
      }),
    );

    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/search nodes/i), "add");
    await screen.findByText("add");
    expect(suggestCalls).toBe(1);

    // Clearing the box back to empty must not issue another request.
    await userEvent.clear(screen.getByPlaceholderText(/search nodes/i));
    await new Promise((resolve) => setTimeout(resolve, 200));
    expect(suggestCalls).toBe(1);
  });
});
