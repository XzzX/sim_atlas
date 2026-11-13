export interface NameAllocator {
  allocate: (base: string) => string;
}

/**
 * Hands out unique labels. With `alwaysIndex` every name gets a numeric suffix,
 * which reproduces flowrep's node-label convention (`mul` -> `mul_0`, see
 * flowrep/parsers/label_helpers.py); without it a base name is used as-is until
 * it collides.
 */
export function createNameAllocator(alwaysIndex: boolean): NameAllocator {
  const used = new Set<string>();
  const counters = new Map<string, number>();
  return {
    allocate(base: string): string {
      if (!alwaysIndex && !used.has(base)) {
        used.add(base);
        return base;
      }
      let index = counters.get(base) ?? 0;
      let candidate = `${base}_${index}`;
      while (used.has(candidate)) {
        index += 1;
        candidate = `${base}_${index}`;
      }
      counters.set(base, index + 1);
      used.add(candidate);
      return candidate;
    },
  };
}
