import importlib.metadata
import pathlib

import anywidget
import traitlets

try:
    __version__ = importlib.metadata.version("simflow")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"

initial_nodes = [
    {
        "id": "1",
        "data": {
            "metadata": {
                "author_name": "John Doe",
                "author_email": "john.doe@example.com",
                "node_type": "function",
                "python_import": "__main__.get_lj_energy",
                "dependencies": None,
                "source_code": 'def get_lj_energy(\n    distances: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n) -> Annotated[\n    float,\n    {\n        "unit": "https://qudt.org/vocab/unit/EV",\n        "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n    },\n]:\n    """\n    Calculates Lennard-Jones potential energy.\n\n    Args:\n        distances: Atomic distances.\n        sigma: LJ sigma parameter (length scale).\n        epsilon: LJ epsilon parameter (energy scale).\n\n    Returns:\n        float: Total Lennard-Jones energy.\n    """\n    r = np.atleast_1d(distances)\n    return epsilon * np.sum((sigma / r) ** 12 - (sigma / r) ** 6) / 2\n',
                "source_code_hash": "cf0b03ab4766604ffcb1837cfe1a4f130af401b0c6dd6cab2a130e3ead4cc6d1",
                "docstring": "Calculates Lennard-Jones potential energy.\n\nArgs:\n    distances: Atomic distances.\n    sigma: LJ sigma parameter (length scale).\n    epsilon: LJ epsilon parameter (energy scale).\n\nReturns:\n    float: Total Lennard-Jones energy.",
                "ai_docstring": "",
                "inputs": [
                    {
                        "has_default_value": False,
                        "label": "distances",
                        "datatype": "ndarray",
                        "unit": "https://qudt.org/vocab/unit/ANGSTROM",
                        "quantity": "https://qudt.org/vocab/quantitykind/Length",
                    },
                    {
                        "has_default_value": False,
                        "label": "sigma",
                        "datatype": "float",
                        "unit": "https://qudt.org/vocab/unit/ANGSTROM",
                        "quantity": "https://qudt.org/vocab/quantitykind/Length",
                    },
                    {
                        "has_default_value": False,
                        "label": "epsilon",
                        "datatype": "float",
                        "unit": "https://qudt.org/vocab/unit/EV",
                        "quantity": "https://qudt.org/vocab/quantitykind/Energy",
                    },
                ],
                "outputs": [
                    {
                        "has_default_value": False,
                        "label": "return",
                        "datatype": "float",
                        "unit": "https://qudt.org/vocab/unit/EV",
                        "quantity": "https://qudt.org/vocab/quantitykind/Energy",
                    },
                ],
            },
        },
        "position": {"x": 1375, "y": 445},
        "type": "FunctionNode",
        "measured": {"width": 163, "height": 135},
    },
]
initial_edges = []


class Widget(anywidget.AnyWidget):
    _esm = pathlib.Path(__file__).parent / "static" / "widget.js"
    _css = pathlib.Path(__file__).parent / "static" / "simflow.css"
    nodes = traitlets.List(initial_nodes).tag(sync=True)
    edges = traitlets.List(initial_edges).tag(sync=True)
