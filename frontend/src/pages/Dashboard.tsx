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
      <Card className="hover:shadow-md transition-shadow">
        <CardContent className="flex items-center gap-4">
          <div className="p-3 bg-blue-50 rounded-lg">
            <Icon className="w-6 h-6 text-blue-600" />
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-500">{label}</p>
            {loading ? (
              <div className="h-8 w-16 bg-gray-200 animate-pulse rounded" />
            ) : (
              <p className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
            )}
          </div>
          <ArrowRight className="w-5 h-5 text-gray-400" />
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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Overview of your basketball analytics data</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-900">Recent Sync Activity</h2>
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
                <div key={log.id} className="px-6 py-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">
                      {log.source.charAt(0).toUpperCase() + log.source.slice(1)} - {log.entity_type}
                    </p>
                    <p className="text-sm text-gray-500">
                      {log.season_name && `Season: ${log.season_name} • `}
                      {new Date(log.started_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right text-sm">
                      <p className="text-gray-900">{log.records_created} created</p>
                      <p className="text-gray-500">{log.records_skipped} skipped</p>
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
              ))}
            </div>
          ) : (
            <div className="px-6 py-8 text-center text-gray-500">
              No sync activity yet. <Link to="/sync" className="text-blue-600 hover:underline">Start a sync</Link>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
        </div>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <Link
              to="/sync"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Start New Sync
            </Link>
            <Link
              to="/players"
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              <UserCircle className="w-4 h-4" />
              Browse Players
            </Link>
            <Link
              to="/games"
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              <Gamepad2 className="w-4 h-4" />
              View Games
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
