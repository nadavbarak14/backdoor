/**
 * Team Detail Page
 *
 * Shows team information, roster, and game history.
 */

import { useParams, Link } from 'react-router-dom';
import { Users, MapPin, Calendar, Home, Plane, ChevronRight } from 'lucide-react';
import { useTeam, useTeamRoster, useTeamGames } from '../hooks/useApi';
import {
  Card,
  CardHeader,
  CardContent,
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  Badge,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableHeader,
  TableCell,
} from '../components/ui';

export default function TeamDetail() {
  const { teamId } = useParams<{ teamId: string }>();

  const { data: team, isLoading: teamLoading, error: teamError } = useTeam(teamId!);
  const { data: roster, isLoading: rosterLoading } = useTeamRoster(teamId!);
  const { data: games, isLoading: gamesLoading } = useTeamGames(teamId!);

  if (teamLoading) return <LoadingSpinner />;
  if (teamError) return <ErrorMessage message={teamError.message} />;
  if (!team) return <ErrorMessage message="Team not found" />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-4 bg-blue-50 rounded-lg">
          <Users className="w-8 h-8 text-blue-600" />
        </div>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{team.name}</h1>
          <div className="flex items-center gap-4 mt-2 text-gray-500">
            {team.city && (
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {team.city}
              </span>
            )}
            {team.venue && <span>Venue: {team.venue}</span>}
            {team.code && <span className="text-sm">Code: {team.code}</span>}
          </div>
        </div>
      </div>

      {/* Roster */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-900">Roster</h2>
          </div>
          {roster?.season_name && (
            <Badge variant="info">{roster.season_name}</Badge>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {rosterLoading ? (
            <LoadingSpinner size="sm" />
          ) : roster?.players.length ? (
            <Table>
              <TableHead>
                <TableRow hoverable={false}>
                  <TableHeader>#</TableHeader>
                  <TableHeader>Player</TableHeader>
                  <TableHeader>Position</TableHeader>
                  <TableHeader>&nbsp;</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {roster.players.map((player) => (
                  <TableRow
                    key={player.id}
                    onClick={() => window.location.href = `/players/${player.id}`}
                  >
                    <TableCell className="font-medium text-gray-500">
                      {player.jersey_number || '-'}
                    </TableCell>
                    <TableCell className="font-medium text-gray-900">
                      <Link
                        to={`/players/${player.id}`}
                        className="hover:text-blue-600"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {player.full_name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-gray-500">
                      {player.positions?.join('/') || '-'}
                    </TableCell>
                    <TableCell>
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyState
              title="No roster data"
              description="Roster information is not available for this team"
            />
          )}
        </CardContent>
      </Card>

      {/* Recent Games */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-900">Recent Games</h2>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {gamesLoading ? (
            <LoadingSpinner size="sm" />
          ) : games?.items.length ? (
            <Table>
              <TableHead>
                <TableRow hoverable={false}>
                  <TableHeader>Date</TableHeader>
                  <TableHeader>&nbsp;</TableHeader>
                  <TableHeader>Opponent</TableHeader>
                  <TableHeader>Result</TableHeader>
                  <TableHeader>Score</TableHeader>
                  <TableHeader>&nbsp;</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {games.items
                  .filter((game) => game.team_score != null && game.opponent_score != null)
                  .slice(0, 10)
                  .map((game) => {
                  const won = game.team_score > game.opponent_score;
                  return (
                    <TableRow
                      key={game.game_id}
                      onClick={() => window.location.href = `/games/${game.game_id}`}
                    >
                      <TableCell className="text-gray-500">
                        {new Date(game.game_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {game.is_home ? (
                          <Home className="w-4 h-4 text-gray-400" />
                        ) : (
                          <Plane className="w-4 h-4 text-gray-400" />
                        )}
                      </TableCell>
                      <TableCell className="font-medium text-gray-900">
                        <Link
                          to={`/teams/${game.opponent_team_id}`}
                          className="hover:text-blue-600"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {game.opponent_team_name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant={won ? 'success' : 'error'}>
                          {won ? 'W' : 'L'}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">
                        {game.team_score} - {game.opponent_score}
                      </TableCell>
                      <TableCell>
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <EmptyState
              title="No games"
              description="No game data available for this team"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
