/**
 * Team List Page
 *
 * Displays all teams with search and filter functionality.
 */

import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Users, Search, MapPin, ChevronRight } from 'lucide-react';
import { useTeams, useLeagues } from '../hooks/useApi';
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

export default function TeamList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [page, setPage] = useState(1);

  const seasonId = searchParams.get('season_id') || undefined;
  const leagueId = searchParams.get('league_id') || undefined;

  const { data: leagues } = useLeagues();
  const { data, isLoading, error } = useTeams(
    { search: search || undefined, season_id: seasonId, league_id: leagueId },
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

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Teams</h1>
        <p className="text-gray-500 mt-1">
          {data?.total ?? 0} teams
          {seasonId && ' in selected season'}
          {leagueId && ' in selected league'}
        </p>
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
                  placeholder="Search teams..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            {leagues?.items && (
              <Select
                value={leagueId || ''}
                onChange={(value) => {
                  if (value) {
                    searchParams.set('league_id', value);
                  } else {
                    searchParams.delete('league_id');
                  }
                  setSearchParams(searchParams);
                  setPage(1);
                }}
                options={leagues.items.map((l) => ({ value: l.id, label: l.name }))}
                placeholder="All leagues"
                className="w-48"
              />
            )}
          </div>
        </CardContent>
      </Card>

      {/* Team List */}
      {isLoading ? (
        <LoadingSpinner />
      ) : error ? (
        <ErrorMessage message={error.message} />
      ) : !data?.items.length ? (
        <EmptyState
          icon={Users}
          title="No teams found"
          description={search ? 'Try a different search term' : 'No teams have been synced yet'}
        />
      ) : (
        <Card>
          <div className="divide-y divide-gray-200">
            {data.items.map((team) => (
              <Link
                key={team.id}
                to={`/teams/${team.id}`}
                className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50"
              >
                <div className="p-2 bg-blue-50 rounded-lg">
                  <Users className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900">{team.name}</p>
                  <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                    {team.city && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {team.city}
                      </span>
                    )}
                    {team.code && <span>Code: {team.code}</span>}
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
