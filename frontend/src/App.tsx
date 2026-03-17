import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { SearchPage } from "./pages/SearchPage";
import { DetailPage } from "./pages/DetailPage";
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
        <Route path="/node/:nodeHash" element={<DetailPage />} />
      </Routes>
    </Router>
  );
}

export default App;
