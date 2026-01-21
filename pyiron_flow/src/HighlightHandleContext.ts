import { createContext } from 'react';
import type { FilterState } from './interfaces/FilterState';

export const HighlightHandleContext = createContext<Partial<FilterState> | undefined>(undefined);