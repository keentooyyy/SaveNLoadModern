import '@/styles/custom.css';
import '@/styles/app.css';
import GameDetailPage from '@/pages/GameDetailPage.vue';
import { mountIsland } from '@/utils/islands';

void mountIsland('game-detail', GameDetailPage);
