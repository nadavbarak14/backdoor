/**
 * Dashboard Page
 *
 * Home page showing overview of all data and recent activity.
 */

import { Link } from 'react-router-dom';
import { Trophy, Users, UserCircle, Gamepad2, RefreshCw, ArrowRight } from 'lucide-react';
import { useLeagues, useTeams, usePlayers, useGames, useSyncLogs } from '../hooks/useApi';
import { Card, CardContent, LoadingSpinner, ErrorMessage, Badge } from '../components/ui';

function StatCard({
  icon: Icon,
  label,
  value,
  to,
  loading,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  to: string;
  loading?: boolean;
}) {
  return (
    <Link to={to}>
      <Card className="hover:shadow-md active:bg-gray-50 transition-shadow">
        <CardContent className="flex items-center gap-3 sm:gap-4">
          <div className="p-2 sm:p-3 bg-blue-50 rounded-lg">
            <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs sm:text-sm text-gray-500">{label}</p>
            {loading ? (
              <div className="h-6 sm:h-8 w-16 bg-gray-200 animate-pulse rounded" />
            ) : (
              <p className="text-xl sm:text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
            )}
          </div>
          <ArrowRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
        </CardContent>
      </Card>
    </Link>
  );
}

export default function Dashboard() {
  const { data: leagues, isLoading: leaguesLoading, error: leaguesError } = useLeagues();
  const { data: teams, isLoading: teamsLoading } = useTeams();
  const { data: players, isLoading: playersLoading } = usePlayers();
  const { data: games, isLoading: gamesLoading } = useGames();
  const { data: syncLogs, isLoading: syncLoading } = useSyncLogs({ page_size: 5 });

  if (leaguesError) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <ErrorMessage message={`Failed to load data: ${leaguesError.message}`} />
        <p className="text-gray-500">
          Make sure the API server is running at <code>http://localhost:8000</code>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6 lg:space-y-8">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm sm:text-base text-gray-500 mt-1">Overview of your basketball analytics data</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatCard
          icon={Trophy}
          label="Leagues"
          value={leagues?.total ?? 0}
          to="/leagues"
          loading={leaguesLoading}
        />
        <StatCard
          icon={Users}
          label="Teams"
          value={teams?.total ?? 0}
          to="/teams"
          loading={teamsLoading}
        />
        <StatCard
          icon={UserCircle}
          label="Players"
          value={players?.total ?? 0}
          to="/players"
          loading={playersLoading}
        />
        <StatCard
          icon={Gamepad2}
          label="Games"
          value={games?.total ?? 0}
          to="/games"
          loading={gamesLoading}
        />
      </div>

      {/* Recent Sync Activity */}
      <Card>
        <div className="px-4 py-3 sm:px-6 sm:py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4 sm:w-5 sm:h-5 text-gray-500" />
            <h2 className="text-base sm:text-lg font-semibold text-gray-900">Recent Syncs</h2>
          </div>
          <Link to="/sync" className="text-sm text-blue-600 hover:text-blue-700">
            View all
          </Link>
        </div>
        <CardContent className="p-0">
          {syncLoading ? (
            <LoadingSpinner size="sm" />
          ) : syncLogs?.items.length ? (
            <div className="divide-y divide-gray-200">
              {syncLogs.items.map((log) => (
                <div key={log.id} className="px-4 py-3 sm:px-6 sm:py-4">
                  <div className="flex items-start sm:items-center justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gray-900 text-sm sm:text-base truncate">
                        {log.source.charAt(0).toUpperCase() + log.source.slice(1)} - {log.entity_type}
                      </p>
                      <p className="text-xs sm:text-sm text-gray-500 truncate">
                        {log.season_name && `${log.season_name} • `}
                        {new Date(log.started_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
                      <div className="text-right text-xs sm:text-sm hidden sm:block">
                        <p className="text-gray-900">{log.records_created} new</p>
                      </div>
                      <Badge
                        variant={
                          log.status === 'COMPLETED'
                            ? 'success'
                            : log.status === 'FAILED'
                            ? 'error'
                            : log.status === 'STARTED'
                            ? 'info'
                            : 'warning'
                        }
                      >
                        {log.status}
                      </Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-4 py-6 sm:px-6 sm:py-8 text-center text-gray-500 text-sm sm:text-base">
              No sync activity yet. <Link to="/sync" className="text-blue-600 hover:underline">Start a sync</Link>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <div className="px-4 py-3 sm:px-6 sm:py-4 border-b border-gray-200">
          <h2 className="text-base sm:text-lg font-semibold text-gray-900">Quick Actions</h2>
        </div>
        <CardContent>
          <div className="grid grid-cols-1 sm:flex sm:flex-wrap gap-3 sm:gap-4">
            <Link
              to="/sync"
              className="inline-flex items-center justify-center sm:justify-start gap-2 px-4 py-3 sm:py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-800 transition-colors text-sm sm:text-base"
            >
              <RefreshCw className="w-4 h-4" />
              Start New Sync
            </Link>
            <Link
              to="/games"
              className="inline-flex items-center justify-center sm:justify-start gap-2 px-4 py-3 sm:py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 active:bg-gray-300 transition-colors text-sm sm:text-base"
            >
              <Gamepad2 className="w-4 h-4" />
              View Games
            </Link>
            <Link
              to="/teams"
              className="inline-flex items-center justify-center sm:justify-start gap-2 px-4 py-3 sm:py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 active:bg-gray-300 transition-colors text-sm sm:text-base"
            >
              <Users className="w-4 h-4" />
              Browse Teams
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
