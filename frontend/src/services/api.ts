/**
 * API service for communicating with the LawLens Django REST endpoint.
 */

import type { ChatRequest, LegalResponse } from '../types';

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

/**
 * Send a legal query to the LawLens POST /api/chat/ endpoint.
 *
 * @param query The user's legal question.
 * @param conversationId Optional conversation/session ID for conversational context.
 * @returns Serialized LegalResponse matching backend contract.
 */
export async function sendLegalQuery(
  query: string,
  conversationId?: string | null
): Promise<LegalResponse> {
  const payload: ChatRequest = {
    query: query.trim(),
  };

  if (conversationId && conversationId.trim()) {
    payload.conversation_id = conversationId.trim();
  }

  // Construct primary URL and dev proxy fallback URL
  const primaryUrl = API_BASE_URL ? `${API_BASE_URL}/api/chat/` : '/api/chat/';
  const fallbackUrl = '/api/chat/';

  const executeRequest = async (url: string): Promise<Response> => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout for RAG/LLM

    try {
      return await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }
  };

  let response: Response;
  try {
    response = await executeRequest(primaryUrl);
  } catch (err: unknown) {
    // If primary URL is absolute and failed (e.g. CORS or network refusal in local browser),
    // and primary is different from relative proxy, try the Vite dev proxy
    if (primaryUrl !== fallbackUrl && err instanceof TypeError) {
      try {
        response = await executeRequest(fallbackUrl);
      } catch {
        throw new Error(
          'Unable to reach the LawLens legal API service. Please verify that the backend server is running.'
        );
      }
    } else {
      if (err instanceof Error && err.name === 'AbortError') {
        throw new Error('Request timed out while reviewing the legal corpus. Please try again.');
      }
      throw new Error(
        'Unable to connect to LawLens. Please check your network connection and ensure the backend is available.'
      );
    }
  }

  if (!response.ok) {
    let errorMessage = `Server returned status ${response.status}.`;
    try {
      const errorJson = await response.json();
      if (errorJson && typeof errorJson === 'object') {
        if (typeof errorJson.error === 'string') {
          errorMessage = errorJson.error;
        } else if (typeof errorJson.query === 'string') {
          errorMessage = errorJson.query;
        } else if (Array.isArray(errorJson.query)) {
          errorMessage = errorJson.query.join(', ');
        }
      }
    } catch {
      // Use fallback status message if body is not JSON
    }

    if (response.status === 404) {
      throw new Error(`Conversation not found. ${errorMessage}`);
    } else if (response.status === 400) {
      throw new Error(`Invalid request: ${errorMessage}`);
    } else if (response.status === 500) {
      throw new Error('An internal error occurred while processing your legal request.');
    }
    throw new Error(errorMessage);
  }

  const data = (await response.json()) as LegalResponse;

  // Ensure safe defaults for all fields
  return {
    query: data.query || query,
    answer: data.answer || 'No answer content received from legal service.',
    supported: Boolean(data.supported),
    citations: Array.isArray(data.citations) ? data.citations : [],
    refusal_reason: data.refusal_reason || null,
    is_refusal: Boolean(data.is_refusal),
    language: data.language || 'en',
    session_id: data.session_id || data.conversation_id,
    conversation_id: data.conversation_id || data.session_id,
  };
}
