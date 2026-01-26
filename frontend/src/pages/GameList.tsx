/**
 * Game List Page
 *
 * Displays all games with filtering by season and date.
 */

import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Gamepad2, Calendar, ChevronRight } from 'lucide-react';
import { useGames } from '../hooks/useApi';
import {
  Card,
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  Badge,
  Pagination,
} from '../components/ui';

const PAGE_SIZE = 20;

export default function GameList() {
  const [searchParams] = useSearchParams();
  const [page, setPage] = useState(1);

  const seasonId = searchParams.get('season_id') || undefined;
  const teamId = searchParams.get('team_id') || undefined;

  const { data, isLoading, error } = useGames(
    { season_id: seasonId, team_id: teamId, status: 'FINAL' },
    (page - 1) * PAGE_SIZE,
    PAGE_SIZE
  );

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Games</h1>
        <p className="text-sm sm:text-base text-gray-500 mt-1">{data?.total ?? 0} games</p>
      </div>

      {/* Game List */}
      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage message={error.message} />
      ) : !data?.items.length ? (
        <EmptyState
          icon={Gamepad2}
          title="No games found"
          description="No games have been synced yet"
        />
      ) : (
        <Card>
          <div className="divide-y divide-gray-200">
            {data.items.map((game) => {
              const homeWon = (game.home_score ?? 0) > (game.away_score ?? 0);
              return (
                <Link
                  key={game.id}
                  to={`/games/${game.id}`}
                  className="block px-3 py-3 sm:px-6 sm:py-4 hover:bg-gray-50 active:bg-gray-100"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 sm:gap-4 text-xs sm:text-sm text-gray-500">
                      <Calendar className="w-4 h-4 hidden sm:block" />
                      <span>{new Date(game.game_date).toLocaleDateString()}</span>
                    </div>
                    <Badge
                      variant={game.status === 'FINAL' ? 'success' : 'default'}
                    >
                      {game.status}
                    </Badge>
                  </div>

                  <div className="mt-2 sm:mt-3 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      {/* Home Team */}
                      <div className="flex items-center justify-between py-1 sm:py-2">
                        <span
                          className={`text-sm sm:text-base font-medium truncate mr-2 ${
                            homeWon ? 'text-gray-900' : 'text-gray-500'
                          }`}
                        >
                          {game.home_team_name ?? 'Home Team'}
                        </span>
                        <span
                          className={`text-base sm:text-lg font-bold flex-shrink-0 ${
                            homeWon ? 'text-gray-900' : 'text-gray-500'
                          }`}
                        >
                          {game.home_score ?? '-'}
                        </span>
                      </div>

                      {/* Away Team */}
                      <div className="flex items-center justify-between py-1 sm:py-2 border-t border-gray-100">
                        <span
                          className={`text-sm sm:text-base font-medium truncate mr-2 ${
                            !homeWon ? 'text-gray-900' : 'text-gray-500'
                          }`}
                        >
                          {game.away_team_name ?? 'Away Team'}
                        </span>
                        <span
                          className={`text-base sm:text-lg font-bold flex-shrink-0 ${
                            !homeWon ? 'text-gray-900' : 'text-gray-500'
                          }`}
                        >
                          {game.away_score ?? '-'}
                        </span>
                      </div>
                    </div>

                    <ChevronRight className="w-5 h-5 text-gray-400 ml-2 sm:ml-4 flex-shrink-0" />
                  </div>
                </Link>
              );
            })}
          </div>
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </Card>
      )}
    </div>
  );
}
