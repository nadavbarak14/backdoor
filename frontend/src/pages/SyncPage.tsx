/**
 * Sync Page
 *
 * Allows triggering syncs with real-time progress via SSE.
 * Shows sync history and status.
 */

import { useState, useCallback } from 'react';
import { RefreshCw, Play, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useSyncStatus, useSyncLogs } from '../hooks/useApi';
import { streamSync } from '../api/client';
import {
  Card,
  CardHeader,
  CardContent,
  LoadingSpinner,
  ErrorMessage,
  Button,
  Input,
  Select,
  Badge,
  ProgressBar,
} from '../components/ui';

const SOURCES = [
  { value: 'winner', label: 'Winner League' },
  { value: 'euroleague', label: 'Euroleague' },
  { value: 'nba', label: 'NBA' },
];

interface SyncProgress {
  isRunning: boolean;
  phase: string;
  current: number;
  total: number;
  skipped: number;
  synced: number;
  errors: number;
  currentGame: string;
  logs: string[];
  completed: boolean;
  error: string | null;
}

const initialProgress: SyncProgress = {
  isRunning: false,
  phase: '',
  current: 0,
  total: 0,
  skipped: 0,
  synced: 0,
  errors: 0,
  currentGame: '',
  logs: [],
  completed: false,
  error: null,
};

