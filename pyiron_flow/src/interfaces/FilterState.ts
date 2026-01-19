import type { Datatype, Unit, Quantity, Annotation } from "./NodeResponse";

export interface FilterState {
    datatype?: Datatype;
    unit?: Unit;
    quantity?: Quantity;
    filterType: 'inputs' | 'outputs' | 'both';
}

export function annotationMatchesFilter(annotation: Annotation, filter: Partial<FilterState>): boolean {
    if (filter.datatype && annotation.datatype !== filter.datatype) {
        return false;
    }
    if (filter.unit && annotation.unit !== filter.unit) {
        return false;
    }
    if (filter.quantity && annotation.quantity !== filter.quantity) {
        return false;
    }
    return true;
}
