import React, { useState, useEffect, useMemo } from 'react';
import { Button } from "@/components/ui/button";
import '../styles/AddNodeDialog.css';
import { nodes } from '../interfaces/NodeStore';
import { type NodeResponse } from '../interfaces/NodeResponse';
import { ChevronDown } from 'lucide-react';
import { annotationMatchesFilter, type FilterState } from '../interfaces/FilterState';

interface AddNodeDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onAdd: (nodeData: NodeResponse) => void;
    initialFilters: Partial<FilterState>;
}

export const AddNodeDialog: React.FunctionComponent<AddNodeDialogProps> = ({ isOpen, onClose, onAdd, initialFilters }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [showFilters, setShowFilters] = useState(false);
    const [filters, setFilters] = useState<Partial<FilterState>>(initialFilters);

    // Update filters when initialFilters change
    useEffect(() => {
        setFilters(initialFilters);
        // Show filters if there are initial filters set
        if (initialFilters.datatype || initialFilters.unit || initialFilters.quantity) {
            setShowFilters(true);
        }
    }, [initialFilters]);

    // Handle Escape key to close dialog
    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                handleCancel();
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [isOpen]);

    // Extract unique filter values from all nodes
    const availableFilters = useMemo(() => {
        const datatypes = new Set<string>();
        const units = new Set<string>();
        const quantities = new Set<string>();

        nodes.forEach(node => {
            [...Object.values(node.inputs), ...Object.values(node.outputs)].forEach(annotation => {
                if (annotation.datatype) datatypes.add(annotation.datatype);
                if (annotation.unit) units.add(annotation.unit);
                if (annotation.quantity) quantities.add(annotation.quantity);
            });
        });

        return {
            datatypes: Array.from(datatypes).sort(),
            units: Array.from(units).sort(),
            quantities: Array.from(quantities).sort(),
        };
    }, []);

    const filteredNodes = useMemo(() => {
        return nodes.filter(node => {
            // Search filter
            if (searchTerm !== '') {
                const term = searchTerm.toLowerCase();
                if (!node.python_import?.toLowerCase().includes(term) &&
                    !node.docstring?.toLowerCase().includes(term)) {
                    return false;
                }
            }

            // Attribute filters
            const hasActiveFilters = filters.datatype || filters.unit || filters.quantity;
            if (!hasActiveFilters) {
                return true;
            }

            const inputsMatch = filters.filterType !== 'outputs' &&
                Object.values(node.inputs).some((annotation) => annotationMatchesFilter(annotation, filters));
            const outputsMatch = filters.filterType !== 'inputs' &&
                Object.values(node.outputs).some((annotation) => annotationMatchesFilter(annotation, filters));

            return filters.filterType === 'both' ? (inputsMatch || outputsMatch) : (inputsMatch || outputsMatch);
        });
    }, [searchTerm, filters]);

    const handleAdd = (node: NodeResponse) => {
        onAdd(node);
        setSearchTerm('');
        setFilters({ datatype: '', unit: '', quantity: '', filterType: 'both' });
        setShowFilters(false);
        onClose();
    };

    const handleCancel = () => {
        setSearchTerm('');
        setFilters({ datatype: '', unit: '', quantity: '', filterType: 'both' });
        setShowFilters(false);
        onClose();
    };

    const handleClearFilters = () => {
        setFilters({ datatype: '', unit: '', quantity: '', filterType: 'both' });
    };

    const hasActiveFilters = filters.datatype || filters.unit || filters.quantity;

    if (!isOpen) return null;

    return (
        <div className="add-node-dialog-overlay" onClick={handleCancel}>
            <div className="add-node-dialog" onClick={(e) => { e.stopPropagation(); }}>
                <h2>Add Node</h2>
                <div className="search-section">
                    <input
                        type="text"
                        placeholder="Search nodes..."
                        value={searchTerm}
                        onChange={(e) => { setSearchTerm(e.target.value); }}
                        className="search-input"
                        autoFocus
                    />
                    <button
                        className="filter-toggle"
                        onClick={() => { setShowFilters(!showFilters); }}
                        title="Toggle filters"
                    >
                        <ChevronDown size={18} style={{ transform: showFilters ? 'rotate(180deg)' : '' }} />
                    </button>
                </div>

                {showFilters && (
                    <div className="filters-section">
                        <div className="filter-group">
                            <label>Filter Type:</label>
                            <div className="filter-options">
                                <label className="radio-label">
                                    <input
                                        type="radio"
                                        name="filterType"
                                        value="both"
                                        checked={filters.filterType === 'both'}
                                        onChange={(e) => setFilters({ ...filters, filterType: e.target.value as 'inputs' | 'outputs' | 'both' })}
                                    />
                                    Both
                                </label>
                                <label className="radio-label">
                                    <input
                                        type="radio"
                                        name="filterType"
                                        value="inputs"
                                        checked={filters.filterType === 'inputs'}
                                        onChange={(e) => setFilters({ ...filters, filterType: e.target.value as 'inputs' | 'outputs' | 'both' })}
                                    />
                                    Inputs
                                </label>
                                <label className="radio-label">
                                    <input
                                        type="radio"
                                        name="filterType"
                                        value="outputs"
                                        checked={filters.filterType === 'outputs'}
                                        onChange={(e) => setFilters({ ...filters, filterType: e.target.value as 'inputs' | 'outputs' | 'both' })}
                                    />
                                    Outputs
                                </label>
                            </div>
                        </div>

                        <div className="filter-group">
                            <label>Datatype:</label>
                            <select
                                value={filters.datatype ?? ''}
                                onChange={(e) => setFilters({ ...filters, datatype: e.target.value })}
                                className="filter-select"
                            >
                                <option value="">All</option>
                                {availableFilters.datatypes.map(dt => (
                                    <option key={dt} value={dt}>{dt}</option>
                                ))}
                            </select>
                        </div>

                        <div className="filter-group">
                            <label>Unit:</label>
                            <select
                                value={filters.unit ?? ''}
                                onChange={(e) => setFilters({ ...filters, unit: e.target.value })}
                                className="filter-select"
                            >
                                <option value="">All</option>
                                {availableFilters.units.map(u => (
                                    <option key={u} value={u}>{u}</option>
                                ))}
                            </select>
                        </div>

                        <div className="filter-group">
                            <label>Quantity:</label>
                            <select
                                value={filters.quantity ?? ''}
                                onChange={(e) => setFilters({ ...filters, quantity: e.target.value })}
                                className="filter-select"
                            >
                                <option value="">All</option>
                                {availableFilters.quantities.map(q => (
                                    <option key={q} value={q}>{q}</option>
                                ))}
                            </select>
                        </div>

                        {hasActiveFilters && (
                            <button className="clear-filters-btn" onClick={handleClearFilters}>
                                Clear Filters
                            </button>
                        )}
                    </div>
                )}

                <div className="node-list">
                    {filteredNodes.length > 0 ? (
                        filteredNodes.map((node) => (
                            <div
                                key={node.source_code_hash}
                                className="node-item"
                                onClick={() => { handleAdd(node); }}
                            >
                                <div className="node-import">{node.python_import}</div>
                                <div className="node-docstring">{node.docstring}</div>
                            </div>
                        ))
                    ) : (
                        <div className="no-results">No nodes match your filters</div>
                    )}
                </div>
                <div className="dialog-buttons">
                    <Button
                        onClick={handleCancel}
                        variant="outline"
                        className="cancel-button"
                    >
                        Cancel
                    </Button>
                </div>
            </div>
        </div>
    );
};
