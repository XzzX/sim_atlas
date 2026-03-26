import { type NodeMetadata } from "./interfaces/NodeMetadata";
import type { Node, Edge } from "@xyflow/react";

export const initialNodes: Node[] = [
  {
    id: "1",
    data: {
      metadata: {
        author_name: "John Doe",
        author_email: "john.doe@example.com",
        node_type: "function",
        python_import: "__main__.get_lj_energy",
        dependencies: null,
        source_code:
          'def get_lj_energy(\n    distances: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n) -> Annotated[\n    float,\n    {\n        "unit": "https://qudt.org/vocab/unit/EV",\n        "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n    },\n]:\n    """\n    Calculates Lennard-Jones potential energy.\n\n    Args:\n        distances: Atomic distances.\n        sigma: LJ sigma parameter (length scale).\n        epsilon: LJ epsilon parameter (energy scale).\n\n    Returns:\n        float: Total Lennard-Jones energy.\n    """\n    r = np.atleast_1d(distances)\n    return epsilon * np.sum((sigma / r) ** 12 - (sigma / r) ** 6) / 2\n',
        source_code_hash:
          "cf0b03ab4766604ffcb1837cfe1a4f130af401b0c6dd6cab2a130e3ead4cc6d1",
        docstring:
          "Calculates Lennard-Jones potential energy.\n\nArgs:\n    distances: Atomic distances.\n    sigma: LJ sigma parameter (length scale).\n    epsilon: LJ epsilon parameter (energy scale).\n\nReturns:\n    float: Total Lennard-Jones energy.",
        ai_docstring: "",
        inputs: [
          {
            has_default_value: false,
            label: "distances",
            datatype: "ndarray",
            unit: "https://qudt.org/vocab/unit/ANGSTROM",
            quantity: "https://qudt.org/vocab/quantitykind/Length",
          },
          {
            has_default_value: false,
            label: "sigma",
            datatype: "float",
            unit: "https://qudt.org/vocab/unit/ANGSTROM",
            quantity: "https://qudt.org/vocab/quantitykind/Length",
          },
          {
            has_default_value: false,
            label: "epsilon",
            datatype: "float",
            unit: "https://qudt.org/vocab/unit/EV",
            quantity: "https://qudt.org/vocab/quantitykind/Energy",
          },
        ],
        outputs: [
          {
            has_default_value: false,
            label: "return",
            datatype: "float",
            unit: "https://qudt.org/vocab/unit/EV",
            quantity: "https://qudt.org/vocab/quantitykind/Energy",
          },
        ],
      },
    },
    position: { x: 1375, y: 445 },
    type: "FunctionNode",
    measured: { width: 163, height: 135 },
  },
];

export const initialEdges: Edge[] = [];

