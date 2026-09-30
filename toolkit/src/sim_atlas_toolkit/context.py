from dataclasses import dataclass

from sim_atlas_toolkit.node_store import NodeStore
from sim_atlas_toolkit.settings import ToolkitSettings


@dataclass(frozen=True, slots=True)
class ParseContext:
    """Collaborators every parser needs: configuration plus the node store."""

    settings: ToolkitSettings
    store: NodeStore