export default function SyncPage() {
  const [source, setSource] = useState('winner');
  const [seasonId, setSeasonId] = useState('2024-25');
  const [includePbp, setIncludePbp] = useState(false);
  const [progress, setProgress] = useState<SyncProgress>(initialProgress);

  const { data: syncStatus, isLoading: statusLoading, error: statusError } = useSyncStatus();
  const { data: syncLogs, isLoading: logsLoading, refetch: refetchLogs } = useSyncLogs({
    page_size: 10,
  });

  const startSync = useCallback(async () => {
    setProgress({ ...initialProgress, isRunning: true, phase: 'Starting...' });

    try {
      for await (const { event, data } of streamSync(source, seasonId, includePbp)) {
        const eventData = data as Record<string, unknown>;

        switch (event) {
          case 'start':
            setProgress((p) => ({
              ...p,
              phase: 'Syncing games',
              total: (eventData.total as number) || 0,
              skipped: (eventData.skipped as number) || 0,
              logs: [
                ...p.logs,
                `Starting sync: ${eventData.total} games to sync, ${eventData.skipped} already synced`,
              ].slice(-50),
            }));
            break;

          case 'progress':
            setProgress((p) => ({
              ...p,
              current: (eventData.current as number) || 0,
              currentGame: (eventData.game_id as string) || '',
            }));
            break;

          case 'synced':
            setProgress((p) => ({
              ...p,
              synced: p.synced + 1,
              logs: [
                ...p.logs,
                `Synced: ${eventData.game_id}`,
              ].slice(-50),
            }));
            break;

          case 'error':
            setProgress((p) => ({
              ...p,
              errors: p.errors + 1,
              logs: [
                ...p.logs,
                `Error (${eventData.game_id}): ${eventData.error}`,
              ].slice(-50),
            }));
            break;

          case 'complete':
            const syncLog = eventData.sync_log as Record<string, unknown>;
            setProgress((p) => ({
              ...p,
              isRunning: false,
              completed: true,
              phase: 'Complete',
              logs: [
                ...p.logs,
                `Sync completed: ${syncLog?.records_created ?? 0} created, ${syncLog?.records_skipped ?? 0} skipped`,
              ].slice(-50),
            }));
            refetchLogs();
            break;
        }
      }
    } catch (err) {
      setProgress((p) => ({
        ...p,
        isRunning: false,
        error: err instanceof Error ? err.message : 'Sync failed',
      }));
    }
  }, [source, seasonId, includePbp, refetchLogs]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Sync</h1>
        <p className="text-gray-500 mt-1">
          Synchronize data from external sources with real-time progress
        </p>
      </div>

      {/* API Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-900">API Status</h2>
          </div>
        </CardHeader>
        <CardContent>
          {statusLoading ? (
            <LoadingSpinner size="sm" />
          ) : statusError ? (
            <ErrorMessage message="Cannot connect to API server. Make sure it's running at http://localhost:8000" />
          ) : syncStatus ? (
            <div className="flex flex-wrap gap-4">
              {syncStatus.sources.map((src) => (
                <div
                  key={src.name}
                  className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg"
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      src.enabled ? 'bg-green-500' : 'bg-gray-400'
                    }`}
                  />
                  <span className="font-medium">
                    {src.name.charAt(0).toUpperCase() + src.name.slice(1)}
                  </span>
                  <span className="text-sm text-gray-500">
                    {src.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Sync Form */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold text-gray-900">Start New Sync</h2>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <Select
              label="Data Source"
              value={source}
              onChange={setSource}
              options={SOURCES}
            />
            <Input
              label="Season ID"
              value={seasonId}
              onChange={setSeasonId}
              placeholder="e.g., 2024-25"
            />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Options
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includePbp}
                  onChange={(e) => setIncludePbp(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">
                  Include play-by-play data (slower)
                </span>
              </label>
            </div>
          </div>

          <Button
            onClick={startSync}
            disabled={progress.isRunning || !seasonId}
            loading={progress.isRunning}
            className="w-full md:w-auto"
          >
            <Play className="w-4 h-4" />
            Start Sync
          </Button>
        </CardContent>
      </Card>

      {/* Progress */}
      {(progress.isRunning || progress.completed || progress.error) && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                Sync Progress
              </h2>
              {progress.completed && (
                <Badge variant="success">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Completed
                </Badge>
              )}
              {progress.error && (
                <Badge variant="error">
                  <XCircle className="w-3 h-3 mr-1" />
                  Failed
                </Badge>
              )}
              {progress.isRunning && (
                <Badge variant="info">
                  <Clock className="w-3 h-3 mr-1 animate-spin" />
                  Running
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {progress.error ? (
              <ErrorMessage message={progress.error} />
            ) : (
              <div className="space-y-4">
                {/* Progress bar */}
                <ProgressBar
                  value={progress.current}
                  max={progress.total || 1}
                  label={
                    progress.total > 0
                      ? `${progress.current} / ${progress.total} games`
                      : progress.phase
                  }
                />

                {/* Stats */}
                <div className="grid grid-cols-4 gap-4 text-center">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-2xl font-bold text-gray-900">
                      {progress.total}
                    </p>
                    <p className="text-sm text-gray-500">Total</p>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg">
                    <p className="text-2xl font-bold text-green-600">
                      {progress.synced}
                    </p>
                    <p className="text-sm text-gray-500">Synced</p>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <p className="text-2xl font-bold text-blue-600">
                      {progress.skipped}
                    </p>
                    <p className="text-sm text-gray-500">Already Synced</p>
                  </div>
                  <div className="p-3 bg-red-50 rounded-lg">
                    <p className="text-2xl font-bold text-red-600">
                      {progress.errors}
                    </p>
                    <p className="text-sm text-gray-500">Errors</p>
                  </div>
                </div>

                {/* Log output */}
                <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
                  <pre className="text-sm text-gray-300 font-mono">
                    {progress.logs.length > 0
                      ? progress.logs.slice(-20).join('\n')
                      : 'Waiting for events...'}
                  </pre>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Sync History */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Sync History</h2>
          <Button
            variant="secondary"
            onClick={() => refetchLogs()}
            disabled={logsLoading}
          >
            <RefreshCw className={`w-4 h-4 ${logsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent className="p-0">
          {logsLoading ? (
            <LoadingSpinner size="sm" />
          ) : syncLogs?.items.length ? (
            <div className="divide-y divide-gray-200">
              {syncLogs.items.map((log) => (
                <div
                  key={log.id}
                  className="px-6 py-4 flex items-center justify-between"
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      {log.source.charAt(0).toUpperCase() + log.source.slice(1)} -{' '}
                      {log.entity_type}
                    </p>
                    <p className="text-sm text-gray-500">
                      {log.season_name && `Season: ${log.season_name} • `}
                      {new Date(log.started_at).toLocaleString()}
                      {log.completed_at &&
                        ` • ${Math.round(
                          (new Date(log.completed_at).getTime() -
                            new Date(log.started_at).getTime()) /
                            1000
                        )}s`}
                    </p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right text-sm">
                      <p className="text-green-600">{log.records_created} created</p>
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
              No sync history yet
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
