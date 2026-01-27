/**
 * Game Detail Page
 *
 * Shows game information and full box score.
 */

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Calendar, MapPin } from 'lucide-react';
import { useGame, useGamePbp } from '../hooks/useApi';
import type { PlayByPlayEvent } from '../types';
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

const EVENT_TYPE_LABELS: Record<string, string> = {
  shot: 'Shot',
  free_throw: 'Free Throw',
  rebound: 'Rebound',
  assist: 'Assist',
  turnover: 'Turnover',
  steal: 'Steal',
  block: 'Block',
  foul: 'Foul',
  substitution: 'Substitution',
  timeout: 'Timeout',
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  shot: 'bg-blue-100 text-blue-800',
  free_throw: 'bg-purple-100 text-purple-800',
  rebound: 'bg-orange-100 text-orange-800',
  assist: 'bg-green-100 text-green-800',
  turnover: 'bg-red-100 text-red-800',
  steal: 'bg-yellow-100 text-yellow-800',
  block: 'bg-indigo-100 text-indigo-800',
  foul: 'bg-pink-100 text-pink-800',
  substitution: 'bg-gray-100 text-gray-800',
  timeout: 'bg-gray-100 text-gray-800',
};

function PlayByPlayTimeline({
  events,
  periodFilter,
  eventTypeFilter,
  onPeriodChange,
  onEventTypeChange,
}: {
  events: PlayByPlayEvent[];
  periodFilter: number | null;
  eventTypeFilter: string | null;
  onPeriodChange: (p: number | null) => void;
  onEventTypeChange: (e: string | null) => void;
}) {
  const periods = [...new Set(events.map((e) => e.period))].sort();
  const eventTypes = [...new Set(events.map((e) => e.event_type))].sort();

  const filtered = events.filter((e) => {
    if (periodFilter && e.period !== periodFilter) return false;
    if (eventTypeFilter && e.event_type !== eventTypeFilter) return false;
    return true;
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">Play-by-Play</h3>
          <span className="text-sm text-gray-500">{filtered.length} events</span>
        </div>
        <div className="flex gap-2 mt-2 flex-wrap">
          <select
            className="text-sm border rounded px-2 py-1"
            value={periodFilter ?? ''}
            onChange={(e) => onPeriodChange(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">All Quarters</option>
            {periods.map((p) => (
              <option key={p} value={p}>Q{p}</option>
            ))}
          </select>
          <select
            className="text-sm border rounded px-2 py-1"
            value={eventTypeFilter ?? ''}
            onChange={(e) => onEventTypeChange(e.target.value || null)}
          >
            <option value="">All Events</option>
            {eventTypes.map((t) => (
              <option key={t} value={t}>{EVENT_TYPE_LABELS[t] || t}</option>
            ))}
          </select>
        </div>
      </CardHeader>
      <CardContent className="p-0 max-h-96 overflow-y-auto">
        <div className="divide-y">
          {filtered.map((event) => (
            <div key={event.id} className="px-4 py-2 flex items-center gap-3 text-sm">
              <span className="w-12 text-gray-500 font-mono">Q{event.period} {event.clock}</span>
              <Badge className={EVENT_TYPE_COLORS[event.event_type] || 'bg-gray-100'}>
                {event.success === true && '✓ '}
                {event.success === false && '✗ '}
                {EVENT_TYPE_LABELS[event.event_type] || event.event_type}
              </Badge>
              <span className="flex-1">
                {event.player_name && (
                  <Link
                    to={`/players/${event.player_id}`}
                    className="font-medium hover:text-blue-600"
                  >
                    {event.player_name}
                  </Link>
                )}
                {event.event_subtype && (
                  <span className="text-gray-500 ml-1">({event.event_subtype})</span>
                )}
              </span>
              <span className="text-gray-400 text-xs">{event.team_name}</span>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="px-4 py-8 text-center text-gray-500">No events found</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function GameDetail() {
  const { gameId } = useParams<{ gameId: string }>();
  const [periodFilter, setPeriodFilter] = useState<number | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<string | null>(null);

  const { data: game, isLoading: gameLoading, error: gameError } = useGame(gameId!);
  const { data: pbpData } = useGamePbp(gameId!);

  // Box score data is included in the game response
  const hasBoxScore = game?.home_players && game.home_players.length > 0;
  const hasPbp = pbpData?.events && pbpData.events.length > 0;

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

      {/* Play-by-Play */}
      {hasPbp && (
        <PlayByPlayTimeline
          events={pbpData.events}
          periodFilter={periodFilter}
          eventTypeFilter={eventTypeFilter}
          onPeriodChange={setPeriodFilter}
          onEventTypeChange={setEventTypeFilter}
        />
      )}
    </div>
  );
}
