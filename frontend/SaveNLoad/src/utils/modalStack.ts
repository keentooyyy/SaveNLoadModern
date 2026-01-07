type BootstrapModalInstance = {
  hide: () => void;
  show: () => void;
};

type ModalStackEntry = {
  elements: HTMLElement[];
  shellElements: HTMLElement[];
  shellBackdrops: HTMLElement[];
};

const stack = new Map<string, ModalStackEntry>();

const getBootstrapModal = (el: HTMLElement): BootstrapModalInstance | null => {
  const bootstrap = (window as any)?.bootstrap;
  if (!bootstrap?.Modal) {
    return null;
  }
  return bootstrap.Modal.getOrCreateInstance(el);
};

export const pauseBootstrapModals = () => {
  const openModals = Array.from(document.querySelectorAll('.modal.show:not(.modal-shell-root)')) as HTMLElement[];
  const openShells = Array.from(document.querySelectorAll('.modal-shell-root.show')) as HTMLElement[];
  const openShellBackdrops = Array.from(document.querySelectorAll('.modal-shell-backdrop.show')) as HTMLElement[];

  if (!openModals.length && !openShells.length && !openShellBackdrops.length) {
    return null;
  }

  const token = `modal_${Math.random().toString(36).slice(2, 10)}`;
  stack.set(token, { elements: openModals, shellElements: openShells, shellBackdrops: openShellBackdrops });

  openModals.forEach((el) => {
    const instance = getBootstrapModal(el);
    instance?.hide();
  });

  openShells.forEach((el) => el.classList.add('modal-shell-paused'));
  openShellBackdrops.forEach((el) => el.classList.add('modal-shell-paused'));

  return token;
};

export const restoreBootstrapModals = (token: string | null) => {
  if (!token) {
    return;
  }
  const entry = stack.get(token);
  if (!entry) {
    return;
  }
  stack.delete(token);

  entry.elements.forEach((el) => {
    const instance = getBootstrapModal(el);
    instance?.show();
  });

  entry.shellElements.forEach((el) => el.classList.remove('modal-shell-paused'));
  entry.shellBackdrops.forEach((el) => el.classList.remove('modal-shell-paused'));
};
