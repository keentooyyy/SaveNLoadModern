type Toastr = {
  success?: (message: string, title?: string) => void;
  error?: (message: string, title?: string) => void;
  info?: (message: string, title?: string) => void;
  warning?: (message: string, title?: string) => void;
};

const getToastr = () => (window as any).toastr as Toastr | undefined;
const FLASH_KEY = 'snl_flash_toast';

type FlashPayload = {
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  title?: string;
};

const setFlash = (payload: FlashPayload) => {
  try {
    window.sessionStorage.setItem(FLASH_KEY, JSON.stringify(payload));
  } catch {
    // ignore
  }
};

const consumeFlash = (): FlashPayload | null => {
  try {
    const raw = window.sessionStorage.getItem(FLASH_KEY);
    if (!raw) {
      return null;
    }
    window.sessionStorage.removeItem(FLASH_KEY);
    return JSON.parse(raw) as FlashPayload;
  } catch {
    return null;
  }
};

export const notify = {
  success: (message: string, title?: string) => {
    const t = getToastr();
    if (t?.success) {
      t.success(message, title);
    }
  },
  error: (message: string, title?: string) => {
    const t = getToastr();
    if (t?.error) {
      t.error(message, title);
    }
  },
  info: (message: string, title?: string) => {
    const t = getToastr();
    if (t?.info) {
      t.info(message, title);
    }
  },
  warning: (message: string, title?: string) => {
    const t = getToastr();
    if (t?.warning) {
      t.warning(message, title);
    }
  },
  flashSuccess: (message: string, title?: string) => {
    setFlash({ type: 'success', message, title });
  },
  flashError: (message: string, title?: string) => {
    setFlash({ type: 'error', message, title });
  },
  flashInfo: (message: string, title?: string) => {
    setFlash({ type: 'info', message, title });
  },
  flashWarning: (message: string, title?: string) => {
    setFlash({ type: 'warning', message, title });
  },
  showFlash: () => {
    const payload = consumeFlash();
    if (!payload) {
      return;
    }
    const t = getToastr();
    if (!t) {
      return;
    }
    const handler = t[payload.type];
    if (handler) {
      handler(payload.message, payload.title);
    }
  }
};
