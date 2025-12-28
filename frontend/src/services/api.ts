// API Service - Connect to backend
// Clean, typed interface for all backend calls

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Type Definitions
export interface UploadResponse {
  document_id: string;
  filename: string;
  size: number;
  pages: number;
  status: string;
  message: string;
}

export interface ProcessingStatus {
  document_id: string;
  status: string;
  progress_percent: number;
  current_step: string;
  chunks_processed: number;
  total_chunks: number;
  entities_extracted: number;
  relationships_created: number;
  error_message?: string;
}

export interface QueryRequest {
  document_id: string;
  question: string;
  include_context?: boolean;
}
export interface QueryResponse {
  answer: string;
  sources: Array<{
    type?: string;
    page?: number;
    chunk_id?: number;
    text_preview?: string;
  }>;
  retrieval_method: string;
  context_used?: any[];
}

export interface GraphStats {
  total_nodes: number;
  total_relationships: number;
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  status: string;
  pages: number;
}

// API Functions
export const uploadDocument = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
};

export const getProcessingStatus = async (documentId: string): Promise<ProcessingStatus> => {
  const response = await api.get(`/documents/${documentId}/status`);
  return response.data;
};

export const queryDocument = async (request: QueryRequest) => {
  const response = await api.post('/query', {
    document_id: request.document_id,
    question: request.question,
    include_context: request.include_context || false
  });
  return response.data;
};

export const getGraphStats = async (documentId: string): Promise<GraphStats> => {
  const response = await api.get(`/graph/${documentId}/stats`);
  return response.data;
};

export const listDocuments = async (): Promise<DocumentInfo[]> => {
  const response = await api.get('/documents');
  return response.data;
};

export const checkHealth = async (): Promise<{ status: string }> => {
  const response = await axios.get('http://localhost:8000/health');
  return response.data;
};
export interface GraphData {
  nodes: Array<{ id: number; name: string }>;
  links: Array<{ source: number; target: number; type: string }>;
}

export const getGraphData = async (documentId: string, limit: number = 100): Promise<GraphData> => {
  const response = await api.get(`/graph/${documentId}/data?limit=${limit}`);
  return response.data;
};
export default api;