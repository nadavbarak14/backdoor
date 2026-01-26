/**
 * League List Page
 *
 * Displays all leagues with their season counts.
 */

import { Link } from 'react-router-dom';
import { Trophy, Calendar, MapPin, ChevronRight } from 'lucide-react';
import { useLeagues } from '../hooks/useApi';
import { Card, CardContent, LoadingSpinner, ErrorMessage, EmptyState } from '../components/ui';

export default function LeagueList() {
  const { data, isLoading, error } = useLeagues();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error.message} />;
  if (!data?.items.length) {
    return (
      <EmptyState
        icon={Trophy}
        title="No leagues found"
        description="No leagues have been synced yet. Start a sync to import league data."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Leagues</h1>
        <p className="text-gray-500 mt-1">{data.total} leagues available</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.items.map((league) => (
          <Link key={league.id} to={`/leagues/${league.id}`}>
            <Card className="hover:shadow-md transition-shadow h-full">
              <CardContent className="flex items-start gap-4">
                <div className="p-3 bg-amber-50 rounded-lg">
                  <Trophy className="w-6 h-6 text-amber-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">{league.name}</h3>
                  <div className="mt-2 space-y-1">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Calendar className="w-4 h-4" />
                      <span>{league.season_count} seasons</span>
                    </div>
                    {league.country && (
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <MapPin className="w-4 h-4" />
                        <span>{league.country}</span>
                      </div>
                    )}
                  </div>
                  <p className="mt-2 text-xs text-gray-400">Code: {league.code}</p>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
