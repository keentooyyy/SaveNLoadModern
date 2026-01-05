// WS mirror from SaveNLoad/templates: shared helpers for UI sockets.
const API_BASE = import.meta.env.VITE_API_BASE as string | undefined;
const WS_BASE = import.meta.env.VITE_WS_BASE as string | undefined;

const normalizePath = (path: string) => (path.startsWith('/') ? path : `/${path}`);

export const buildWsUrl = (path: string, query?: Record<string, string>) => {
  const normalizedPath = normalizePath(path);
  const base = WS_BASE || API_BASE || window.location.origin;
  const baseUrl = new URL(base, window.location.origin);
  const wsProtocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = new URL(`${wsProtocol}//${baseUrl.host}${normalizedPath}`);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value) {
        url.searchParams.set(key, value);
      }
    });
  }
  return url.toString();
};
