from node_store_spec.models import Annotation

from .models import NodeMetadata


def escape_html(text: str) -> str:
    """Escape HTML special characters"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_node_html(node: NodeMetadata) -> str:
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

    collapse_id = f"collapse-{node.source_code_hash[:8]}"

    inputs_html = ""
    for name, annotation in node.inputs.items():
        inputs_html += render_annotation_html(name, annotation)

    outputs_html = ""
    for name, annotation in node.outputs.items():
        outputs_html += render_annotation_html(name, annotation)

    node_html = f"""
    <div class="card mb-4" style="cursor: pointer;">
        <div 
            class="card-body" 
            role="button" 
            data-bs-toggle="collapse" 
            data-bs-target="#{collapse_id}" 
            aria-expanded="false" 
            aria-controls="{collapse_id}">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div class="flex-grow-1">
                    <h5 class="card-title mb-0">{escape_html(node.python_import or "Unnamed Node")}</h5>
                    <h6 class="card-subtitle text-muted small">Author: {escape_html(node.author_name)} ({escape_html(node.author_email)})</h6>
                    <p class="card-text text-muted small mb-0 mt-1">Type: {escape_html(node.node_type)}</p>
                </div>
                <div class="d-flex gap-2" style="flex-shrink: 0;">
                    <span class="badge bg-secondary" style="align-self: center;">Click to expand</span>
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


def render_search_results_html(results: list[NodeMetadata]) -> str:
    if results:
        results_html = "<h2 class='mt-5 mb-4'>Search Results</h2>"
        results_html += "<div class='row'>"
        for node in results:
            results_html += render_node_html(node)
        results_html += "</div>"
    else:
        results_html = "<div class='alert alert-info mt-5' role='alert'>No results found for your search.</div>"

    return results_html


def render_search_page(query: str, results: list[NodeMetadata]):
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
            {f"<div class='welcome-text'><p class='lead'>Enter a search query to find nodes</p></div>" if not query else ""}
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
        for name, annotation in node.inputs.items():
            inputs_html += f"<li><strong>{escape_html(name)}</strong>: "
            if annotation.label:
                inputs_html += f"{escape_html(annotation.label)} "
            if annotation.datatype:
                inputs_html += f"<code>{escape_html(annotation.datatype)}</code> "
            if annotation.unit:
                inputs_html += f"[{escape_html(annotation.unit)}] "
            if annotation.quantity:
                inputs_html += f"- {escape_html(annotation.quantity)}"
            inputs_html += "</li>"
    else:
        inputs_html = "<li class='text-muted'>No inputs</li>"

    outputs_html = ""
    if node.outputs:
        for name, annotation in node.outputs.items():
            outputs_html += f"<li><strong>{escape_html(name)}</strong>: "
            if annotation.label:
                outputs_html += f"{escape_html(annotation.label)} "
            if annotation.datatype:
                outputs_html += f"<code>{escape_html(annotation.datatype)}</code> "
            if annotation.unit:
                outputs_html += f"[{escape_html(annotation.unit)}] "
            if annotation.quantity:
                outputs_html += f"- {escape_html(annotation.quantity)}"
            outputs_html += "</li>"
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

            <div class='detail-card'>
                <h3 class='section-title'>Source Code</h3>
                <pre style='background-color: #f5f5f5; padding: 1rem; border-radius: 0.3rem; overflow-x: auto;'><code>{escape_html(node.source_code)}</code></pre>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return page
