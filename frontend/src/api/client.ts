import { API_BASE_URL, API_INCLUDE_CREDENTIALS, USE_MOCK_API } from "./config";
import { ApiError } from "./errors";
import { mockAdapter } from "./mock-adapter";
import { getAccessToken } from "@/features/auth/lib/token-storage";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type ApiRequestOptions<TBody> = {
  method?: HttpMethod;
  body?: TBody;
  headers?: HeadersInit;
  signal?: AbortSignal;
  auth?: boolean;
};

function createUrl(path: string) {
  if (path.startsWith("http")) {
    return path;
  }

  return `${API_BASE_URL}${path}`;
}

async function parseError(response: Response) {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

async function parseResponse<TResponse>(response: Response) {
  const text = await response.text();

  if (!text) {
    return undefined as TResponse;
  }

  return JSON.parse(text) as TResponse;
}

function createHeaders(
  options: ApiRequestOptions<unknown>,
  accept: "application/json" | "text/event-stream",
) {
  const headers = new Headers(options.headers);

  if (!headers.has("Accept")) {
    headers.set("Accept", accept);
  }

  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (options.auth !== false) {
    const accessToken = getAccessToken();

    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
  }

  return headers;
}

export const apiClient = {
  async request<TResponse, TBody = unknown>(path: string, options: ApiRequestOptions<TBody> = {}) {
    if (USE_MOCK_API) {
      return mockAdapter.request<TResponse, TBody>(path, options);
    }

    const response = await fetch(createUrl(path), {
      method: options.method ?? "GET",
      credentials: API_INCLUDE_CREDENTIALS ? "include" : "same-origin",
      headers: createHeaders(options, "application/json"),
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    });

    if (!response.ok) {
      throw new ApiError(response.statusText, response.status, await parseError(response));
    }

    return parseResponse<TResponse>(response);
  },

  async stream<TBody>(path: string, options: ApiRequestOptions<TBody>) {
    if (USE_MOCK_API) {
      return mockAdapter.stream(path, options);
    }

    const response = await fetch(createUrl(path), {
      method: options.method ?? "POST",
      credentials: API_INCLUDE_CREDENTIALS ? "include" : "same-origin",
      headers: createHeaders(options, "text/event-stream"),
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    });

    if (!response.ok) {
      throw new ApiError(response.statusText, response.status, await parseError(response));
    }

    if (!response.body) {
      throw new ApiError("Streaming response body is empty.", response.status);
    }

    return response.body;
  },
};
