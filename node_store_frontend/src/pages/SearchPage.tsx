import React, { useState, useEffect } from "react";
import {
  Container,
  Row,
  Col,
  Form,
  InputGroup,
  Spinner,
  Alert,
} from "react-bootstrap";
import { Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useDebouncedCallback } from "use-debounce";
import { nodeAPI } from "../services/api";
import {
  NodeMetadata,
  ScoredSearchResponse,
  FilterOptions,
} from "../types/index";
import { FacetedSearch } from "../components/FacetedSearch";
import { NodeCard } from "../components/NodeCard";
import "../App.css";

export const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [allNodes, setAllNodes] = useState<ScoredSearchResponse[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<FilterOptions>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performSearch = async () => {
    try {
      setLoading(true);
      setError(null);
      const results = await nodeAPI.search(searchQuery, filters);
      setAllNodes(results);
    } catch (err) {
      setError("Search failed. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const debouncedSearch = useDebouncedCallback(() => {
    void performSearch();
  }, 500);

  const immediateSearch = () => {
    debouncedSearch.cancel();
    void performSearch();
  };

  // Fetch all nodes on component mount
  // useEffect(() => {
  //   void performSearch("");
  // }, []);

  useEffect(() => {
    return () => {
      debouncedSearch.cancel();
    };
  }, [debouncedSearch]);

  const handleClearFilters = () => {
    setFilters({});
    setSearchQuery("");
    void debouncedSearch();
  };

  const handleNodeSelect = (node: NodeMetadata) => {
    navigate(`/node/${node.source_code_hash}`);
  };

  return (
    <>
      {/* Main Content */}

      <Container className="py-4">
        {/* Search Bar */}
        <Row className="mb-4">
          <Col lg={12} className="mx-auto">
            <div className="mb-3">
              <InputGroup size="lg" className="shadow-sm">
                <InputGroup.Text className="bg-light">
                  <Search size={18} />
                </InputGroup.Text>
                <Form.Control
                  placeholder="Search nodes by name, description, or functionality..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    debouncedSearch();
                  }}
                  onKeyDown={(e) => e.key === "Enter" && immediateSearch()}
                />
              </InputGroup>
            </div>
          </Col>
        </Row>

        {/* Error Alert */}
        {error && (
          <Row className="mb-3">
            <Col lg={8} className="mx-auto">
              <Alert
                variant="danger"
                onClose={() => setError(null)}
                dismissible
              >
                {error}
              </Alert>
            </Col>
          </Row>
        )}

        {/* Filters Box */}
        <Row className="mb-3">
          <Col lg={12}>
            <FacetedSearch
              nodes={allNodes}
              filters={filters}
              onFilterChange={(filterOptions) => {
                setFilters(filterOptions);
                void debouncedSearch();
              }}
              onClearFilters={handleClearFilters}
            />
          </Col>
        </Row>

        {/* Search Results */}
        <Row className="g-4">
          <Col lg={12}>
            <div className="search-results">
              {loading ? (
                <div className="text-center py-5">
                  <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </Spinner>
                  <p className="mt-3 text-muted">Loading nodes...</p>
                </div>
              ) : allNodes.length === 0 ? (
                <Alert variant="info">
                  No nodes found. Try adjusting your search query or filters.
                </Alert>
              ) : (
                <>
                  <Row className="g-3">
                    {allNodes.map((result) => (
                      <Col key={result.node.source_code_hash} md={12} lg={12}>
                        <NodeCard
                          node={result.node}
                          score={result.score}
                          onSelect={handleNodeSelect}
                        />
                      </Col>
                    ))}
                  </Row>
                </>
              )}
            </div>
          </Col>
        </Row>
      </Container>
    </>
  );
};
