import React, { useMemo, useState } from "react";
import { Form, Button, Row, Col, Card, Collapse } from "react-bootstrap";
import { Typeahead } from "react-bootstrap-typeahead";
import { NodeType, FilterOptions, ScoredSearchResponse } from "../types/index";
import { X } from "lucide-react";

interface FacetedSearchProps {
  nodes: ScoredSearchResponse[];
  filters: FilterOptions;
  onFilterChange: (filters: FilterOptions) => void;
  onClearFilters: () => void;
}

export const FacetedSearch: React.FC<FacetedSearchProps> = ({
  nodes,
  filters,
  onFilterChange,
  onClearFilters,
}) => {
  const [showFilters, setShowFilters] = useState(true);

  // Calculate available facet values based on current nodes
  const facets = useMemo(() => {
    const result = {
      nodeTypes: new Map<NodeType, number>(),
      authors: new Map<string, number>(),
      keywords: new Map<string, number>(),
      inputDatatypes: new Map<string, number>(),
      outputDatatypes: new Map<string, number>(),
    };

    nodes.forEach((node) => {
      // Count by node type
      result.nodeTypes.set(
        node.node.node_type,
        (result.nodeTypes.get(node.node.node_type) || 0) + 1,
      );

      // Count by author
      result.authors.set(
        node.node.author_name,
        (result.authors.get(node.node.author_name) || 0) + 1,
      );

      // Count by keywords
      if (node.node.keywords) {
        node.node.keywords.forEach((keyword) => {
          result.keywords.set(keyword, (result.keywords.get(keyword) || 0) + 1);
        });
      }

      // Count by input datatype
      node.node.inputs.forEach((input) => {
        if (input.datatype) {
          result.inputDatatypes.set(
            input.datatype,
            (result.inputDatatypes.get(input.datatype) || 0) + 1,
          );
        }
      });

      // Count by output datatype
      node.node.outputs.forEach((output) => {
        if (output.datatype) {
          result.outputDatatypes.set(
            output.datatype,
            (result.outputDatatypes.get(output.datatype) || 0) + 1,
          );
        }
      });
    });

    return result;
  }, [nodes]);

  const activeFilterCount = [
    filters.type?.length || 0,
    filters.author?.length || 0,
    filters.keywords?.length || 0,
    filters.inputDatatype?.length || 0,
    filters.outputDatatype?.length || 0,
  ].reduce((a, b) => a + b, 0);

  const nodeTypeOptions = Array.from(facets.nodeTypes.keys()).sort((a, b) =>
    a.localeCompare(b),
  );
  const authorOptions = Array.from(facets.authors.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([author]) => author);
  const keywordOptions = Array.from(facets.keywords.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([keyword]) => keyword);
  const inputDatatypeOptions = Array.from(facets.inputDatatypes.keys()).sort(
    (a, b) => a.localeCompare(b),
  );
  const outputDatatypeOptions = Array.from(facets.outputDatatypes.keys()).sort(
    (a, b) => a.localeCompare(b),
  );

  return (
    <Card className="shadow-sm">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span className="fw-semibold">Filters</span>
        <Button
          variant="outline-secondary"
          size="sm"
          onClick={() => setShowFilters((prev) => !prev)}
          aria-expanded={showFilters}
        >
          {showFilters ? "Hide" : "Show"}
        </Button>
      </Card.Header>
      <Collapse in={showFilters}>
        <Card.Body>
          <div className="d-flex justify-content-between align-items-center mb-3">
            {activeFilterCount > 0 && (
              <Button
                variant="link"
                size="sm"
                onClick={onClearFilters}
                className="p-0"
              >
                <X size={16} className="me-1" style={{ display: "inline" }} />
                Clear All
              </Button>
            )}
          </div>

          <Row className="g-3">
            <Col md={6} lg={4} xl={3}>
              <Form.Label>Node Type</Form.Label>
              <Typeahead
                id="node-type-filter"
                multiple
                clearButton
                options={nodeTypeOptions}
                selected={filters.type || []}
                onChange={(selected) => {
                  const updated = selected
                    .map((option) => String(option))
                    .filter((option): option is NodeType =>
                      Object.values(NodeType).includes(option as NodeType),
                    );
                  onFilterChange({ ...filters, type: updated });
                }}
                placeholder="Select node types..."
                renderMenuItemChildren={(option) => {
                  const value = String(option) as NodeType;
                  return (
                    <>
                      {value} ({facets.nodeTypes.get(value) || 0})
                    </>
                  );
                }}
              />
            </Col>

            <Col md={6} lg={4} xl={3}>
              <Form.Label>Author</Form.Label>
              <Typeahead
                id="author-filter"
                multiple
                clearButton
                options={authorOptions}
                selected={filters.author || []}
                onChange={(selected) => {
                  onFilterChange({
                    ...filters,
                    author: selected.map((option) => String(option)),
                  });
                }}
                placeholder="Select authors..."
                renderMenuItemChildren={(option) => {
                  const value = String(option);
                  return (
                    <>
                      {value} ({facets.authors.get(value) || 0})
                    </>
                  );
                }}
              />
            </Col>

            <Col md={6} lg={4} xl={3}>
              <Form.Label>Keywords</Form.Label>
              <Typeahead
                id="keywords-filter"
                multiple
                clearButton
                options={keywordOptions}
                selected={filters.keywords || []}
                onChange={(selected) => {
                  onFilterChange({
                    ...filters,
                    keywords: selected.map((option) => String(option)),
                  });
                }}
                placeholder="Select keywords..."
                renderMenuItemChildren={(option) => {
                  const value = String(option);
                  return (
                    <>
                      {value} ({facets.keywords.get(value) || 0})
                    </>
                  );
                }}
              />
            </Col>
          </Row>
          <Row className="g-3">
            <Col md={6} lg={4} xl={3}>
              <Form.Label>Input Type</Form.Label>
              <Typeahead
                id="input-datatype-filter"
                multiple
                clearButton
                options={inputDatatypeOptions}
                selected={filters.inputDatatype || []}
                onChange={(selected) => {
                  onFilterChange({
                    ...filters,
                    inputDatatype: selected.map((option) => String(option)),
                  });
                }}
                placeholder="Select input types..."
                renderMenuItemChildren={(option) => {
                  const value = String(option);
                  return (
                    <>
                      {value} ({facets.inputDatatypes.get(value) || 0})
                    </>
                  );
                }}
              />
            </Col>

            <Col md={6} lg={4} xl={3}>
              <Form.Label>Output Type</Form.Label>
              <Typeahead
                id="output-datatype-filter"
                multiple
                clearButton
                options={outputDatatypeOptions}
                selected={filters.outputDatatype || []}
                onChange={(selected) => {
                  onFilterChange({
                    ...filters,
                    outputDatatype: selected.map((option) => String(option)),
                  });
                }}
                placeholder="Select output types..."
                renderMenuItemChildren={(option) => {
                  const value = String(option);
                  return (
                    <>
                      {value} ({facets.outputDatatypes.get(value) || 0})
                    </>
                  );
                }}
              />
            </Col>
          </Row>
        </Card.Body>
      </Collapse>
    </Card>
  );
};
