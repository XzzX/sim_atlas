import logging

from sim_atlas_toolkit.parsers.parser import get_metadata, register_parser

logger = logging.getLogger(__name__)

try:
    from sim_atlas_toolkit.parsers import flowrep_parser

    register_parser(flowrep_parser.parse)
except ImportError as exc:
    logger.debug("flowrep parser unavailable: %s", exc)

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

__all__ = ["get_metadata"]
