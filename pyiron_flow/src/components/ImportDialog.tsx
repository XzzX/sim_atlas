import React, { useState, useCallback } from 'react';
import '../styles/ImportDialog.css';

interface ImportDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onLoad: (text: string) => void;
}

export const ImportDialog: React.FunctionComponent<ImportDialogProps> = ({ isOpen, onClose, onLoad }) => {
    const [text, setText] = useState('');
    const [isDragActive, setIsDragActive] = useState(false);

    const handleDrag = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setIsDragActive(true);
        } else if (e.type === 'dragleave') {
            setIsDragActive(false);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);

        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            const file = files[0];
            const reader = new FileReader();
            reader.onload = (event) => {
                if (event.target?.result) {
                    setText(event.target.result as string);
                }
            };
            reader.readAsText(file);
        }
    }, []);

    const handleLoad = () => {
        onLoad(text);
        setText('');
        onClose();
    };

    const handleExit = () => {
        setText('');
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="import-dialog-overlay" onClick={handleExit}>
            <div className="import-dialog" onClick={(e) => e.stopPropagation()}>
                <h2>Import Workflow</h2>
                <div
                    className={`import-drop-zone ${isDragActive ? 'active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                >
                    <textarea
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="Paste JSON here or drag and drop a file..."
                        className="import-textarea"
                    />
                    {isDragActive && <div className="drag-overlay">Drop your file here</div>}
                </div>
                <div className="import-dialog-buttons">
                    <button onClick={handleLoad} className="load-button">
                        Load
                    </button>
                    <button onClick={handleExit} className="exit-button">
                        Exit
                    </button>
                </div>
            </div>
        </div>
    );
};
