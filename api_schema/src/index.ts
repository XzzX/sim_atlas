// Entry point of sim-atlas-api-schema (ADR-0027). Everything in gen/ is generated
// by scripts/gen-api-schema; only hand-written conveniences live here.
import {
  ArtifactTypeSchema,
  type ArtifactType as GeneratedArtifactType,
} from "./gen/zod.gen";

export * from "./gen/zod.gen";

/** Enum-style access to the values, e.g. `ArtifactType.workflow`. */
export const ArtifactType = ArtifactTypeSchema.enum;
export type ArtifactType = GeneratedArtifactType;
