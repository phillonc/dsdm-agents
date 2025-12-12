/**
 * useGenUI Hook
 *
 * React hook for interacting with the Generative UI API.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

// API Types
interface GenerationContext {
  symbol?: string;
  current_price?: number;
  positions?: Array<{
    symbol: string;
    strike?: number;
    expiration?: string;
    option_type?: string;
    quantity: number;
  }>;
  watchlist?: string[];
}

interface UserPreferences {
  theme?: 'dark' | 'light' | 'system';
  chart_type?: 'candlestick' | 'line' | 'bar';
  expertise_level?: 'beginner' | 'intermediate' | 'advanced';
}

interface GenerateUIRequest {
  query: string;
  context?: GenerationContext;
  preferences?: UserPreferences;
  stream?: boolean;
}

interface GenerationMetadata {
  query_parsed?: {
    intent: string;
    symbol?: string;
  };
  components_used: string[];
  data_subscriptions: string[];
  evaluation_score?: number;
}

interface GenerationResult {
  generation_id: string;
  status: 'pending' | 'parsing' | 'planning' | 'generating' | 'post_processing' | 'evaluating' | 'complete' | 'failed';
  html?: string;
  metadata: GenerationMetadata;
  created_at: string;
  generation_time_ms: number;
}

interface StreamEvent {
  event: string;
  generation_id?: string;
  progress?: number;
  message?: string;
  html?: string;
  metadata?: GenerationMetadata;
  error?: string;
}

interface UseGenUIOptions {
  apiBaseUrl?: string;
  authToken?: string;
  onProgress?: (progress: number, message: string) => void;
  onError?: (error: Error) => void;
}

interface UseGenUIReturn {
  // State
  html: string | null;
  generationId: string | null;
  status: string;
  progress: number;
  loading: boolean;
  error: Error | null;
  metadata: GenerationMetadata | null;

  // Actions
  generate: (request: GenerateUIRequest) => Promise<GenerationResult | null>;
  generateStream: (request: GenerateUIRequest) => Promise<void>;
  refine: (refinement: string) => Promise<GenerationResult | null>;
  clear: () => void;
}

/**
 * Custom hook for Generative UI operations
 */
export function useGenUI(options: UseGenUIOptions = {}): UseGenUIReturn {
  const {
    apiBaseUrl = 'http://localhost:8004',
    authToken,
    onProgress,
    onError,
  } = options;

  // State
  const [html, setHtml] = useState<string | null>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [metadata, setMetadata] = useState<GenerationMetadata | null>(null);

  // Refs for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);

  // Build headers
  const getHeaders = useCallback(() => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
  }, [authToken]);

  // Generate UI (non-streaming)
  const generate = useCallback(async (
    request: GenerateUIRequest
  ): Promise<GenerationResult | null> => {
    setLoading(true);
    setError(null);
    setProgress(0);
    setStatus('generating');

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/genui/generate`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ ...request, stream: false }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Generation failed');
      }

      const result: GenerationResult = await response.json();

      setGenerationId(result.generation_id);
      setHtml(result.html || null);
      setMetadata(result.metadata);
      setStatus(result.status);
      setProgress(100);

      return result;
    } catch (err: any) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      setStatus('failed');
      onError?.(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, getHeaders, onError]);

  // Generate UI (streaming)
  const generateStream = useCallback(async (
    request: GenerateUIRequest
  ): Promise<void> => {
    // Cancel any existing request
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);
    setProgress(0);
    setStatus('connecting');
    setHtml(null);
    setMetadata(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/genui/generate/stream`, {
        method: 'POST',
        headers: {
          ...getHeaders(),
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(request),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Stream connection failed');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              continue;
            }

            try {
              const event: StreamEvent = JSON.parse(data);

              if (event.generation_id) {
                setGenerationId(event.generation_id);
              }

              if (event.progress !== undefined) {
                setProgress(event.progress);
              }

              if (event.event) {
                setStatus(event.event);
              }

              if (event.message) {
                onProgress?.(event.progress || 0, event.message);
              }

              if (event.event === 'complete') {
                setHtml(event.html || null);
                setMetadata(event.metadata || null);
                setProgress(100);
              }

              if (event.error) {
                throw new Error(event.error);
              }
            } catch (parseError) {
              console.error('Failed to parse SSE event:', parseError);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setStatus('cancelled');
        return;
      }

      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      setStatus('failed');
      onError?.(error);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, getHeaders, onProgress, onError]);

  // Refine existing generation
  const refine = useCallback(async (
    refinement: string
  ): Promise<GenerationResult | null> => {
    if (!generationId) {
      const error = new Error('No generation to refine');
      setError(error);
      onError?.(error);
      return null;
    }

    setLoading(true);
    setError(null);
    setStatus('refining');

    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/genui/refine`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          generation_id: generationId,
          refinement,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Refinement failed');
      }

      const result: GenerationResult = await response.json();

      setGenerationId(result.generation_id);
      setHtml(result.html || null);
      setMetadata(result.metadata);
      setStatus(result.status);

      return result;
    } catch (err: any) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      setStatus('failed');
      onError?.(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [generationId, apiBaseUrl, getHeaders, onError]);

  // Clear state
  const clear = useCallback(() => {
    abortControllerRef.current?.abort();
    setHtml(null);
    setGenerationId(null);
    setStatus('idle');
    setProgress(0);
    setLoading(false);
    setError(null);
    setMetadata(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  return {
    html,
    generationId,
    status,
    progress,
    loading,
    error,
    metadata,
    generate,
    generateStream,
    refine,
    clear,
  };
}

export default useGenUI;
