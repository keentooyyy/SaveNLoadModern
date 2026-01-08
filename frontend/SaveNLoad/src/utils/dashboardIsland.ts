import '@/styles/custom.css';
import '@/styles/app.css';
import DashboardPage from '@/pages/DashboardPage.vue';
import { mountIsland } from '@/utils/islands';

void mountIsland('dashboard', DashboardPage);
