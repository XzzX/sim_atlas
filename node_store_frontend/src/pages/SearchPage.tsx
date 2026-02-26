import React, { useState, useEffect } from "react";
import {
  Container,
  Row,
  Col,
  Form,
  InputGroup,
  Button,
  Spinner,
  Alert,
  Badge,
  Nav,
  Navbar,
} from "react-bootstrap";
import { Search, Zap } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { nodeAPI } from "../services/api";
import {
  NodeMetadata,
  ScoredSearchResponse,
  FacetFilters,
} from "../types/index";
import { FacetedSearch } from "../components/FacetedSearch";
import { NodeCard } from "../components/NodeCard";
import "../App.css";

export const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [allNodes, setAllNodes] = useState<NodeMetadata[]>([]);
  const [filteredNodes, setFilteredNodes] = useState<ScoredSearchResponse[]>(
    [],
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [filters, setFilters] = useState<FacetFilters>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch all nodes on component mount
  useEffect(() => {
    const fetchNodes = async () => {
      try {
        setLoading(true);
        setError(null);
        const nodes = await nodeAPI.listNodes();
        setAllNodes(nodes);
      } catch (err) {
        setError("Failed to load nodes. Please try again later.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchNodes();
  }, []);

  // Apply filters and search
  useEffect(() => {
    const applyFilters = () => {
      let filtered = allNodes;

      // Apply facet filters
      if (filters.nodeType && filters.nodeType.length > 0) {
        filtered = filtered.filter((node) =>
          filters.nodeType!.includes(node.node_type),
        );
      }

      if (filters.author && filters.author.length > 0) {
        filtered = filtered.filter((node) =>
          filters.author!.includes(node.author_name),
        );
      }

      if (filters.keywords && filters.keywords.length > 0) {
        filtered = filtered.filter(
          (node) =>
            node.keywords &&
            filters.keywords!.every((keyword) =>
              node.keywords!.includes(keyword),
            ),
        );
      }

      if (filters.inputDatatype && filters.inputDatatype.length > 0) {
        filtered = filtered.filter((node) =>
          node.inputs.some((input) =>
            filters.inputDatatype!.includes(input.datatype || ""),
          ),
        );
      }

      if (filters.outputDatatype && filters.outputDatatype.length > 0) {
        filtered = filtered.filter((node) =>
          node.outputs.some((output) =>
            filters.outputDatatype!.includes(output.datatype || ""),
          ),
        );
      }

      // Convert to scored format
      const scored: ScoredSearchResponse[] = filtered.map((node) => ({
        score: 1.0,
        node,
      }));

      setFilteredNodes(scored);
    };

    applyFilters();
  }, [allNodes, filters]);

  const handleSearch = async () => {
    try {
      setLoading(true);
      setError(null);

      const results = await nodeAPI.search(searchQuery);

      // Apply current filters to search results
      let filtered = results.map((r) => r.node);

      if (filters.nodeType && filters.nodeType.length > 0) {
        filtered = filtered.filter((node) =>
          filters.nodeType!.includes(node.node_type),
        );
      }

      if (filters.author && filters.author.length > 0) {
        filtered = filtered.filter((node) =>
          filters.author!.includes(node.author_name),
        );
      }

      if (filters.keywords && filters.keywords.length > 0) {
        filtered = filtered.filter(
          (node) =>
            node.keywords &&
            filters.keywords!.every((keyword) =>
              node.keywords!.includes(keyword),
            ),
        );
      }

      const scored: ScoredSearchResponse[] = results
        .filter((r) => filtered.includes(r.node))
        .sort((a, b) => b.score - a.score);

      setFilteredNodes(scored);
    } catch (err) {
      setError("Search failed. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleClearFilters = () => {
    setFilters({});
    setSearchQuery("");
  };

  const handleShowAllNodes = () => {
    setSearchQuery("");
    setFilters({});
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
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
                <Button
                  variant="primary"
                  onClick={handleSearch}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                        className="me-2"
                      />
                      Searching...
                    </>
                  ) : (
                    "Search"
                  )}
                </Button>
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

        {/* Results Section */}
        <Row className="g-4">
          {/* Filters Sidebar */}
          <Col lg={3} className="mb-4" style={{ display: "flex" }}>
            <div className="position-sticky w-100 h-100">
              <FacetedSearch
                nodes={filteredNodes.map((r) => r.node)}
                filters={filters}
                onFilterChange={setFilters}
                onClearFilters={handleClearFilters}
              />
            </div>
          </Col>

          {/* Search Results */}
          <Col lg={9}>
            <div className="search-results">
              {loading ? (
                <div className="text-center py-5">
                  <Spinner animation="border" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </Spinner>
                  <p className="mt-3 text-muted">Loading nodes...</p>
                </div>
              ) : filteredNodes.length === 0 ? (
                <Alert variant="info">
                  No nodes found. Try adjusting your search query or filters.
                </Alert>
              ) : (
                <>
                  <Row className="g-3">
                    {filteredNodes.map((result) => (
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
