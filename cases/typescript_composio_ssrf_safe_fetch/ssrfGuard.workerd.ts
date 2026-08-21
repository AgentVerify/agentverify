class ComposioBlockedInternalUrlError extends Error {}

export const ssrfSafeFetch = async (rawUrl: string): Promise<Response> => {
  throw new ComposioBlockedInternalUrlError('unsupported', { cause: rawUrl });
};

export const ssrfSafeFetchWhereSupported = async (
  rawUrl: string,
  init: RequestInit = {},
): Promise<Response> => fetch(rawUrl, init);
