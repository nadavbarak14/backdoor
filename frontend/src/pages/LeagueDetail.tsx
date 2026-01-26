/**
 * League Detail Page
 *
 * Shows league information and its seasons with links to teams.
 */

import { useParams, Link } from 'react-router-dom';
import { Trophy, Calendar, MapPin, Users, ChevronRight } from 'lucide-react';
import { useLeague, useLeagueSeasons } from '../hooks/useApi';
import {
  Card,
  CardHeader,
  CardContent,
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  LinkButton,
} from '../components/ui';

export default function LeagueDetail() {
  const { leagueId } = useParams<{ leagueId: string }>();
  const { data: league, isLoading: leagueLoading, error: leagueError } = useLeague(leagueId!);
  const { data: seasons, isLoading: seasonsLoading } = useLeagueSeasons(leagueId!);

  if (leagueLoading) return <LoadingSpinner />;
  if (leagueError) return <ErrorMessage message={leagueError.message} />;
  if (!league) return <ErrorMessage message="League not found" />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-4 bg-amber-50 rounded-lg">
          <Trophy className="w-8 h-8 text-amber-600" />
        </div>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{league.name}</h1>
          <div className="flex items-center gap-4 mt-2 text-gray-500">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              {league.season_count} seasons
            </span>
            {league.country && (
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {league.country}
              </span>
            )}
            <span className="text-sm">Code: {league.code}</span>
          </div>
        </div>
        <LinkButton to={`/teams?league_id=${league.id}`} variant="secondary">
          <Users className="w-4 h-4" />
          View Teams
        </LinkButton>
      </div>

      {/* Seasons */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">Seasons</h2>
        </CardHeader>
        <CardContent className="p-0">
          {seasonsLoading ? (
            <LoadingSpinner size="sm" />
          ) : seasons?.length ? (
            <div className="divide-y divide-gray-200">
              {seasons.map((season) => (
                <Link
                  key={season.id}
                  to={`/teams?season_id=${season.id}`}
                  className="flex items-center justify-between px-6 py-4 hover:bg-gray-50"
                >
                  <div>
                    <p className="font-medium text-gray-900">{season.name}</p>
                    <p className="text-sm text-gray-500">
                      {new Date(season.start_date).toLocaleDateString()} - {new Date(season.end_date).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-500">
                      View teams
                    </span>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title="No seasons"
              description="No seasons have been synced for this league yet."
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
