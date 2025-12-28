import React, { useState } from 'react';
import './App.css';
import FileUpload from './components/Upload/FileUpload';
import ChatInterface from './components/Chat/ChatInterface';
import DocumentPanel from './components/DocumentPanel/DocumentPanel';
import Header from './components/Layout/Header';

interface AppState {
  currentDocumentId: string | null;
  documentName: string | null;
  isProcessing: boolean;
  isReady: boolean;
}

function App() {
  const [state, setState] = useState<AppState>({
    currentDocumentId: null,
    documentName: null,
    isProcessing: false,
    isReady: false,
  });

  const handleUploadComplete = (documentId: string, filename: string) => {
    setState({
      currentDocumentId: documentId,
      documentName: filename,
      isProcessing: true,
      isReady: false,
    });
  };

  const handleProcessingComplete = () => {
    setState(prev => ({
      ...prev,
      isProcessing: false,
      isReady: true,
    }));
  };

  const handleQuestionClick = (question: string) => {
    // This will be passed to ChatInterface to auto-fill the question
    const event = new CustomEvent('auto-question', { detail: question });
    window.dispatchEvent(event);
  };

  const handleReset = () => {
    // Reset to upload screen
    setState({
      currentDocumentId: null,
      documentName: null,
      isProcessing: false,
      isReady: false,
    });
  };

  return (
    <div className="App">
      <Header 
        onReset={handleReset}
        hasDocument={!!state.currentDocumentId}
      />
      
      <div className="main-container">
        {!state.currentDocumentId ? (
          <div className="upload-section">
            <h1>Knowledge Graph Builder</h1>
            <p>Upload any technical manual to create an intelligent knowledge graph</p>
            <FileUpload onUploadComplete={handleUploadComplete} />
          </div>
        ) : (
          <div className="workspace">
            {/* Left panel - Document Intelligence */}
            <div className="document-panel-container">
              <DocumentPanel
                documentId={state.currentDocumentId}
                documentName={state.documentName || ''}
                isReady={state.isReady}
                onQuestionClick={handleQuestionClick}
              />
            </div>
            
            {/* Right panel - Chat interface */}
            <div className="chat-panel">
              <ChatInterface
                documentId={state.currentDocumentId}
                documentName={state.documentName || ''}
                isProcessing={state.isProcessing}
                onProcessingComplete={handleProcessingComplete}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;