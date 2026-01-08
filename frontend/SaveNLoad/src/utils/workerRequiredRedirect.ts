const WORKER_REQUIRED_RETURN_KEY = 'savenload_worker_required_return';

const getCurrentPath = () => (
  `${window.location.pathname}${window.location.search}${window.location.hash}`
);

const normalizeReturnPath = (path: string) => {
  const trimmed = path.trim();
  if (!trimmed) {
    return '';
  }
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    try {
      const url = new URL(trimmed);
      return `${url.pathname}${url.search}${url.hash}`;
    } catch {
      return '';
    }
  }
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
};

export const setWorkerRequiredReturnPath = (path?: string) => {
  if (typeof window === 'undefined') {
    return;
  }
  const target = normalizeReturnPath(path || getCurrentPath());
  if (!target || target.startsWith('/worker-required')) {
    return;
  }
  try {
    window.sessionStorage.setItem(WORKER_REQUIRED_RETURN_KEY, target);
  } catch {
    // ignore storage errors
  }
};

export const getWorkerRequiredReturnPath = () => {
  if (typeof window === 'undefined') {
    return '';
  }
  try {
    return window.sessionStorage.getItem(WORKER_REQUIRED_RETURN_KEY) || '';
  } catch {
    return '';
  }
};

export const clearWorkerRequiredReturnPath = () => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.sessionStorage.removeItem(WORKER_REQUIRED_RETURN_KEY);
  } catch {
    // ignore storage errors
  }
};

export const redirectToWorkerRequired = (returnPath?: string) => {
  const target = normalizeReturnPath(returnPath || getCurrentPath());
  if (target && !target.startsWith('/worker-required')) {
    setWorkerRequiredReturnPath(target);
    window.location.assign(`/worker-required?return=${encodeURIComponent(target)}`);
    return;
  }
  window.location.assign('/worker-required');
};
