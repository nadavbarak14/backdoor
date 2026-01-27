/**
 * Chat Constants
 *
 * Static data and configuration for the chat interface including
 * quick prompts and other constant values.
 *
 * @module lib/chat/constants
 */

import { TrendingUp, Users, Activity, Zap } from "lucide-react";
import type { QuickPrompt } from "./types";

/**
 * Quick prompt suggestions displayed on the welcome screen.
 * These provide one-click access to common basketball analytics queries.
 */
export const quickPrompts: QuickPrompt[] = [
  {
    icon: TrendingUp,
    label: "Top Scorers",
    prompt: "Who are the top scorers this season?",
  },
  {
    icon: Users,
    label: "Team Stats",
    prompt: "Show me team comparison stats",
  },
  {
    icon: Activity,
    label: "Live Games",
    prompt: "What games are happening today?",
  },
  {
    icon: Zap,
    label: "Hot Streaks",
    prompt: "Which players are on hot streaks?",
  },
];

/**
 * Default placeholder text for the chat input.
 */
export const INPUT_PLACEHOLDER = "Ask about players, teams, stats...";

/**
 * Simulated AI response message (temporary until API integration).
 */
export const SIMULATED_AI_RESPONSE =
  "I'm ready to analyze basketball data for you. This feature will be fully connected in the next update.";

/**
 * Backend API URL for chat streaming endpoint.
 * Defaults to localhost:8000 for local development.
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