export const allNodeMetadata: NodeMetadata[] = [
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_bulk_modulus_dict",
    dependencies: null,
    source_code:
      'def get_bulk_modulus_dict() -> Annotated[dict[str, float], {"label": "bulk_modulus"}]:\n    """\n    Returns a dictionary of bulk moduli for different elements.\n\n    Returns:\n        dict: Dictionary mapping element symbols to bulk modulus values in GPa.\n    """\n    return {"Al": 76, "Cu": 140, "Ni": 180}\n',
    source_code_hash:
      "fba85eb63625c3d82258678949e8e2cbfd32d9ae07444cc728885323d2500f5d",
    docstring:
      "Returns a dictionary of bulk moduli for different elements.\n\nReturns:\n    dict: Dictionary mapping element symbols to bulk modulus values in GPa.",
    ai_docstring: "",
    inputs: [],
    outputs: [
      {
        has_default_value: false,
        label: "bulk_modulus",
        datatype: "dict",
        unit: null,
        quantity: null,
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_lj_energy",
    dependencies: null,
    source_code:
      'def get_lj_energy(\n    distances: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n) -> Annotated[\n    float,\n    {\n        "unit": "https://qudt.org/vocab/unit/EV",\n        "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n    },\n]:\n    """\n    Calculates Lennard-Jones potential energy.\n\n    Args:\n        distances: Atomic distances.\n        sigma: LJ sigma parameter (length scale).\n        epsilon: LJ epsilon parameter (energy scale).\n\n    Returns:\n        float: Total Lennard-Jones energy.\n    """\n    r = np.atleast_1d(distances)\n    return epsilon * np.sum((sigma / r) ** 12 - (sigma / r) ** 6) / 2\n',
    source_code_hash:
      "cf0b03ab4766604ffcb1837cfe1a4f130af401b0c6dd6cab2a130e3ead4cc6d1",
    docstring:
      "Calculates Lennard-Jones potential energy.\n\nArgs:\n    distances: Atomic distances.\n    sigma: LJ sigma parameter (length scale).\n    epsilon: LJ epsilon parameter (energy scale).\n\nReturns:\n    float: Total Lennard-Jones energy.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "distances",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "return",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_lj_pw_forces",
    dependencies: null,
    source_code:
      'def get_lj_pw_forces(\n    distances: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    vecs: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n) -> Annotated[\n    NDArray[np.float64],\n    {\n        "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM",\n        "quantity": "https://qudt.org/vocab/quantitykind/Force",\n    },\n]:\n    """\n    Calculates pairwise Lennard-Jones forces.\n\n    Args:\n        distances: Pairwise atomic distances.\n        vecs: Distance vectors between atoms.\n        sigma: LJ sigma parameter.\n        epsilon: LJ epsilon parameter.\n\n    Returns:\n        ndarray: Pairwise force vectors.\n    """\n    v = vecs.copy()\n    v[v == np.inf] = 0\n    return (\n        -6\n        * epsilon\n        * ((2 * (sigma / distances) ** 12 - (sigma / distances) ** 6) / distances**2)[\n            ..., None\n        ]\n        * v\n    )\n',
    source_code_hash:
      "b8811f00f23c252602e1ed4a3ee2772534bbbe921e8960d7b11903a75fc7e15c",
    docstring:
      "Calculates pairwise Lennard-Jones forces.\n\nArgs:\n    distances: Pairwise atomic distances.\n    vecs: Distance vectors between atoms.\n    sigma: LJ sigma parameter.\n    epsilon: LJ epsilon parameter.\n\nReturns:\n    ndarray: Pairwise force vectors.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "distances",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "vecs",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "return",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Force",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_lj_forces",
    dependencies: null,
    source_code:
      'def get_lj_forces(\n    distances: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    vecs: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n) -> Annotated[\n    NDArray[np.float64],\n    {\n        "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM",\n        "quantity": "https://qudt.org/vocab/quantitykind/Force",\n    },\n]:\n    """\n    Calculates total Lennard-Jones forces on each atom.\n\n    Args:\n        distances: Pairwise atomic distances.\n        vecs: Distance vectors between atoms.\n        sigma: LJ sigma parameter.\n        epsilon: LJ epsilon parameter.\n\n    Returns:\n        ndarray: Force vectors for each atom.\n    """\n    return get_lj_pw_forces(distances, vecs, sigma, epsilon).sum(axis=1)\n',
    source_code_hash:
      "36af99e977036e602c5bbf72a2d03477be3f2710aaacc94cd5e6e4d7714c769b",
    docstring:
      "Calculates total Lennard-Jones forces on each atom.\n\nArgs:\n    distances: Pairwise atomic distances.\n    vecs: Distance vectors between atoms.\n    sigma: LJ sigma parameter.\n    epsilon: LJ epsilon parameter.\n\nReturns:\n    ndarray: Force vectors for each atom.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "distances",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "vecs",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "return",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Force",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_lj_pressure",
    dependencies: null,
    source_code:
      'def get_lj_pressure(\n    distances: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    vecs: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    volume: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM3",\n            "quantity": "https://qudt.org/vocab/quantitykind/Volume",\n        },\n    ],\n) -> Annotated[\n    NDArray[np.float64],\n    {\n        "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM3",\n        "quantity": "https://qudt.org/vocab/quantitykind/Pressure",\n    },\n]:\n    """\n    Calculates pressure tensor from Lennard-Jones forces.\n\n    Args:\n        distances: Pairwise atomic distances.\n        vecs: Distance vectors between atoms.\n        sigma: LJ sigma parameter.\n        epsilon: LJ epsilon parameter.\n        volume: Volume of the system.\n\n    Returns:\n        ndarray: Pressure tensor.\n    """\n    v = vecs.copy()\n    v[v == np.inf] = 0\n    p = (\n        -0.25\n        * np.einsum(\n            "...i,...j->...ij", get_lj_pw_forces(distances, v, sigma, epsilon), v\n        ).sum(axis=(0, 1))\n        / volume\n    )\n    return p + p.T\n',
    source_code_hash:
      "f99aa090a18fc45855194ef10f15fe01ff6fd79a39306e20ba08382ffaed5f89",
    docstring:
      "Calculates pressure tensor from Lennard-Jones forces.\n\nArgs:\n    distances: Pairwise atomic distances.\n    vecs: Distance vectors between atoms.\n    sigma: LJ sigma parameter.\n    epsilon: LJ epsilon parameter.\n    volume: Volume of the system.\n\nReturns:\n    ndarray: Pressure tensor.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "distances",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "vecs",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "volume",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM3",
        quantity: "https://qudt.org/vocab/quantitykind/Volume",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "return",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM3",
        quantity: "https://qudt.org/vocab/quantitykind/Pressure",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_sigma",
    dependencies: null,
    source_code:
      'def get_sigma(\n    structure: Atoms,\n    cutoff: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/DimensionlessRatio",\n        },\n    ] = 4,\n    sigma_start: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ] = 2,\n    d_sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ] = 1,\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ] = 1,\n    n_cycle: Annotated[\n        int,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/Dimensionless",\n        },\n    ] = 20,\n) -> tuple[\n    Annotated[\n        float,\n        {\n            "label": "sigma",\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    Annotated[\n        NDArray[np.float64],\n        {\n            "label": "p_hist",\n            "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM3",\n            "quantity": "https://qudt.org/vocab/quantitykind/Pressure",\n        },\n    ],\n]:\n    """\n    Optimizes the LJ sigma parameter to achieve zero pressure.\n\n    Args:\n        structure: ASE Atoms object.\n        cutoff: Cutoff radius multiplier.\n        sigma_start: Initial sigma value.\n        d_sigma: Initial step size for sigma adjustment.\n        epsilon: LJ epsilon parameter.\n        n_cycle: Number of optimization cycles.\n\n    Returns:\n        tuple: Optimized sigma value and pressure history.\n    """\n    sigma = sigma_start\n    p_hist = []\n    for _ in range(20):\n        neigh = get_neighbors(\n            structure, num_neighbors=None, cutoff_radius=cutoff * sigma\n        )\n        p = get_lj_pressure(\n            neigh.distances, neigh.vecs, sigma, epsilon, structure.get_volume()\n        )[0, 0]\n        p_hist.append([sigma, p])\n        if p < 0:\n            sigma += d_sigma\n        else:\n            sigma -= d_sigma\n        d_sigma *= 0.5\n    p_hist = np.array(p_hist)\n    return sigma, p_hist\n',
    source_code_hash:
      "b386f269584c664b9db0d5d0d34de97ee56024699f1d6cfa833d23024f54929a",
    docstring:
      "Optimizes the LJ sigma parameter to achieve zero pressure.\n\nArgs:\n    structure: ASE Atoms object.\n    cutoff: Cutoff radius multiplier.\n    sigma_start: Initial sigma value.\n    d_sigma: Initial step size for sigma adjustment.\n    epsilon: LJ epsilon parameter.\n    n_cycle: Number of optimization cycles.\n\nReturns:\n    tuple: Optimized sigma value and pressure history.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "cutoff",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/DimensionlessRatio",
      },
      {
        has_default_value: false,
        label: "sigma_start",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "d_sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "n_cycle",
        datatype: "int",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/Dimensionless",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "p_hist",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM3",
        quantity: "https://qudt.org/vocab/quantitykind/Pressure",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_bulk_modulus",
    dependencies: null,
    source_code:
      'def get_bulk_modulus(\n    structure: Atoms,\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    cutoff: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/DimensionlessRatio",\n        },\n    ] = 4,\n    factor: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/DimensionlessRatio",\n        },\n    ] = 0.99,\n) -> Annotated[\n    float,\n    {\n        "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM3",\n        "quantity": "https://qudt.org/vocab/quantitykind/BulkModulus",\n    },\n]:\n    """\n    Calculates bulk modulus from LJ potential.\n\n    Args:\n        structure: ASE Atoms object.\n        sigma: LJ sigma parameter.\n        epsilon: LJ epsilon parameter.\n        cutoff: Cutoff radius multiplier.\n        factor: Compression factor for finite difference.\n\n    Returns:\n        float: Bulk modulus in eV/Angstrom^3.\n    """\n    neigh = get_neighbors(structure, num_neighbors=None, cutoff_radius=cutoff * sigma)\n    p = get_lj_pressure(\n        neigh.distances, neigh.vecs, sigma, epsilon, structure.get_volume()\n    )\n    p_m = get_lj_pressure(\n        neigh.distances * factor,\n        neigh.vecs * factor,\n        sigma,\n        epsilon,\n        structure.get_volume() * factor**3,\n    )\n    return -(p - p_m)[0, 0] / (1 - factor**3)\n',
    source_code_hash:
      "4c67e08d725321c0598cbcb0bbb4df10f2ea93be01ab9594c4566087b092b098",
    docstring:
      "Calculates bulk modulus from LJ potential.\n\nArgs:\n    structure: ASE Atoms object.\n    sigma: LJ sigma parameter.\n    epsilon: LJ epsilon parameter.\n    cutoff: Cutoff radius multiplier.\n    factor: Compression factor for finite difference.\n\nReturns:\n    float: Bulk modulus in eV/Angstrom^3.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "cutoff",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/DimensionlessRatio",
      },
      {
        has_default_value: false,
        label: "factor",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/DimensionlessRatio",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "return",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM3",
        quantity: "https://qudt.org/vocab/quantitykind/BulkModulus",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_unit_registry",
    dependencies: null,
    source_code:
      'def get_unit_registry() -> Annotated[UnitRegistry, {"label": "unit_registry"}]:\n    """\n    Creates and returns a Pint UnitRegistry for unit conversions.\n\n    Returns:\n        UnitRegistry: Pint unit registry object.\n    """\n    return UnitRegistry()\n',
    source_code_hash:
      "2a24a4b1ad6cbeee0a7c90591ba754b322c824fb1ae3c034a8951d671cd68c1c",
    docstring:
      "Creates and returns a Pint UnitRegistry for unit conversions.\n\nReturns:\n    UnitRegistry: Pint unit registry object.",
    ai_docstring: "",
    inputs: [],
    outputs: [
      {
        has_default_value: false,
        label: "unit_registry",
        datatype: "UnitRegistry",
        unit: null,
        quantity: null,
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_epsilon",
    dependencies: null,
    source_code:
      'def get_epsilon(\n    structure: Atoms,\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    ureg: UnitRegistry,\n    bulk_modulus_dict: dict[\n        str,\n        Annotated[\n            float,\n            {\n                "unit": "https://qudt.org/vocab/unit/GigaPA",\n                "quantity": "https://qudt.org/vocab/quantitykind/BulkModulus",\n            },\n        ],\n    ],\n    epsilon_start: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ] = 0.6,\n    d_epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ] = 0.5,\n    n_cycle: Annotated[\n        int,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/Dimensionless",\n        },\n    ] = 20,\n    cutoff: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/DimensionlessRatio",\n        },\n    ] = 4,\n    factor: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/DimensionlessRatio",\n        },\n    ] = 0.99,\n) -> tuple[\n    Annotated[\n        float,\n        {\n            "label": "epsilon",\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    Annotated[\n        NDArray[np.float64],\n        {\n            "label": "e_hist",\n            "unit": "https://qudt.org/vocab/unit/GigaPA",\n            "quantity": "https://qudt.org/vocab/quantitykind/BulkModulus",\n        },\n    ],\n]:\n    """\n    Optimizes the LJ epsilon parameter to match reference bulk modulus.\n\n    Args:\n        structure: ASE Atoms object.\n        sigma: LJ sigma parameter.\n        ureg: Pint UnitRegistry for unit conversion.\n        bulk_modulus_dict: Dictionary of reference bulk moduli.\n        epsilon_start: Initial epsilon value.\n        d_epsilon: Initial step size for epsilon adjustment.\n        n_cycle: Number of optimization cycles.\n        cutoff: Cutoff radius multiplier.\n        factor: Compression factor for bulk modulus calculation.\n\n    Returns:\n        tuple: Optimized epsilon value and bulk modulus history.\n    """\n    ref_bulk_modulus = bulk_modulus_dict[structure.get_chemical_symbols()[0]]\n    epsilon = epsilon_start\n    e_hist = []\n    for n in range(n_cycle):\n        B = (\n            (\n                get_bulk_modulus(structure, sigma, epsilon)\n                * ureg.electron_volt\n                / ureg.angstrom**3\n            )\n            .to("gigapascal")\n            .magnitude\n        )\n        e_hist.append([epsilon, B])\n        if B > ref_bulk_modulus:\n            epsilon -= d_epsilon\n        else:\n            epsilon += d_epsilon\n        d_epsilon *= 0.5\n    return epsilon, np.array(e_hist)\n',
    source_code_hash:
      "f98d4b98f61df1971405eebff975294f7485a9aeb4f5ff7235e1a418095f2872",
    docstring:
      "Optimizes the LJ epsilon parameter to match reference bulk modulus.\n\nArgs:\n    structure: ASE Atoms object.\n    sigma: LJ sigma parameter.\n    ureg: Pint UnitRegistry for unit conversion.\n    bulk_modulus_dict: Dictionary of reference bulk moduli.\n    epsilon_start: Initial epsilon value.\n    d_epsilon: Initial step size for epsilon adjustment.\n    n_cycle: Number of optimization cycles.\n    cutoff: Cutoff radius multiplier.\n    factor: Compression factor for bulk modulus calculation.\n\nReturns:\n    tuple: Optimized epsilon value and bulk modulus history.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "ureg",
        datatype: "UnitRegistry",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "bulk_modulus_dict",
        datatype: "dict",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "epsilon_start",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "d_epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "n_cycle",
        datatype: "int",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/Dimensionless",
      },
      {
        has_default_value: false,
        label: "cutoff",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/DimensionlessRatio",
      },
      {
        has_default_value: false,
        label: "factor",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/DimensionlessRatio",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "e_hist",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/GigaPA",
        quantity: "https://qudt.org/vocab/quantitykind/BulkModulus",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_cutoff_radius",
    dependencies: null,
    source_code:
      'def get_cutoff_radius(\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    mul: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/DimensionlessRatio",\n        },\n    ] = 4,\n) -> Annotated[\n    float,\n    {\n        "label": "cutoff_radius",\n        "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n        "quantity": "https://qudt.org/vocab/quantitykind/Length",\n    },\n]:\n    """\n    Calculates cutoff radius for neighbor calculations.\n\n    Args:\n        sigma: LJ sigma parameter.\n        mul: Multiplier for cutoff radius.\n\n    Returns:\n        float: Cutoff radius.\n    """\n    cutoff_radius = sigma * mul\n    return cutoff_radius\n',
    source_code_hash:
      "55a5eecb6c5084606e9e5550c6bffa6457e1c5cb8d5f4c8795eed8fe7aa77e74",
    docstring:
      "Calculates cutoff radius for neighbor calculations.\n\nArgs:\n    sigma: LJ sigma parameter.\n    mul: Multiplier for cutoff radius.\n\nReturns:\n    float: Cutoff radius.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "mul",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/DimensionlessRatio",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "cutoff_radius",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_BFGS",
    dependencies: null,
    source_code:
      'def get_BFGS(\n    dx: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    dg: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Force",\n        },\n    ],\n    H: Annotated[\n        NDArray[np.float64],\n        {\n            "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM2",\n            "quantity": "https://qudt.org/vocab/quantitykind/HessianMatrix",\n        },\n    ],\n) -> Annotated[\n    NDArray[np.float64],\n    {\n        "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM2",\n        "quantity": "https://qudt.org/vocab/quantitykind/HessianMatrix",\n    },\n]:\n    """\n    Updates Hessian matrix using BFGS algorithm.\n\n    Args:\n        dx: Change in position.\n        dg: Change in gradient (negative force).\n        H: Current Hessian matrix.\n\n    Returns:\n        ndarray: Updated Hessian matrix.\n    """\n    Hx = H.dot(dx)\n    return np.outer(dg, dg) / dg.dot(dx) - np.outer(Hx, Hx) / dx.dot(Hx) + H\n',
    source_code_hash:
      "2e65f129032530bbeb6943559f4f562ca40a4f54db0904c9a85f49bd71841ca8",
    docstring:
      "Updates Hessian matrix using BFGS algorithm.\n\nArgs:\n    dx: Change in position.\n    dg: Change in gradient (negative force).\n    H: Current Hessian matrix.\n\nReturns:\n    ndarray: Updated Hessian matrix.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "dx",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "dg",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Force",
      },
      {
        has_default_value: false,
        label: "H",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM2",
        quantity: "https://qudt.org/vocab/quantitykind/HessianMatrix",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "return",
        datatype: "ndarray",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM2",
        quantity: "https://qudt.org/vocab/quantitykind/HessianMatrix",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.relax_structure",
    dependencies: null,
    source_code:
      'def relax_structure(\n    structure: Atoms,\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    cutoff_radius: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    h_init: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM2",\n            "quantity": "https://qudt.org/vocab/quantitykind/HessianMatrix",\n        },\n    ] = 100,\n    n_max: Annotated[\n        int,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/Dimensionless",\n        },\n    ] = 100,\n    f_max: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV_PER_ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Force",\n        },\n    ] = 0.01,\n) -> Annotated[Atoms, {"label": "structure"}]:\n    """\n    Relaxes atomic structure using BFGS optimization.\n\n    Args:\n        structure: ASE Atoms object to relax.\n        sigma: LJ sigma parameter.\n        epsilon: LJ epsilon parameter.\n        cutoff_radius: Cutoff radius for neighbor calculations.\n        h_init: Initial Hessian diagonal value.\n        n_max: Maximum number of optimization steps.\n        f_max: Maximum force convergence criterion.\n\n    Returns:\n        Atoms: Relaxed structure.\n    """\n    struct = structure.copy()\n    H = h_init * np.eye(np.prod(structure.positions.shape))\n    x_lst = [struct.positions.copy()]\n    neigh = get_neighbors(struct, num_neighbors=None, cutoff_radius=cutoff_radius)\n    f_lst = [get_lj_forces(neigh.distances, neigh.vecs, sigma, epsilon)]\n    E_hist = []\n    for _ in range(n_max):\n        struct.positions += (np.linalg.inv(H) @ f_lst[-1].flatten()).reshape(-1, 3)\n        neigh = get_neighbors(struct, num_neighbors=None, cutoff_radius=cutoff_radius)\n        x_lst.append(struct.positions.copy())\n        f_lst.append(get_lj_forces(neigh.distances, neigh.vecs, sigma, epsilon))\n        E_hist.append(\n            (\n                get_lj_energy(neigh.distances, sigma, epsilon),\n                np.linalg.norm(f_lst[-1], axis=-1).max(),\n            )\n        )\n        if E_hist[-1][-1] < f_max:\n            break\n        dx = np.diff(x_lst, axis=0).reshape(-1, np.prod(struct.positions.shape))\n        dg = -np.diff(f_lst, axis=0).reshape(-1, np.prod(struct.positions.shape))\n        H = get_BFGS(dx[-1], dg[-1], H)\n    return struct\n',
    source_code_hash:
      "ac0ff5fa6e94bcea8fe813f11b5756632b9bbbb5f8568270bdaca7a67d1723ff",
    docstring:
      "Relaxes atomic structure using BFGS optimization.\n\nArgs:\n    structure: ASE Atoms object to relax.\n    sigma: LJ sigma parameter.\n    epsilon: LJ epsilon parameter.\n    cutoff_radius: Cutoff radius for neighbor calculations.\n    h_init: Initial Hessian diagonal value.\n    n_max: Maximum number of optimization steps.\n    f_max: Maximum force convergence criterion.\n\nReturns:\n    Atoms: Relaxed structure.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "cutoff_radius",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "h_init",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM2",
        quantity: "https://qudt.org/vocab/quantitykind/HessianMatrix",
      },
      {
        has_default_value: false,
        label: "n_max",
        datatype: "int",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/Dimensionless",
      },
      {
        has_default_value: false,
        label: "f_max",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV_PER_ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Force",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_structure",
    dependencies: null,
    source_code:
      'def get_structure(element: str) -> Annotated[Atoms, {"label": "structure"}]:\n    """\n    Creates a bulk crystal structure for the given element.\n\n    Args:\n        element: Chemical symbol of the element.\n\n    Returns:\n        Atoms: Cubic bulk structure.\n    """\n    structure = build.bulk(element, cubic=True)\n    return structure\n',
    source_code_hash:
      "72c525ee1139bc3e013ae3274e609fb06c18663a2362f1c00ba0377b1e25f393",
    docstring:
      "Creates a bulk crystal structure for the given element.\n\nArgs:\n    element: Chemical symbol of the element.\n\nReturns:\n    Atoms: Cubic bulk structure.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "element",
        datatype: "str",
        unit: null,
        quantity: null,
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.repeat_structure",
    dependencies: null,
    source_code:
      'def repeat_structure(\n    structure: Atoms,\n    n_repeat: Annotated[\n        int,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/Dimensionless",\n        },\n    ],\n) -> Annotated[Atoms, {"label": "structure"}]:\n    """\n    Repeats the structure in all three dimensions.\n\n    Args:\n        structure: ASE Atoms object.\n        n_repeat: Number of repetitions in each direction.\n\n    Returns:\n        Atoms: Repeated structure.\n    """\n    return structure.repeat(n_repeat)\n',
    source_code_hash:
      "e28f2e481d0f1d5a62b29e281c69be03d61f58478a979b99d6914afb611330df",
    docstring:
      "Repeats the structure in all three dimensions.\n\nArgs:\n    structure: ASE Atoms object.\n    n_repeat: Number of repetitions in each direction.\n\nReturns:\n    Atoms: Repeated structure.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "n_repeat",
        datatype: "int",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/Dimensionless",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.create_vacancy",
    dependencies: null,
    source_code:
      'def create_vacancy(structure: Atoms) -> Annotated[Atoms, {"label": "vac"}]:\n    """\n    Creates a vacancy by removing the first atom.\n\n    Args:\n        structure: ASE Atoms object.\n\n    Returns:\n        Atoms: Structure with vacancy.\n    """\n    vac = structure.copy()\n    del vac[0]\n    return vac\n',
    source_code_hash:
      "6ec6411cff4b2476ed7b639a76c7a94b5ca5cd2a77fb53d4a1f7c620852f6a4f",
    docstring:
      "Creates a vacancy by removing the first atom.\n\nArgs:\n    structure: ASE Atoms object.\n\nReturns:\n    Atoms: Structure with vacancy.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "vac",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_energy",
    dependencies: null,
    source_code:
      'def get_energy(\n    structure: Atoms,\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    cutoff_radius: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    per_atom: Annotated[\n        bool,\n        {\n            "unit": "https://qudt.org/vocab/unit/DIMENSIONLESS",\n            "quantity": "https://qudt.org/vocab/quantitykind/Dimensionless",\n        },\n    ] = False,\n) -> Annotated[\n    float,\n    {\n        "label": "energy",\n        "unit": "https://qudt.org/vocab/unit/EV",\n        "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n    },\n]:\n    """\n    Calculates the Lennard-Jones energy of a structure.\n\n    Args:\n        structure: ASE Atoms object.\n        sigma: LJ sigma parameter.\n        epsilon: LJ epsilon parameter.\n        cutoff_radius: Cutoff radius for neighbor calculations.\n        per_atom: If True, returns energy per atom.\n\n    Returns:\n        float: Total or per-atom energy.\n    """\n    neigh = get_neighbors(structure, num_neighbors=None, cutoff_radius=cutoff_radius)\n    energy = get_lj_energy(neigh.distances, sigma, epsilon)\n    if per_atom:\n        energy /= len(structure)\n    return energy\n',
    source_code_hash:
      "6637120a768e08331e618a93579b464c5f90e34a89fcb4c236e01db80c9a98f5",
    docstring:
      "Calculates the Lennard-Jones energy of a structure.\n\nArgs:\n    structure: ASE Atoms object.\n    sigma: LJ sigma parameter.\n    epsilon: LJ epsilon parameter.\n    cutoff_radius: Cutoff radius for neighbor calculations.\n    per_atom: If True, returns energy per atom.\n\nReturns:\n    float: Total or per-atom energy.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "cutoff_radius",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "per_atom",
        datatype: "bool",
        unit: "https://qudt.org/vocab/unit/DIMENSIONLESS",
        quantity: "https://qudt.org/vocab/quantitykind/Dimensionless",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "energy",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_energy_difference",
    dependencies: null,
    source_code:
      'def get_energy_difference(\n    e_vac: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    e_bulk: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    structure: Atoms,\n) -> Annotated[\n    float,\n    {\n        "label": "energy",\n        "unit": "https://qudt.org/vocab/unit/EV",\n        "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n    },\n]:\n    """\n    Calculates vacancy formation energy.\n\n    Args:\n        e_vac: Energy of structure with vacancy.\n        e_bulk: Energy per atom of bulk structure.\n        structure: Structure with vacancy.\n\n    Returns:\n        float: Vacancy formation energy.\n    """\n    energy = e_vac - e_bulk * len(structure)\n    return energy\n',
    source_code_hash:
      "6aa2e48d0aa18081939d9ff08d0f679251ffcce8442dec390c5d34b3576d5341",
    docstring:
      "Calculates vacancy formation energy.\n\nArgs:\n    e_vac: Energy of structure with vacancy.\n    e_bulk: Energy per atom of bulk structure.\n    structure: Structure with vacancy.\n\nReturns:\n    float: Vacancy formation energy.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "e_vac",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "e_bulk",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "energy",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_bulk_energy",
    dependencies: null,
    source_code:
      'def get_bulk_energy(\n    bulk: Atoms,\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    cutoff_radius: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n) -> Annotated[\n    float,\n    {\n        "label": "bulk_energy",\n        "unit": "https://qudt.org/vocab/unit/EV",\n        "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n    },\n]:\n    """\n    Calculates energy per atom for bulk structure.\n\n    Args:\n        bulk: Bulk ASE Atoms object.\n        sigma: LJ sigma parameter.\n        epsilon: LJ epsilon parameter.\n        cutoff_radius: Cutoff radius for neighbor calculations.\n\n    Returns:\n        float: Energy per atom.\n    """\n    return get_energy(\n        structure=bulk,\n        sigma=sigma,\n        epsilon=epsilon,\n        cutoff_radius=cutoff_radius,\n        per_atom=True,\n    )\n',
    source_code_hash:
      "887ea59e1144d2c66579bc9c6119bd2124b2944ae2e8b4348f873765be960396",
    docstring:
      "Calculates energy per atom for bulk structure.\n\nArgs:\n    bulk: Bulk ASE Atoms object.\n    sigma: LJ sigma parameter.\n    epsilon: LJ epsilon parameter.\n    cutoff_radius: Cutoff radius for neighbor calculations.\n\nReturns:\n    float: Energy per atom.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "bulk",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "cutoff_radius",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "bulk_energy",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
    ],
  },
  {
    author_name: "John Doe",
    author_email: "john.doe@example.com",
    node_type: "function",
    python_import: "my_nodes.vacancy_formation.get_vac_energy",
    dependencies: null,
    source_code:
      'def get_vac_energy(\n    vacancy_structure: Atoms,\n    sigma: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n    epsilon: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/EV",\n            "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n        },\n    ],\n    cutoff_radius: Annotated[\n        float,\n        {\n            "unit": "https://qudt.org/vocab/unit/ANGSTROM",\n            "quantity": "https://qudt.org/vocab/quantitykind/Length",\n        },\n    ],\n) -> Annotated[\n    float,\n    {\n        "label": "vac_energy",\n        "unit": "https://qudt.org/vocab/unit/EV",\n        "quantity": "https://qudt.org/vocab/quantitykind/Energy",\n    },\n]:\n    """\n    Calculates total energy for structure with vacancy.\n\n    Args:\n        vacancy_structure: ASE Atoms object with vacancy.\n        sigma: LJ sigma parameter.\n        epsilon: LJ epsilon parameter.\n        cutoff_radius: Cutoff radius for neighbor calculations.\n\n    Returns:\n        float: Total energy of vacancy structure.\n    """\n    return get_energy(\n        structure=vacancy_structure,\n        sigma=sigma,\n        epsilon=epsilon,\n        cutoff_radius=cutoff_radius,\n        per_atom=False,\n    )\n',
    source_code_hash:
      "bd2b5cb60a7345b9df57b900d14f14c9b182a32b9e1702d8de3ba8363122c6bd",
    docstring:
      "Calculates total energy for structure with vacancy.\n\nArgs:\n    vacancy_structure: ASE Atoms object with vacancy.\n    sigma: LJ sigma parameter.\n    epsilon: LJ epsilon parameter.\n    cutoff_radius: Cutoff radius for neighbor calculations.\n\nReturns:\n    float: Total energy of vacancy structure.",
    ai_docstring: "",
    inputs: [
      {
        has_default_value: false,
        label: "vacancy_structure",
        datatype: "Atoms",
        unit: null,
        quantity: null,
      },
      {
        has_default_value: false,
        label: "sigma",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
      {
        has_default_value: false,
        label: "epsilon",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
      {
        has_default_value: false,
        label: "cutoff_radius",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/ANGSTROM",
        quantity: "https://qudt.org/vocab/quantitykind/Length",
      },
    ],
    outputs: [
      {
        has_default_value: false,
        label: "vac_energy",
        datatype: "float",
        unit: "https://qudt.org/vocab/unit/EV",
        quantity: "https://qudt.org/vocab/quantitykind/Energy",
      },
    ],
  },
];
