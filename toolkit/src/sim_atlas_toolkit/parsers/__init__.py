from sim_atlas_toolkit.parsers.parser import get_metadata, register_parser

try:
    from sim_atlas_toolkit.parsers import aiflow

    register_parser(aiflow.parse)
except ImportError:
    pass

try:
    from sim_atlas_toolkit.parsers import dataclass_node

    register_parser(dataclass_node.parse)
except ImportError:
    pass

try:
    from sim_atlas_toolkit.parsers import flowrep_parser

    register_parser(flowrep_parser.parse)
except ImportError:
    pass

try:
    from sim_atlas_toolkit.parsers import pyiron_workflow

    register_parser(pyiron_workflow.parse)
except ImportError:
    pass

try:
    from sim_atlas_toolkit.parsers import python_function

    register_parser(python_function.parse)
except ImportError:
    pass

try:
    from sim_atlas_toolkit.parsers import python_workflow_definition

    register_parser(python_workflow_definition.parse)
except ImportError:
    pass

__all__ = ["get_metadata"]
