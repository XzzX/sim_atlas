import logging

from sim_atlas_toolkit.parsers.parser import get_metadata, register_parser

logger = logging.getLogger(__name__)

try:
    from sim_atlas_toolkit.parsers import flowrep_parser

    register_parser(flowrep_parser.parse)
except ImportError as exc:
    logger.debug("flowrep parser unavailable: %s", exc)

try:
    from sim_atlas_toolkit.parsers import pyiron_workflow

    register_parser(pyiron_workflow.parse)
except ImportError as exc:
    logger.debug("pyiron_workflow parser unavailable: %s", exc)

try:
    from sim_atlas_toolkit.parsers import dataclass_node

    register_parser(dataclass_node.parse)
except ImportError as exc:
    logger.debug("dataclass_node parser unavailable: %s", exc)

try:
    from sim_atlas_toolkit.parsers import python_function

    register_parser(python_function.parse)
except ImportError as exc:
    logger.debug("python_function parser unavailable: %s", exc)

try:
    from sim_atlas_toolkit.parsers import python_workflow_definition

    register_parser(python_workflow_definition.parse)
except ImportError as exc:
    logger.debug("python_workflow_definition parser unavailable: %s", exc)

try:
    from sim_atlas_toolkit.parsers import aiflow

    register_parser(aiflow.parse)
except ImportError as exc:
    logger.debug("aiflow parser unavailable: %s", exc)

__all__ = ["get_metadata"]
