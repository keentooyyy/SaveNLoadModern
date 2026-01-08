import '@/styles/custom.css';
import '@/styles/app.css';
import WorkerRequiredPage from '@/pages/WorkerRequiredPage.vue';
import { mountIsland } from '@/utils/islands';

void mountIsland('worker-required', WorkerRequiredPage);
