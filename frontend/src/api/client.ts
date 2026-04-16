import { API_BASE_URL, API_INCLUDE_CREDENTIALS, USE_MOCK_API } from "./config";
import { ApiError } from "./errors";
import { mockAdapter } from "./mock-adapter";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type ApiRequestOptions<TBody> = {
  method?: HttpMethod;
  body?: TBody;
  headers?: HeadersInit;
  signal?: AbortSignal;
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

export const apiClient = {
  async request<TResponse, TBody = unknown>(
    path: string,
    options: ApiRequestOptions<TBody> = {},
  ) {
    if (USE_MOCK_API) {
      return mockAdapter.request<TResponse>();
    }

    const response = await fetch(createUrl(path), {
      method: options.method ?? "GET",
      credentials: API_INCLUDE_CREDENTIALS ? "include" : "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options.headers,
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    });

    if (!response.ok) {
      throw new ApiError(response.statusText, response.status, await parseError(response));
    }

    return (await response.json()) as TResponse;
  },

  async stream<TBody>(path: string, options: ApiRequestOptions<TBody>) {
    if (USE_MOCK_API) {
      return mockAdapter.stream(path, options);
    }

    const response = await fetch(createUrl(path), {
      method: options.method ?? "POST",
      credentials: API_INCLUDE_CREDENTIALS ? "include" : "same-origin",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        ...options.headers,
      },
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
