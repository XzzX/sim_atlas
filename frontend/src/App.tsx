import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { SearchPage } from "./pages/SearchPage";
import { NodePage } from "./pages/NodePage";
import { useState } from "react";

// Function to find the base subpath dynamically from the URL bar
const getDynamicBasename = () => {
  const segments = window.location.pathname.split('/');
  return segments[1] ? `/${segments[1]}` : '/';
};

function App() {
  const [searchQuery, setSearchQuery] = useState("");
  
  return (
    <Router basename={getDynamicBasename()}>
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
