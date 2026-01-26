/**
 * Router Configuration
 *
 * Defines all application routes with the main layout.
 */

import { createBrowserRouter } from 'react-router-dom';
import { Layout } from './components/Layout';

// Page components (lazy loaded)
import Dashboard from './pages/Dashboard';
import LeagueList from './pages/LeagueList';
import LeagueDetail from './pages/LeagueDetail';
import TeamList from './pages/TeamList';
import TeamDetail from './pages/TeamDetail';
import PlayerList from './pages/PlayerList';
import PlayerDetail from './pages/PlayerDetail';
import GameList from './pages/GameList';
import GameDetail from './pages/GameDetail';
import SyncPage from './pages/SyncPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: 'leagues',
        element: <LeagueList />,
      },
      {
        path: 'leagues/:leagueId',
        element: <LeagueDetail />,
      },
      {
        path: 'teams',
        element: <TeamList />,
      },
      {
        path: 'teams/:teamId',
        element: <TeamDetail />,
      },
      {
        path: 'players',
        element: <PlayerList />,
      },
      {
        path: 'players/:playerId',
        element: <PlayerDetail />,
      },
      {
        path: 'games',
        element: <GameList />,
      },
      {
        path: 'games/:gameId',
        element: <GameDetail />,
      },
      {
        path: 'sync',
        element: <SyncPage />,
      },
    ],
  },
]);
