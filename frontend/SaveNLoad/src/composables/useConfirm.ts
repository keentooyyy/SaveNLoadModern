import { reactive } from 'vue';
import { pauseBootstrapModals, restoreBootstrapModals } from '@/utils/modalStack';

type ConfirmOptions = {
  title?: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'primary' | 'danger';
};

type ConfirmState = {
  open: boolean;
  title: string;
  message: string;
  confirmText: string;
  cancelText: string;
  variant: 'primary' | 'danger';
  resolve: ((value: boolean) => void) | null;
  pauseToken: string | null;
};

const state = reactive<ConfirmState>({
  open: false,
  title: 'Confirm',
  message: 'Are you sure?',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  variant: 'primary',
  resolve: null,
  pauseToken: null
});

const close = () => {
  state.open = false;
  state.resolve = null;
  restoreBootstrapModals(state.pauseToken);
  state.pauseToken = null;
};

const requestConfirm = (options: ConfirmOptions = {}) => {
  state.title = options.title || 'Confirm';
  state.message = options.message || 'Are you sure?';
  state.confirmText = options.confirmText || 'Confirm';
  state.cancelText = options.cancelText || 'Cancel';
  state.variant = options.variant || 'primary';
  state.pauseToken = pauseBootstrapModals();
  state.open = true;
  return new Promise<boolean>((resolve) => {
    state.resolve = resolve;
  });
};

const confirmAction = () => {
  if (state.resolve) {
    state.resolve(true);
  }
  close();
};

const cancelAction = () => {
  if (state.resolve) {
    state.resolve(false);
  }
  close();
};

export const useConfirm = () => ({
  state,
  requestConfirm,
  confirmAction,
  cancelAction
});
