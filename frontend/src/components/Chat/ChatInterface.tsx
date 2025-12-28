import React, { useState, useEffect, useRef } from 'react';
import { queryDocument, getProcessingStatus } from '../../services/api';
import ReactMarkdown from 'react-markdown';
import './ChatInterface.css';
import SuggestedQuestions from './SuggestedQuestions';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: any[];
  retrieval_method?: string;
  flowchart?: string;
}

interface ChatInterfaceProps {
  documentId: string;
  documentName: string;
  isProcessing: boolean;
  onProcessingComplete: () => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  documentId,
  documentName,
  isProcessing,
  onProcessingComplete
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<any>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Poll processing status
  useEffect(() => {
    if (!isProcessing) return;

    const pollInterval = setInterval(async () => {
      try {
        const status = await getProcessingStatus(documentId);
        setProcessingStatus(status);

        if (status.status === 'completed') {
          clearInterval(pollInterval);
          onProcessingComplete();
          setMessages([{
            role: 'assistant',
            content: `✓ ${documentName} has been processed successfully!\n\n` +
              `**Statistics:**\n` +
              `- ${status.chunks_processed} text chunks created\n` +
              `- ${status.entities_extracted} entities extracted\n` +
              `- ${status.relationships_created} relationships mapped\n\n` +
              `You can now ask me questions about the manual!`
          }]);
          setShowSuggestions(true);
        } else if (status.status === 'failed') {
          clearInterval(pollInterval);
          setMessages([{
            role: 'assistant',
            content: `Processing failed: ${status.error_message}`
          }]);
        } else if (status.status === 'rejected') {
          // REJECTION MESSAGE - Show in UI!
          clearInterval(pollInterval);
          setMessages([{
            role: 'system',
            content: status.error_message || 'Document type not supported'
          }]);
        }
      } catch (err) {
        console.error('Error polling status:', err);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [isProcessing, documentId, documentName, onProcessingComplete]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || isProcessing) return;

    const userMessage: Message = {
      role: 'user',
      content: input
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setShowSuggestions(false); // Hide suggestions after first question

    try {
      const response = await queryDocument({
        document_id: documentId,
        question: input,
        include_context: false
        // Removed retrieval_method - not in interface
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        retrieval_method: response.retrieval_method,
        flowchart: response.flowchart
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error('Query error:', err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your question. Please try again.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleQuestionClick = (question: string) => {
    setInput(question);
    // Auto-submit
    setTimeout(() => {
      const form = document.querySelector('.input-form') as HTMLFormElement;
      if (form) {
        form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      }
    }, 100);
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <h2>{documentName}</h2>
        {isProcessing && processingStatus && (
          <div className="processing-badge">
            Processing... {processingStatus.progress_percent}%
          </div>
        )}
      </div>

      <div className="messages-container">
        {isProcessing && processingStatus && (
          <div className="processing-status">
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${processingStatus.progress_percent}%` }}
              />
            </div>
            <p>{processingStatus.current_step}</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>

              {msg.sources && msg.sources.length > 0 && (
                <div className="sources">
                  <p className="sources-label">Sources:</p>
                  {msg.sources.map((source, i) => (
                    <div key={i} className="source-item">
                      {source.name} ({source.type})
                    </div>
                  ))}
                </div>
              )}

              {msg.retrieval_method && (
                <div className="retrieval-method">
                  Retrieved via: {msg.retrieval_method}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        {/* Suggested Questions */}
        {showSuggestions && messages.length <= 1 && !loading && (
          <SuggestedQuestions onQuestionClick={handleQuestionClick} />
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isProcessing ? "Processing document..." : "Ask a question about the manual..."}
          disabled={loading || isProcessing}
          className="message-input"
        />
        <button 
          type="submit"
          disabled={loading || isProcessing || !input.trim()}
          className="send-button"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatInterface;