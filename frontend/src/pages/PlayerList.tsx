/**
 * Player List Page
 *
 * Displays all players with search and filter functionality.
 */

import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { UserCircle, Search, MapPin, ChevronRight } from 'lucide-react';
import { usePlayers } from '../hooks/useApi';
import {
  Card,
  CardContent,
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  Select,
  Pagination,
} from '../components/ui';

const PAGE_SIZE = 20;

const POSITIONS = [
  { value: 'PG', label: 'Point Guard' },
  { value: 'SG', label: 'Shooting Guard' },
  { value: 'SF', label: 'Small Forward' },
  { value: 'PF', label: 'Power Forward' },
  { value: 'C', label: 'Center' },
];

export default function PlayerList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [page, setPage] = useState(1);

  const teamId = searchParams.get('team_id') || undefined;
  const position = searchParams.get('position') || undefined;

  const { data, isLoading, error } = usePlayers(
    { search: search || undefined, team_id: teamId, position },
    (page - 1) * PAGE_SIZE,
    PAGE_SIZE
  );

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
    if (value) {
      searchParams.set('search', value);
    } else {
      searchParams.delete('search');
    }
    setSearchParams(searchParams);
  };

  const handlePositionChange = (value: string) => {
    if (value) {
      searchParams.set('position', value);
    } else {
      searchParams.delete('position');
    }
    setSearchParams(searchParams);
    setPage(1);
  };

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Players</h1>
        <p className="text-gray-500 mt-1">{data?.total ?? 0} players</p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search players..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <Select
              value={position || ''}
              onChange={handlePositionChange}
              options={POSITIONS}
              placeholder="All positions"
              className="w-48"
            />
          </div>
        </CardContent>
      </Card>

      {/* Player List */}
      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage message={error.message} />
      ) : !data?.items.length ? (
        <EmptyState
          icon={UserCircle}
          title="No players found"
          description={search ? 'Try a different search term' : 'No players have been synced yet'}
        />
      ) : (
        <Card>
          <div className="divide-y divide-gray-200">
            {data.items.map((player) => (
              <Link
                key={player.id}
                to={`/players/${player.id}`}
                className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50"
              >
                <div className="p-2 bg-purple-50 rounded-full">
                  <UserCircle className="w-6 h-6 text-purple-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900">{player.full_name}</p>
                  <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                    {player.positions?.length > 0 && <span>{player.positions.join('/')}</span>}
                    {player.nationality && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {player.nationality}
                      </span>
                    )}
                    {player.height_cm && <span>{player.height_cm} cm</span>}
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </Link>
            ))}
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
