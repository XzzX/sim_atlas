# sim-atlas-models

Shared [Pydantic](https://docs.pydantic.dev/) wire models of the
[Simulation Atlas](https://github.com/XzzX/sim_atlas) REST API. The `sim-atlas`
backend and the `sim-atlas-toolkit` client both import their request and response
schemas from this package, so the two sides cannot drift apart.

```python
from sim_atlas_models import NodeRequest, NodeResponse
```

## Field ownership

* **Request models** (`NodeRequest`, `Annotation`, `Reference`, `ExecutionResultRequest`,
  `WfDefinition`, …) contain only fields the client owns and reject any other field
  (`extra="forbid"`).
* **Response models** (`NodeResponse`, `AnnotationResponse`, `ReferenceResponse`,
  `ExecutionResultResponse`) add the fields the server generates or derives
  (`creator_*`, `creation_timestamp`, `used_by`, `connections`,
  `ReferenceResponse.artifact_type`) and ignore unknown fields (`extra="ignore"`).

See ADR-0024 in the repository for the rationale.

## Versioning

`sim-atlas-models` is released in lockstep with `sim-atlas` and `sim-atlas-toolkit`,
and both pin it to the exact same version.
