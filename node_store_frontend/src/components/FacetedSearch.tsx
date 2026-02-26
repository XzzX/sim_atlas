import React, { useMemo } from "react";
import { Form, Accordion, Badge, Button } from "react-bootstrap";
import { NodeMetadata, NodeType, FacetFilters } from "../types/index";
import { X } from "lucide-react";

interface FacetedSearchProps {
  nodes: NodeMetadata[];
  filters: FacetFilters;
  onFilterChange: (filters: FacetFilters) => void;
  onClearFilters: () => void;
}

export const FacetedSearch: React.FC<FacetedSearchProps> = ({
  nodes,
  filters,
  onFilterChange,
  onClearFilters,
}) => {
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
        node.node_type,
        (result.nodeTypes.get(node.node_type) || 0) + 1,
      );

      // Count by author
      result.authors.set(
        node.author_name,
        (result.authors.get(node.author_name) || 0) + 1,
      );

      // Count by keywords
      if (node.keywords) {
        node.keywords.forEach((keyword) => {
          result.keywords.set(keyword, (result.keywords.get(keyword) || 0) + 1);
        });
      }

      // Count by input datatype
      node.inputs.forEach((input) => {
        if (input.datatype) {
          result.inputDatatypes.set(
            input.datatype,
            (result.inputDatatypes.get(input.datatype) || 0) + 1,
          );
        }
      });

      // Count by output datatype
      node.outputs.forEach((output) => {
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

  const handleNodeTypeToggle = (nodeType: NodeType) => {
    const current = filters.nodeType || [];
    const updated = current.includes(nodeType)
      ? current.filter((t) => t !== nodeType)
      : [...current, nodeType];
    onFilterChange({ ...filters, nodeType: updated });
  };

  const handleAuthorToggle = (author: string) => {
    const current = filters.author || [];
    const updated = current.includes(author)
      ? current.filter((a) => a !== author)
      : [...current, author];
    onFilterChange({ ...filters, author: updated });
  };

  const handleKeywordsToggle = (keyword: string) => {
    const current = filters.keywords || [];
    const updated = current.includes(keyword)
      ? current.filter((k) => k !== keyword)
      : [...current, keyword];
    onFilterChange({ ...filters, keywords: updated });
  };

  const handleInputDatatypeToggle = (datatype: string) => {
    const current = filters.inputDatatype || [];
    const updated = current.includes(datatype)
      ? current.filter((d) => d !== datatype)
      : [...current, datatype];
    onFilterChange({ ...filters, inputDatatype: updated });
  };

  const handleOutputDatatypeToggle = (datatype: string) => {
    const current = filters.outputDatatype || [];
    const updated = current.includes(datatype)
      ? current.filter((d) => d !== datatype)
      : [...current, datatype];
    onFilterChange({ ...filters, outputDatatype: updated });
  };

  const activeFilterCount = [
    filters.nodeType?.length || 0,
    filters.author?.length || 0,
    filters.keywords?.length || 0,
    filters.inputDatatype?.length || 0,
    filters.outputDatatype?.length || 0,
  ].reduce((a, b) => a + b, 0);

  return (
    <div className="facet-filter">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h6 className="mb-0">Filters</h6>
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

      <Accordion alwaysOpen flush>
        {/* Node Type Filter */}
        <Accordion.Item eventKey="0">
          <Accordion.Header>
            Node Type
            {filters.nodeType && filters.nodeType.length > 0 && (
              <Badge bg="primary" className="ms-2">
                {filters.nodeType.length}
              </Badge>
            )}
          </Accordion.Header>
          <Accordion.Body className="p-2">
            {Array.from(facets.nodeTypes.entries()).map(([nodeType, count]) => (
              <Form.Check
                key={nodeType}
                type="checkbox"
                id={`nodeType-${nodeType}`}
                label={`${nodeType} (${count})`}
                checked={filters.nodeType?.includes(nodeType) || false}
                onChange={() => handleNodeTypeToggle(nodeType)}
                className="mb-2"
              />
            ))}
          </Accordion.Body>
        </Accordion.Item>

        {/* Author Filter */}
        <Accordion.Item eventKey="1">
          <Accordion.Header>
            Author
            {filters.author && filters.author.length > 0 && (
              <Badge bg="primary" className="ms-2">
                {filters.author.length}
              </Badge>
            )}
          </Accordion.Header>
          <Accordion.Body className="p-2">
            {Array.from(facets.authors.entries())
              .sort((a, b) => b[1] - a[1])
              .map(([author, count]) => (
                <Form.Check
                  key={author}
                  type="checkbox"
                  id={`author-${author}`}
                  label={`${author} (${count})`}
                  checked={filters.author?.includes(author) || false}
                  onChange={() => handleAuthorToggle(author)}
                  className="mb-2"
                />
              ))}
          </Accordion.Body>
        </Accordion.Item>

        {/* Keywords Filter */}
        <Accordion.Item eventKey="2">
          <Accordion.Header>
            Keywords
            {filters.keywords && filters.keywords.length > 0 && (
              <Badge bg="primary" className="ms-2">
                {filters.keywords.length}
              </Badge>
            )}
          </Accordion.Header>
          <Accordion.Body className="p-2">
            {Array.from(facets.keywords.entries())
              .sort((a, b) => b[1] - a[1])
              .map(([keyword, count]) => (
                <Form.Check
                  key={keyword}
                  type="checkbox"
                  id={`keyword-${keyword}`}
                  label={`${keyword} (${count})`}
                  checked={filters.keywords?.includes(keyword) || false}
                  onChange={() => handleKeywordsToggle(keyword)}
                  className="mb-2"
                />
              ))}
          </Accordion.Body>
        </Accordion.Item>

        {/* Input Datatype Filter */}
        <Accordion.Item eventKey="3">
          <Accordion.Header>
            Input Type
            {filters.inputDatatype && filters.inputDatatype.length > 0 && (
              <Badge bg="primary" className="ms-2">
                {filters.inputDatatype.length}
              </Badge>
            )}
          </Accordion.Header>
          <Accordion.Body className="p-2">
            {Array.from(facets.inputDatatypes.entries())
              .sort((a, b) => a[0].localeCompare(b[0]))
              .map(([datatype, count]) => (
                <Form.Check
                  key={datatype}
                  type="checkbox"
                  id={`inputDatatype-${datatype}`}
                  label={`${datatype} (${count})`}
                  checked={filters.inputDatatype?.includes(datatype) || false}
                  onChange={() => handleInputDatatypeToggle(datatype)}
                  className="mb-2"
                />
              ))}
          </Accordion.Body>
        </Accordion.Item>

        {/* Output Datatype Filter */}
        <Accordion.Item eventKey="4">
          <Accordion.Header>
            Output Type
            {filters.outputDatatype && filters.outputDatatype.length > 0 && (
              <Badge bg="primary" className="ms-2">
                {filters.outputDatatype.length}
              </Badge>
            )}
          </Accordion.Header>
          <Accordion.Body className="p-2">
            {Array.from(facets.outputDatatypes.entries())
              .sort((a, b) => a[0].localeCompare(b[0]))
              .map(([datatype, count]) => (
                <Form.Check
                  key={datatype}
                  type="checkbox"
                  id={`outputDatatype-${datatype}`}
                  label={`${datatype} (${count})`}
                  checked={filters.outputDatatype?.includes(datatype) || false}
                  onChange={() => handleOutputDatatypeToggle(datatype)}
                  className="mb-2"
                />
              ))}
          </Accordion.Body>
        </Accordion.Item>
      </Accordion>
    </div>
  );
};
