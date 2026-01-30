/**
 * Player Detail Page
 *
 * Shows player information, career stats, and game log.
 */

import { useParams, Link } from 'react-router-dom';
import { UserCircle, MapPin, Calendar, Ruler, ChevronRight } from 'lucide-react';
import { usePlayer, usePlayerStats, usePlayerGames } from '../hooks/useApi';
import {
  Card,
  CardHeader,
  CardContent,
  LoadingSpinner,
  ErrorMessage,
  EmptyState,
  Badge,
  StatCard,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableHeader,
  TableCell,
} from '../components/ui';

export default function PlayerDetail() {
  const { playerId } = useParams<{ playerId: string }>();

  const { data: player, isLoading: playerLoading, error: playerError } = usePlayer(playerId!);
  const { data: stats, isLoading: statsLoading } = usePlayerStats(playerId!);
  const { data: games, isLoading: gamesLoading } = usePlayerGames(playerId!);

  if (playerLoading) return <LoadingSpinner />;
  if (playerError) return <ErrorMessage message={playerError.message} />;
  if (!player) return <ErrorMessage message="Player not found" />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-4 bg-purple-50 rounded-full">
          <UserCircle className="w-12 h-12 text-purple-600" />
        </div>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{player.full_name}</h1>
          <div className="flex flex-wrap items-center gap-4 mt-2 text-gray-500">
            {player.positions?.length > 0 && <Badge variant="info">{player.positions.join('/')}</Badge>}
            {player.nationality && (
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {player.nationality}
              </span>
            )}
            {player.birth_date && (
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {new Date(player.birth_date).toLocaleDateString()}
              </span>
            )}
            {player.height_cm && (
              <span className="flex items-center gap-1">
                <Ruler className="w-4 h-4" />
                {player.height_cm} cm
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Career Stats */}
      {statsLoading ? (
        <LoadingSpinner size="sm" />
      ) : stats ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <StatCard label="Games" value={stats.career_games_played} />
            <StatCard label="PPG" value={stats.career_avg_points.toFixed(1)} />
            <StatCard label="RPG" value={stats.career_avg_rebounds.toFixed(1)} />
            <StatCard label="APG" value={stats.career_avg_assists.toFixed(1)} />
            <StatCard label="Total Points" value={stats.career_points.toLocaleString()} />
            <StatCard label="Total Rebounds" value={stats.career_rebounds.toLocaleString()} />
          </div>

          {/* Season Stats */}
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold text-gray-900">Season Stats</h2>
            </CardHeader>
            <CardContent className="p-0">
              {stats.seasons.length ? (
                <Table>
                  <TableHead>
                    <TableRow hoverable={false}>
                      <TableHeader>Season</TableHeader>
                      <TableHeader>Team</TableHeader>
                      <TableHeader>GP</TableHeader>
                      <TableHeader>PPG</TableHeader>
                      <TableHeader>RPG</TableHeader>
                      <TableHeader>APG</TableHeader>
                      <TableHeader>FG%</TableHeader>
                      <TableHeader>3P%</TableHeader>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {stats.seasons.map((season) => (
                      <TableRow key={season.id}>
                        <TableCell className="font-medium text-gray-900">
                          {season.season_name}
                        </TableCell>
                        <TableCell>
                          <Link
                            to={`/teams/${season.team_id}`}
                            className="text-blue-600 hover:text-blue-700"
                          >
                            {season.team_name}
                          </Link>
                        </TableCell>
                        <TableCell>{season.games_played}</TableCell>
                        <TableCell>{season.avg_points?.toFixed(1) ?? '-'}</TableCell>
                        <TableCell>{season.avg_rebounds?.toFixed(1) ?? '-'}</TableCell>
                        <TableCell>{season.avg_assists?.toFixed(1) ?? '-'}</TableCell>
                        <TableCell>
                          {season.field_goal_pct != null
                            ? `${season.field_goal_pct.toFixed(1)}%`
                            : '-'}
                        </TableCell>
                        <TableCell>
                          {season.three_point_pct != null
                            ? `${season.three_point_pct.toFixed(1)}%`
                            : '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <EmptyState title="No season stats" description="Stats not available" />
              )}
            </CardContent>
          </Card>
        </>
      ) : null}

      {/* Team History */}
      {player.team_history?.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-gray-900">Team History</h2>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-200">
              {player.team_history.map((history, idx) => (
                <Link
                  key={idx}
                  to={`/teams/${history.team_id}`}
                  className="flex items-center justify-between px-6 py-4 hover:bg-gray-50"
                >
                  <div>
                    <p className="font-medium text-gray-900">{history.team_name}</p>
                    <p className="text-sm text-gray-500">
                      {history.season_name}
                      {history.jersey_number && ` • #${history.jersey_number}`}
                      {history.positions?.length > 0 && ` • ${history.positions.join('/')}`}
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Games */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">Recent Games</h2>
        </CardHeader>
        <CardContent className="p-0">
          {gamesLoading ? (
            <LoadingSpinner size="sm" />
          ) : games?.items.length ? (
            <Table>
              <TableHead>
                <TableRow hoverable={false}>
                  <TableHeader>Date</TableHeader>
                  <TableHeader>Opponent</TableHeader>
                  <TableHeader>Result</TableHeader>
                  <TableHeader>MIN</TableHeader>
                  <TableHeader>PTS</TableHeader>
                  <TableHeader>REB</TableHeader>
                  <TableHeader>AST</TableHeader>
                  <TableHeader>FG</TableHeader>
                  <TableHeader>&nbsp;</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {games.items.slice(0, 10).map((game) => {
                  const won = game.team_score > game.opponent_score;
                  return (
                    <TableRow
                      key={game.id}
                      onClick={() => window.location.href = `/games/${game.game_id}`}
                    >
                      <TableCell className="text-gray-500">
                        {new Date(game.game_date).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="font-medium text-gray-900">
                        <Link
                          to={`/teams/${game.opponent_team_id}`}
                          className="hover:text-blue-600"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {game.is_home ? 'vs' : '@'} {game.opponent_team_name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant={won ? 'success' : 'error'}>
                          {won ? 'W' : 'L'} {game.team_score}-{game.opponent_score}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {game.minutes_played != null
                          ? Math.floor(game.minutes_played / 60)
                          : '-'}
                      </TableCell>
                      <TableCell className="font-medium">{game.points}</TableCell>
                      <TableCell>{game.total_rebounds}</TableCell>
                      <TableCell>{game.assists}</TableCell>
                      <TableCell>
                        {game.field_goals_made}/{game.field_goals_attempted}
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
            <EmptyState title="No games" description="Game log not available" />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
