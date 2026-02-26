import React from "react";
import {
  Container,
  Row,
  Col,
  Badge,
  Button,
  Card,
  Tab,
  Tabs,
  Table,
  Nav,
  Navbar,
} from "react-bootstrap";
import { NodeMetadata } from "../types/index";
import {
  Code,
  User,
  Calendar,
  Box,
  GitBranch,
  Zap,
  ArrowLeft,
} from "lucide-react";

interface NodeDetailViewProps {
  node: NodeMetadata;
  onClose: () => void;
}

export const NodeDetailView: React.FC<NodeDetailViewProps> = ({
  node,
  onClose,
}) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Container className="py-4">
      <Row className="mb-2">
        <Col>
          <Button
            variant="link"
            className="p-0 mb-3 d-flex align-items-center"
            onClick={onClose}
            style={{ color: "#0d6efd", textDecoration: "none" }}
          >
            <ArrowLeft size={18} className="me-2" />
            Back to Search
          </Button>
        </Col>
      </Row>

      <Row className="mb-4">
        <Col>
          <h1 className="mb-3">{node.python_import}</h1>
          <div className="mb-3">
            <Badge bg="info" className="me-2" style={{ fontSize: "0.9rem" }}>
              {node.node_type}
            </Badge>
            {node.node_type === "function" && (
              <Badge bg="secondary" style={{ fontSize: "0.9rem" }}>
                Function
              </Badge>
            )}
          </div>
        </Col>
      </Row>

      {/* Metadata Row */}
      <Row className="mb-4">
        <Col md={6} className="mb-3">
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div className="mb-3">
                <small className="text-muted d-block mb-1">
                  <User
                    size={14}
                    className="me-2"
                    style={{ display: "inline" }}
                  />
                  Author
                </small>
                <p className="mb-0">
                  <strong>{node.author_name}</strong>
                </p>
                <small className="text-muted">{node.author_email}</small>
              </div>
              <hr />
              <div className="mb-0">
                <small className="text-muted d-block mb-1">
                  <User
                    size={14}
                    className="me-2"
                    style={{ display: "inline" }}
                  />
                  Creator
                </small>
                <p className="mb-0">
                  <strong>{node.creator_name}</strong>
                </p>
                <small className="text-muted">{node.creator_email}</small>
              </div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6} className="mb-3">
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div>
                <small className="text-muted d-block mb-1">
                  <Calendar
                    size={14}
                    className="me-2"
                    style={{ display: "inline" }}
                  />
                  Created
                </small>
                <p className="mb-0">
                  <strong>{formatDate(node.creation_timestamp)}</strong>
                </p>
              </div>
              <hr />
              <div>
                <small className="text-muted d-block mb-1">
                  <Code
                    size={14}
                    className="me-2"
                    style={{ display: "inline" }}
                  />
                  Source Hash
                </small>
                <code className="small">{node.source_code_hash}</code>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Documentation */}
      <Row className="mb-4">
        <Col>
          <Card className="shadow-sm">
            <Card.Header className="bg-light">
              <h5 className="mb-0">Documentation</h5>
            </Card.Header>
            <Card.Body>
              <div className="mb-3">
                <h6 className="text-muted">Description</h6>
                <p>{node.docstring || "No description available"}</p>
              </div>
              {node.ai_docstring && (
                <div>
                  <h6 className="text-muted">AI Generated Summary</h6>
                  <div className="alert alert-light">
                    <p className="mb-0">{node.ai_docstring}</p>
                  </div>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Details Tabs */}
      <Row>
        <Col>
          <Tabs defaultActiveKey="inputs" id="node-detail-tabs">
            {/* Inputs Tab */}
            <Tab
              eventKey="inputs"
              title={
                <>
                  <Zap
                    size={14}
                    className="me-2"
                    style={{ display: "inline" }}
                  />
                  Inputs ({node.inputs.length})
                </>
              }
            >
              <Card className="border-0 border-top">
                <Card.Body>
                  {node.inputs.length === 0 ? (
                    <p className="text-muted mb-0">No inputs</p>
                  ) : (
                    <Table striped hover responsive className="mb-0">
                      <thead>
                        <tr>
                          <th>Label</th>
                          <th>Data Type</th>
                          <th>Unit</th>
                          <th>Quantity</th>
                          <th>Default</th>
                        </tr>
                      </thead>
                      <tbody>
                        {node.inputs.map((input, idx) => (
                          <tr key={idx}>
                            <td>
                              <code>{input.label || "-"}</code>
                            </td>
                            <td>
                              {input.datatype ? (
                                <Badge bg="secondary">{input.datatype}</Badge>
                              ) : (
                                <span className="text-muted">-</span>
                              )}
                            </td>
                            <td>
                              <small>{input.unit || "-"}</small>
                            </td>
                            <td>
                              <small>{input.quantity || "-"}</small>
                            </td>
                            <td>
                              {input.has_default_value ? (
                                <Badge bg="success">Yes</Badge>
                              ) : (
                                <Badge bg="light" text="dark">
                                  No
                                </Badge>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>
            </Tab>

            {/* Outputs Tab */}
            <Tab
              eventKey="outputs"
              title={
                <>
                  <Box
                    size={14}
                    className="me-2"
                    style={{ display: "inline" }}
                  />
                  Outputs ({node.outputs.length})
                </>
              }
            >
              <Card className="border-0 border-top">
                <Card.Body>
                  {node.outputs.length === 0 ? (
                    <p className="text-muted mb-0">No outputs</p>
                  ) : (
                    <Table striped hover responsive className="mb-0">
                      <thead>
                        <tr>
                          <th>Label</th>
                          <th>Data Type</th>
                          <th>Unit</th>
                          <th>Quantity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {node.outputs.map((output, idx) => (
                          <tr key={idx}>
                            <td>
                              <code>{output.label || "-"}</code>
                            </td>
                            <td>
                              {output.datatype ? (
                                <Badge bg="secondary">{output.datatype}</Badge>
                              ) : (
                                <span className="text-muted">-</span>
                              )}
                            </td>
                            <td>
                              <small>{output.unit || "-"}</small>
                            </td>
                            <td>
                              <small>{output.quantity || "-"}</small>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </Table>
                  )}
                </Card.Body>
              </Card>
            </Tab>

            {/* Dependencies Tab */}
            <Tab
              eventKey="dependencies"
              title={
                <>
                  <GitBranch
                    size={14}
                    className="me-2"
                    style={{ display: "inline" }}
                  />
                  Dependencies (
                  {node.dependencies ? node.dependencies.length : 0})
                </>
              }
            >
              <Card className="border-0 border-top">
                <Card.Body>
                  {!node.dependencies || node.dependencies.length === 0 ? (
                    <p className="text-muted mb-0">No dependencies</p>
                  ) : (
                    <div>
                      {node.dependencies.map((dep, idx) => (
                        <div key={idx} className="mb-2">
                          <code className="d-block p-2 bg-light rounded">
                            {dep}
                          </code>
                        </div>
                      ))}
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Tab>

            {/* Source Code Tab */}
            <Tab
              eventKey="source"
              title={
                <>
                  <Code
                    size={14}
                    className="me-2"
                    style={{ display: "inline" }}
                  />
                  Source Code
                </>
              }
            >
              <Card className="border-0 border-top">
                <Card.Body>
                  <pre
                    className="bg-light p-3 rounded overflow-auto"
                    style={{ maxHeight: "500px" }}
                  >
                    <code>{node.source_code}</code>
                  </pre>
                </Card.Body>
              </Card>
            </Tab>
          </Tabs>
        </Col>
      </Row>
    </Container>
  );
};
