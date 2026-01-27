/**
 * Game Detail Page
 *
 * Shows game information and full box score.
 */

import { useParams, Link } from 'react-router-dom';
import { Calendar, MapPin } from 'lucide-react';
import { useGame } from '../hooks/useApi';
import {
  Card,
  CardHeader,
  CardContent,
  LoadingSpinner,
  ErrorMessage,
  Badge,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableHeader,
  TableCell,
} from '../components/ui';
import type { PlayerGameStats } from '../types';

function BoxScoreTable({
  players,
  teamName,
}: {
  players: PlayerGameStats[];
  teamName: string;
}) {
  // Sort: starters first, then by minutes
  const sorted = [...players].sort((a, b) => {
    if (a.is_starter !== b.is_starter) return a.is_starter ? -1 : 1;
    return (b.minutes_played ?? 0) - (a.minutes_played ?? 0);
  });

  return (
    <Card>
      <CardHeader>
        <h3 className="font-semibold text-gray-900">{teamName}</h3>
      </CardHeader>
      <CardContent className="p-0 overflow-x-auto">
        <Table>
          <TableHead>
            <TableRow hoverable={false}>
              <TableHeader>Player</TableHeader>
              <TableHeader className="text-right">MIN</TableHeader>
              <TableHeader className="text-right">PTS</TableHeader>
              <TableHeader className="text-right">REB</TableHeader>
              <TableHeader className="text-right">AST</TableHeader>
              <TableHeader className="text-right">STL</TableHeader>
              <TableHeader className="text-right">BLK</TableHeader>
              <TableHeader className="text-right">TO</TableHeader>
              <TableHeader className="text-right">FG</TableHeader>
              <TableHeader className="text-right">3P</TableHeader>
              <TableHeader className="text-right">FT</TableHeader>
              <TableHeader className="text-right">+/-</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {sorted.map((stat) => (
              <TableRow key={stat.id} hoverable={false}>
                <TableCell>
                  <Link
                    to={`/players/${stat.player_id}`}
                    className="font-medium text-gray-900 hover:text-blue-600"
                  >
                    {stat.player_name}
                  </Link>
                  {stat.is_starter && (
                    <span className="ml-1 text-xs text-gray-400">*</span>
                  )}
                </TableCell>
                <TableCell className="text-right text-gray-500">
                  {stat.minutes_played != null
                    ? Math.floor(stat.minutes_played / 60)
                    : '-'}
                </TableCell>
                <TableCell className="text-right font-medium">
                  {stat.points}
                </TableCell>
                <TableCell className="text-right">{stat.total_rebounds}</TableCell>
                <TableCell className="text-right">{stat.assists}</TableCell>
                <TableCell className="text-right">{stat.steals}</TableCell>
                <TableCell className="text-right">{stat.blocks}</TableCell>
                <TableCell className="text-right">{stat.turnovers}</TableCell>
                <TableCell className="text-right text-gray-500">
                  {stat.field_goals_made}-{stat.field_goals_attempted}
                </TableCell>
                <TableCell className="text-right text-gray-500">
                  {stat.three_pointers_made}-{stat.three_pointers_attempted}
                </TableCell>
                <TableCell className="text-right text-gray-500">
                  {stat.free_throws_made}-{stat.free_throws_attempted}
                </TableCell>
                <TableCell className="text-right">
                  {stat.plus_minus != null ? (
                    <span
                      className={
                        stat.plus_minus > 0
                          ? 'text-green-600'
                          : stat.plus_minus < 0
                          ? 'text-red-600'
                          : ''
                      }
                    >
                      {stat.plus_minus > 0 ? '+' : ''}
                      {stat.plus_minus}
                    </span>
                  ) : (
                    '-'
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <p className="px-6 py-2 text-xs text-gray-400">* Starter</p>
      </CardContent>
    </Card>
  );
}

export default function GameDetail() {
  const { gameId } = useParams<{ gameId: string }>();

  const { data: game, isLoading: gameLoading, error: gameError } = useGame(gameId!);

  // Box score data is included in the game response
  const hasBoxScore = game?.home_players && game.home_players.length > 0;

  if (gameLoading) return <LoadingSpinner />;
  if (gameError) return <ErrorMessage message={gameError.message} />;
  if (!game) return <ErrorMessage message="Game not found" />;

  const homeWon = (game.home_score ?? 0) > (game.away_score ?? 0);

  return (
    <div className="space-y-6">
      {/* Header / Scoreboard */}
      <Card>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {new Date(game.game_date).toLocaleDateString()}
              </span>
              {game.venue && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {game.venue}
                </span>
              )}
            </div>
            <Badge variant={game.status === 'FINAL' ? 'success' : 'default'}>
              {game.status}
            </Badge>
          </div>

          <div className="flex items-center justify-center gap-8">
            {/* Home Team */}
            <div className="flex-1 text-center">
              <Link
                to={`/teams/${game.home_team_id}`}
                className="text-xl font-bold text-gray-900 hover:text-blue-600"
              >
                {game.home_team_name ?? 'Home Team'}
              </Link>
              <p className="text-sm text-gray-500">Home</p>
              <p
                className={`text-5xl font-bold mt-2 ${
                  homeWon ? 'text-green-600' : 'text-gray-500'
                }`}
              >
                {game.home_score ?? '-'}
              </p>
            </div>

            <div className="text-2xl font-bold text-gray-400">vs</div>

            {/* Away Team */}
            <div className="flex-1 text-center">
              <Link
                to={`/teams/${game.away_team_id}`}
                className="text-xl font-bold text-gray-900 hover:text-blue-600"
              >
                {game.away_team_name ?? 'Away Team'}
              </Link>
              <p className="text-sm text-gray-500">Away</p>
              <p
                className={`text-5xl font-bold mt-2 ${
                  !homeWon ? 'text-green-600' : 'text-gray-500'
                }`}
              >
                {game.away_score ?? '-'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Box Score */}
      {hasBoxScore ? (
        <div className="space-y-6">
          <BoxScoreTable
            players={game.home_players!}
            teamName={game.home_team_name ?? 'Home Team'}
          />
          <BoxScoreTable
            players={game.away_players!}
            teamName={game.away_team_name ?? 'Away Team'}
          />
        </div>
      ) : (
        <Card>
          <CardContent className="text-center text-gray-500 py-8">
            Box score not available for this game
          </CardContent>
        </Card>
      )}
    </div>
  );
}
