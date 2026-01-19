import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import '../styles/AddNodeDialog.css';
import { nodes } from '../NodeStore';
import { type NodeResponse } from './NodeResponse';

interface AddNodeDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onAdd: (nodeData: NodeResponse) => void;
}

export const AddNodeDialog: React.FunctionComponent<AddNodeDialogProps> = ({ isOpen, onClose, onAdd }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [filteredNodes, setFilteredNodes] = useState<NodeResponse[]>(nodes);

    useEffect(() => {
        if (searchTerm === '') {
            setFilteredNodes(nodes);
        } else {
            const term = searchTerm.toLowerCase();
            setFilteredNodes(nodes.filter(node =>
                node.python_import?.toLowerCase().includes(term) ||
                node.docstring?.toLowerCase().includes(term)
            ));
        }
    }, [searchTerm]);

    const handleAdd = (node: NodeResponse) => {
        onAdd(node);
        setSearchTerm('');
        onClose();
    };

    const handleCancel = () => {
        setSearchTerm('');
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="add-node-dialog-overlay" onClick={handleCancel}>
            <div className="add-node-dialog" onClick={(e) => { e.stopPropagation(); }}>
                <h2>Add Node</h2>
                <input
                    type="text"
                    placeholder="Search nodes..."
                    value={searchTerm}
                    onChange={(e) => { setSearchTerm(e.target.value); }}
                    className="search-input"
                    autoFocus
                />
                <div className="node-list">
                    {filteredNodes.map((node) => (
                        <div
                            key={node.python_import}
                            className="node-item"
                            onClick={() => { handleAdd(node); }}
                        >
                            <div className="node-import">{node.python_import}</div>
                            <div className="node-docstring">{node.docstring}</div>
                        </div>
                    ))}
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
