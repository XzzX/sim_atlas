import React, { useState, useCallback } from "react";

interface ImportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onLoad: (text: string) => void | Promise<void>;
}

export const ImportDialog: React.FunctionComponent<ImportDialogProps> = ({
  isOpen,
  onClose,
  onLoad,
}) => {
  const [text, setText] = useState("");
  const [isDragActive, setIsDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
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
    setText("");
    onClose();
  };

  const handleExit = () => {
    setText("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex justify-center items-center z-50"
      onClick={handleExit}
    >
      <div
        className="bg-white rounded-lg shadow-md p-6 max-w-2xl w-11/12 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-gray-900">Import Workflow</h2>
        <div
          className={`relative border-2 border-dashed rounded p-4 transition-colors ${
            isDragActive
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 bg-gray-50"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste JSON here or drag and drop a file..."
            className="w-full h-64 p-3 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 resize-none"
          />
          {isDragActive && (
            <div className="absolute inset-0 flex items-center justify-center bg-blue-500/20 rounded text-blue-600 font-semibold pointer-events-none">
              Drop your file here
            </div>
          )}
        </div>
        <div className="flex gap-2 justify-end">
          <button
            onClick={handleLoad}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors font-medium"
          >
            Load
          </button>
          <button
            onClick={handleExit}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100 transition-colors font-medium"
          >
            Exit
          </button>
        </div>
      </div>
    </div>
  );
};
