import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { SearchPage } from "./pages/SearchPage";
import { NodePage } from "./pages/NodePage";
import { useState } from "react";

function App() {
  const [searchQuery, setSearchQuery] = useState("");
  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            <SearchPage
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
            />
          }
        />
        <Route path="/node/:id" element={<NodePage />} />
      </Routes>
    </Router>
  );
}

export default App;
