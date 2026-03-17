from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow

from .models import (
    Annotation,
    NodeMetadata,
    NodeResponse,
    NodeType,
    ScoredSearchResponse,
)


def escape_html(text: str) -> str:
    """Escape HTML special characters"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def parse_workflow_from_source(
    source_code: str,
) -> PythonWorkflowDefinitionWorkflow | None:
    """Try to parse source code as a PythonWorkflowDefinitionWorkflow"""
    try:
        workflow = PythonWorkflowDefinitionWorkflow.model_validate_json(source_code)
        return workflow
    except Exception:
        return None


def workflow_to_mermaid(workflow: PythonWorkflowDefinitionWorkflow) -> str:
    """Convert a PythonWorkflowDefinitionWorkflow to a mermaidjs diagram"""
    lines = ["flowchart TD"]

    # Create nodes
    for node in workflow.nodes:
        if node.type == "input":
            lines.append(f'    {node.id}["Input: {escape_html(node.name)}"]')
        elif node.type == "output":
            lines.append(f'    {node.id}["Output: {escape_html(node.name)}"]')
        elif node.type == "function":
            # Extract function name from module.function format
            func_name = node.value.split(".")[-1]
            lines.append(f'    {node.id}["{escape_html(func_name)}"]')

    # Create edges
    for edge in workflow.edges:
        source_port = (
            "".join(c for c in (edge.sourcePort or "") if c.isalnum() or c in " _-")
            if edge.sourcePort
            else ""
        )
        target_port = (
            "".join(c for c in (edge.targetPort or "") if c.isalnum() or c in " _-")
            if edge.targetPort
            else ""
        )

        if source_port and target_port:
            label = f"{source_port} → {target_port}"
            lines.append(f"    {edge.source} -->|{label}| {edge.target}")
        elif source_port:
            lines.append(f"    {edge.source} -->|{source_port}| {edge.target}")
        elif target_port:
            lines.append(f"    {edge.source} -->|{target_port}| {edge.target}")
        else:
            lines.append(f"    {edge.source} --> {edge.target}")

    return "\n".join(lines)


def render_annotation_html(name: str, annotation: Annotation) -> str:
    outputs_html = f"<li><strong>{escape_html(name)}</strong><ul>"
    if annotation.label:
        outputs_html += f"<li>Label: {escape_html(annotation.label)}</li>"
    if annotation.datatype:
        outputs_html += (
            f"<li>Type: <code>{escape_html(annotation.datatype)}</code></li>"
        )
    if annotation.unit:
        outputs_html += f"<li>Unit: {escape_html(annotation.unit)}</li>"
    if annotation.quantity:
        outputs_html += f"<li>Quantity: {escape_html(annotation.quantity)}</li>"
    outputs_html += "</ul></li>"
    return outputs_html


def render_node_html(node: NodeResponse) -> str:
    collapse_id = f"collapse-{node.source_code_hash[:8]}"

    inputs_html = ""
    for inp in node.inputs:
        inputs_html += render_annotation_html(inp.label or "", inp)

    outputs_html = ""
    for outp in node.outputs:
        outputs_html += render_annotation_html(outp.label or "", outp)

    node_html = f"""
    <div class="card mb-4">
        <div class="card-body">
            <div class="d-flex justify-content-between align-items-center">
                <div class="flex-grow-1">
                    <h5 class="card-title mb-0">{escape_html(node.python_import or "Unnamed Node")}</h5>
                    <h6 class="card-subtitle text-muted small">Author: {escape_html(node.author_name)} ({escape_html(node.author_email)})</h6>
                    <p class="card-text text-muted small mb-0 mt-1">Type: {escape_html(node.node_type)}</p>
                </div>
                <div class="d-flex gap-2 ms-3" style="flex-shrink: 0;">
                    <button 
                        class="btn btn-sm btn-outline-secondary"
                        type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#{collapse_id}"
                        aria-expanded="false"
                        aria-controls="{collapse_id}">
                        ▼ Expand
                    </button>
                    <a 
                        href="/nodes-detail/{node.source_code_hash}" 
                        class="btn btn-sm btn-outline-primary">
                        Details →
                    </a>
                </div>
            </div>
        </div>
            
        <div class="collapse" id="{collapse_id}">
            <div class="card-body border-top">
                <p class="card-text">{escape_html(node.docstring).replace(chr(10), "<br>")}</p>
                <hr>
                <h6>Inputs:</h6>
                <ul>
                    {inputs_html}
                </ul>
                <h6>Outputs:</h6>
                <ul>
                    {outputs_html}
                </ul>
            </div>
        </div>
    </div>
    """
    return node_html


def render_search_results_html(results: list[ScoredSearchResponse]) -> str:
    if results:
        results_html = "<h2 class='mt-5 mb-4'>Search Results</h2>"
        results_html += "<div class='row'>"
        for node in results:
            results_html += render_node_html(node.node)
        results_html += "</div>"
    else:
        results_html = "<div class='alert alert-info mt-5' role='alert'>No results found for your search.</div>"

    return results_html


def render_search_page(query: str, results: list[ScoredSearchResponse]) -> str:
    results_html = render_search_results_html(results)

    page = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Node Store - Search</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }}
            .search-header {{
                background: rgba(255, 255, 255, 0.95);
                padding: 3rem 0;
                margin-bottom: 2rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .search-box {{
                max-width: 600px;
                margin: 0 auto;
            }}
            .container-main {{
                flex: 1;
                color: white;
            }}
            .card {{
                border: none;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.2) !important;
            }}
            .btn-search {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                padding: 0.75rem 2rem;
                font-weight: 500;
            }}
            .btn-search:hover {{
                background: linear-gradient(135deg, #5568d3 0%, #653a91 100%);
                color: white;
            }}
            .welcome-text {{
                text-align: center;
                margin-top: 2rem;
            }}
        </style>
    </head>
    <body>
        <div class='search-header'>
            <div class='container'>
                <div class='search-box'>
                    <h1 class='text-center text-dark mb-4'>
                        <strong>Node Store</strong>
                    </h1>
                    <form method='get' class='d-flex gap-2'>
                        <input 
                            type='text' 
                            name='query' 
                            class='form-control form-control-lg' 
                            placeholder='Search nodes by author, email, type, or docstring...'
                            value='{escape_html(query or "")}'
                            autofocus
                        >
                        <button type='submit' class='btn btn-search btn-lg'>Search</button>
                    </form>
                </div>
            </div>
        </div>
        
        <div class='container-main container'>
            {results_html}
            {"<div class='welcome-text'><p class='lead'>Enter a search query to find nodes</p></div>" if not query else ""}
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return page


def render_node_detail_page(node: NodeMetadata) -> str:
    """Render a detailed view of a single node"""
    inputs_html = ""
    if node.inputs:
        for inp in node.inputs:
            inputs_html += render_annotation_html(inp.label or "", inp)
    else:
        inputs_html = "<li class='text-muted'>No inputs</li>"

    outputs_html = ""
    if node.outputs:
        for outp in node.outputs:
            outputs_html += render_annotation_html(outp.label or "", outp)
    else:
        outputs_html = "<li class='text-muted'>No outputs</li>"

    dependencies_html = ""
    if node.dependencies:
        dependencies_html = "<ul>"
        for dep in node.dependencies:
            dependencies_html += f"<li><code>{escape_html(dep)}</code></li>"
        dependencies_html += "</ul>"
    else:
        dependencies_html = "<p class='text-muted'>No dependencies</p>"

    # Generate workflow diagram if this is a PWD node
    workflow_diagram_html = ""
    if node.node_type == NodeType.PYTHON_WORKFLOW_DEFINITION:
        workflow = parse_workflow_from_source(node.source_code)
        if workflow:
            mermaid_diagram = workflow_to_mermaid(workflow)
            workflow_diagram_html = f"""
            <div class='detail-card' style="padding: 0; overflow: hidden; display: flex; flex-direction: column;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 1.5rem 1.5rem 1rem 1.5rem;">
                    <h3 class='section-title' style="margin: 0;">Workflow Diagram</h3>
                    <a href='/ide/?wf_hash={node.source_code_hash}' class='btn btn-sm btn-outline-primary' target='_blank'>
                        Open Web IDE →
                    </a>
                </div>
                <div class="mermaid" style="background-color: white; padding: 2rem; flex: 1; min-height: 800px; border-radius: 0.3rem; display: flex; align-items: center; justify-content: center;">
{mermaid_diagram}
                </div>
                <style width=100%>
                    .mermaid svg {{
                        width: 100% !important;
                        height: 100% !important;
                    }}
                </style>
            </div>
            """

    page = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Node Store - {escape_html(node.python_import or "Node Details")}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 2rem 0;
            }}
            .detail-header {{
                background: rgba(255, 255, 255, 0.95);
                padding: 2rem;
                border-radius: 0.5rem;
                margin-bottom: 2rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .detail-card {{
                background: white;
                border-radius: 0.5rem;
                margin-bottom: 1.5rem;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 1.5rem;
            }}
            .section-title {{
                color: #667eea;
                font-weight: 600;
                border-bottom: 2px solid #667eea;
                padding-bottom: 0.5rem;
                margin-top: 1.5rem;
                margin-bottom: 1rem;
            }}
            code {{
                background-color: #f5f5f5;
                padding: 0.2rem 0.4rem;
                border-radius: 0.3rem;
                color: #d63384;
            }}
            .btn-back {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                color: white;
            }}
            .btn-back:hover {{
                background: linear-gradient(135deg, #5568d3 0%, #653a91 100%);
                color: white;
            }}
            .metadata-row {{
                display: flex;
                justify-content: space-between;
                padding: 0.75rem 0;
                border-bottom: 1px solid #e0e0e0;
            }}
            .metadata-row:last-child {{
                border-bottom: none;
            }}
            .metadata-label {{
                font-weight: 600;
                color: #667eea;
                min-width: 120px;
            }}
        </style>
    </head>
    <body>
        <div class='container' style='max-width: 900px;'>
            <div class='detail-header'>
                <div class='d-flex justify-content-between align-items-start'>
                    <div>
                        <h1>{escape_html(node.python_import or "Node Details")}</h1>
                        <p class='text-muted mb-0'>Node Type: <strong>{escape_html(node.node_type)}</strong></p>
                    </div>
                    <a href='/' class='btn btn-back'>← Back to Search</a>
                </div>
            </div>

            <div class='detail-card'>
                <h3 class='section-title'>Metadata</h3>
                <div class='metadata-row'>
                    <span class='metadata-label'>Author:</span>
                    <span>{escape_html(node.author_name)}</span>
                </div>
                <div class='metadata-row'>
                    <span class='metadata-label'>Email:</span>
                    <span>{escape_html(node.author_email)}</span>
                </div>
                <div class='metadata-row'>
                    <span class='metadata-label'>Hash:</span>
                    <span><code>{node.source_code_hash}</code></span>
                </div>
                <div class='metadata-row'>
                    <span class='metadata-label'>Type:</span>
                    <span>{escape_html(node.node_type)}</span>
                </div>
            </div>

            <div class='detail-card'>
                <h3 class='section-title'>Description</h3>
                <p>{escape_html(node.docstring).replace(chr(10), "<br>")}</p>
                {f"<div class='alert alert-info'>AI Generated Docstring:<br>{escape_html(node.ai_docstring).replace(chr(10), '<br>')}</div>" if node.ai_docstring else ""}
            </div>

            <div class='detail-card'>
                <h3 class='section-title'>Inputs</h3>
                <ul>
                    {inputs_html}
                </ul>
            </div>

            <div class='detail-card'>
                <h3 class='section-title'>Outputs</h3>
                <ul>
                    {outputs_html}
                </ul>
            </div>

            <div class='detail-card'>
                <h3 class='section-title'>Dependencies</h3>
                {dependencies_html}
            </div>

            {workflow_diagram_html}

            <div class='detail-card'>
                <h3 class='section-title'>Source Code</h3>
                <pre style='background-color: #f5f5f5; padding: 1rem; border-radius: 0.3rem; overflow-x: auto;'><code>{escape_html(node.source_code)}</code></pre>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
        <script>
            mermaid.initialize({{ 
                startOnLoad: true
            }});
            mermaid.contentLoaded();
            
            // Enable pan and zoom on mermaid diagrams
            setTimeout(function() {{
                var svgs = document.querySelectorAll('.mermaid svg');
                svgs.forEach(function(svg) {{
                    if (!svg.hasAttribute('data-panZoom-enabled')) {{
                        svgPanZoom(svg, {{
                            zoomEnabled: true,
                            controlIconsEnabled: true,
                            fit: true,
                            center: true,
                            minZoom: 0.5,
                            maxZoom: 10
                        }});
                        svg.setAttribute('data-panZoom-enabled', 'true');
                    }}
                }});
            }}, 100);
        </script>
    </body>
    </html>
    """
    return page
