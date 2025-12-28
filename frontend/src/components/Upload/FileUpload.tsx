import React, { useState } from 'react';
import { uploadDocument } from '../../services/api';
import './FileUpload.css';

interface Props {
  onUploadComplete: (documentId: string, filename: string) => void;
}

const FileUpload: React.FC<Props> = ({ onUploadComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith('.pdf')) {
      setError('Please upload a PDF file');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const response = await uploadDocument(file);
      onUploadComplete(response.document_id, response.filename);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
      setUploading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  return (
    <div className="file-upload">
      <div
        className={`upload-zone ${dragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          accept=".pdf"
          onChange={handleChange}
          disabled={uploading}
          style={{ display: 'none' }}
        />
        
        {uploading ? (
          <div className="uploading-state">
            <div className="spinner"></div>
            <p>Uploading document...</p>
          </div>
        ) : (
          <>
            <div className="upload-icon">📄</div>
            <h3>Drop your PDF here</h3>
            <p>or</p>
            <label htmlFor="file-input" className="upload-button">
              Choose File
            </label>
            <p className="upload-note">
              PDF files only • Up to 50 pages
            </p>
          </>
        )}
      </div>
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default FileUpload;