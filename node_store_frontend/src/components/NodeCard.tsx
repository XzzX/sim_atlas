import React from "react";
import { Card, Badge, Row, Col, Table } from "react-bootstrap";
import { NodeMetadata } from "../types/index";
import { User, Calendar } from "lucide-react";

interface NodeCardProps {
  node: NodeMetadata;
  score?: number;
  onSelect?: (node: NodeMetadata) => void;
}

export const NodeCard: React.FC<NodeCardProps> = ({
  node,
  score,
  onSelect,
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <Card
      className="node-card h-100 shadow-sm"
      onClick={() => onSelect?.(node)}
    >
      <Card.Header className="bg-light">
        <div className="d-flex justify-content-between align-items-start">
          <div>
            <h5 className="mb-2">
              {node.python_import.split(".")[-1] || node.python_import}
            </h5>
            <Badge bg="info" className="me-2">
              {node.node_type}
            </Badge>
            {score !== undefined && (
              <Badge bg="success">Score: {score.toFixed(2)}</Badge>
            )}
          </div>
        </div>
      </Card.Header>
      <Card.Body>
        <p
          className="text-muted small mb-3"
          style={{ whiteSpace: "pre-wrap", wordWrap: "break-word" }}
          title={node.docstring}
        >
          {node.docstring || "No description available"}
        </p>

        {node.ai_docstring && (
          <div className="alert alert-light p-2 mb-3">
            <small className="text-muted">
              <strong>AI Summary:</strong> {node.ai_docstring}
            </small>
          </div>
        )}

        {/* Inputs and Outputs Side by Side */}
        <Row className="g-2 mb-3">
          {/* Inputs Section */}
          <Col xs={6}>
            <small className="text-muted d-block mb-2">
              <strong>Inputs ({node.inputs.length})</strong>
            </small>
            {node.inputs.length > 0 ? (
              <Table
                striped
                hover
                responsive
                size="sm"
                className="mb-0"
                style={{ fontSize: "0.7rem" }}
              >
                <thead>
                  <tr>
                    <th>Label</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {node.inputs.map((input, idx) => (
                    <tr key={idx}>
                      <td>
                        <code style={{ fontSize: "0.65rem" }}>
                          {input.label || "-"}
                        </code>
                      </td>
                      <td>
                        {input.datatype ? (
                          <Badge bg="secondary" style={{ fontSize: "0.6rem" }}>
                            {input.datatype}
                          </Badge>
                        ) : (
                          <span className="text-muted">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <p className="text-muted small mb-0">0</p>
            )}
          </Col>

          {/* Outputs Section */}
          <Col xs={6}>
            <small className="text-muted d-block mb-2">
              <strong>Outputs ({node.outputs.length})</strong>
            </small>
            {node.outputs.length > 0 ? (
              <Table
                striped
                hover
                responsive
                size="sm"
                className="mb-0"
                style={{ fontSize: "0.7rem" }}
              >
                <thead>
                  <tr>
                    <th>Label</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {node.outputs.map((output, idx) => (
                    <tr key={idx}>
                      <td>
                        <code style={{ fontSize: "0.65rem" }}>
                          {output.label || "-"}
                        </code>
                      </td>
                      <td>
                        {output.datatype ? (
                          <Badge bg="secondary" style={{ fontSize: "0.6rem" }}>
                            {output.datatype}
                          </Badge>
                        ) : (
                          <span className="text-muted">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <p className="text-muted small mb-0">0</p>
            )}
          </Col>
        </Row>

        {node.keywords && node.keywords.length > 0 && (
          <div className="mb-3">
            <small className="text-muted d-block mb-2">
              <strong>Keywords</strong>
            </small>
            <div>
              {node.keywords.map((keyword, idx) => (
                <Badge key={idx} bg="info" className="me-1 mb-1">
                  {keyword}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {node.dependencies && node.dependencies.length > 0 && (
          <div className="mb-3">
            <small className="text-muted">
              <strong>Dependencies:</strong>
            </small>
            <div className="mt-1">
              {node.dependencies.slice(0, 3).map((dep, idx) => (
                <Badge key={idx} bg="secondary" className="me-1 mb-1">
                  {dep}
                </Badge>
              ))}
              {node.dependencies.length > 3 && (
                <Badge bg="secondary" className="me-1 mb-1">
                  +{node.dependencies.length - 3}
                </Badge>
              )}
            </div>
          </div>
        )}
      </Card.Body>
      <Card.Footer className="bg-light">
        <Row className="g-2">
          <Col xs={6}>
            <small className="text-muted d-flex align-items-center">
              <User size={12} className="me-1" />
              {node.author_name}
            </small>
          </Col>
          <Col xs={6}>
            <small className="text-muted d-flex align-items-center justify-content-end">
              <Calendar size={12} className="me-1" />
              {formatDate(node.creation_timestamp)}
            </small>
          </Col>
        </Row>
      </Card.Footer>
    </Card>
  );
};
