export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export const USE_MOCK_API =
  process.env.NEXT_PUBLIC_USE_API_MOCKS === "true" || API_BASE_URL.length === 0;

export const API_INCLUDE_CREDENTIALS =
  process.env.NEXT_PUBLIC_API_INCLUDE_CREDENTIALS === "true";
