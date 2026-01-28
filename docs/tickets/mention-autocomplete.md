# Ticket: @-Mention Autocomplete with Hierarchical Browser

## Overview

Implement an @-mention system in the chat UI that allows users to reference entities (players, teams, seasons, leagues) with a dual-mode interface:
1. **Hierarchical browser** - Navigate: League → Season → Team → Player
2. **Fast autocomplete search** - Type to search across all entities

The mention is displayed with the entity name but sent to the AI as `@type:uuid` only.

## User Experience

### Triggering the Mention Picker
1. User types `@` in the chat input
2. A dropdown/modal opens with two modes:
   - **Browse mode** (default): Hierarchical folder-style navigation
   - **Search mode**: Activated when user continues typing after `@`

### Browse Mode (Hierarchical Navigation)
```
@
├── 🏆 Leagues
│   └── Israeli Basketball League
│       └── 📅 Seasons
│           └── 2024-25
│               └── 🏀 Teams
│                   └── Maccabi Tel Aviv
│                       └── 👤 Players
│                           ├── Jaylen Hoard
│                           └── ...
```

- Click to expand/navigate levels
- Breadcrumb navigation to go back
- Each level shows relevant entities

### Search Mode (Autocomplete)
When user types after `@`:
```
@mac
─────────────────────────
👤 Mac McClung          (Player · Maccabi Tel Aviv)
🏀 Maccabi Tel Aviv     (Team · Israeli League)
🏀 Maccabi Haifa        (Team · Israeli League)
🏆 Macedonian League    (League)
─────────────────────────
```

**Search behavior:**
- Searches across ALL entity types simultaneously
- Matches first name, last name, team name, league name, season name
- Results grouped/labeled by type
- Limit: 10 results max
- Debounce: 150ms after keystroke

### Selection & Display
1. User selects "Stephen Curry" from dropdown
2. Input displays: `How is @Stephen Curry doing?`
3. Mention is styled (highlighted, maybe with small icon)
4. On send, message becomes: `How is @player:abc-123-uuid doing?`

## Technical Design

### Backend

#### New Autocomplete Endpoint
```
GET /api/v1/search/autocomplete?q={query}&limit={limit}
```

**Response:**
```json
{
  "results": [
    {
      "id": "uuid-123",
      "type": "player",
      "name": "Mac McClung",
      "context": "Maccabi Tel Aviv",
      "icon": "player"
    },
    {
      "id": "uuid-456",
      "type": "team",
      "name": "Maccabi Tel Aviv",
      "context": "Israeli Basketball League",
      "icon": "team"
    }
  ]
}
```

#### Hierarchical Browser Endpoints
```
GET /api/v1/browse/leagues
GET /api/v1/browse/leagues/{league_id}/seasons
GET /api/v1/browse/seasons/{season_id}/teams
GET /api/v1/browse/teams/{team_id}/players
```

Each returns:
```json
{
  "items": [
    { "id": "uuid", "name": "Entity Name", "type": "league|season|team|player" }
  ],
  "parent": { "id": "uuid", "name": "Parent Name", "type": "..." } // for breadcrumb
}
```

#### Search Optimization

**Option A: Indexed LIKE queries (Start here)**
- Add indexes on name columns
- Use `LIKE 'query%'` for prefix matching
- Use `LIKE '%query%'` for contains matching
- Combine with UNION across tables
- Good for <100k total entities

```sql
-- Example unified search query
SELECT id, 'player' as type, first_name || ' ' || last_name as name,
       (SELECT name FROM team WHERE id = player.current_team_id) as context
FROM player
WHERE first_name LIKE :query || '%'
   OR last_name LIKE :query || '%'
   OR first_name || ' ' || last_name LIKE '%' || :query || '%'
UNION ALL
SELECT id, 'team' as type, name,
       (SELECT name FROM league WHERE id = team.league_id) as context
FROM team
WHERE name LIKE '%' || :query || '%'
-- ... etc for league, season
LIMIT 10
```

**Option B: FTS5 Virtual Table (If needed for scale)**
- Create FTS5 virtual table spanning all searchable entities
- Requires migration
- Best for >100k entities or complex fuzzy matching

### Frontend

#### New Components

**1. MentionPicker.tsx**
```typescript
interface MentionPickerProps {
  isOpen: boolean;
  searchQuery: string;
  onSelect: (entity: MentionEntity) => void;
  onClose: () => void;
  position: { top: number; left: number };
}

interface MentionEntity {
  id: string;
  type: 'player' | 'team' | 'season' | 'league';
  name: string;
  context?: string;
}
```

**2. MentionInput.tsx** (wraps ChatInput)
- Detects `@` trigger
- Manages mention picker state
- Tracks cursor position for dropdown placement
- Handles mention insertion and display
- Converts display text to `@type:id` format on submit

**3. BrowsePanel.tsx**
- Hierarchical navigation UI
- Breadcrumb component
- Expandable list items

**4. SearchResults.tsx**
- Autocomplete results list
- Keyboard navigation (up/down arrows, enter to select)
- Type icons/badges

#### Mention Display in Input
- Mentions styled with background highlight and entity-type color
- Non-editable inline spans (clicking selects whole mention)
- Backspace on mention deletes entire mention

#### State Management
```typescript
interface Mention {
  id: string;
  type: 'player' | 'team' | 'season' | 'league';
  displayName: string;
  startIndex: number;
  endIndex: number;
}

// In ChatInput state:
const [mentions, setMentions] = useState<Mention[]>([]);
const [showPicker, setShowPicker] = useState(false);
const [pickerMode, setPickerMode] = useState<'browse' | 'search'>('browse');
```

#### Message Transformation
```typescript
function transformMessageForSend(content: string, mentions: Mention[]): string {
  // Replace each @DisplayName with @type:id
  // Process in reverse order to preserve indices
  let result = content;
  const sortedMentions = [...mentions].sort((a, b) => b.startIndex - a.startIndex);

  for (const mention of sortedMentions) {
    const displayText = content.slice(mention.startIndex, mention.endIndex);
    result = result.slice(0, mention.startIndex) +
             `@${mention.type}:${mention.id}` +
             result.slice(mention.endIndex);
  }
  return result;
}
```

### Schema Updates

#### ChatMessage Schema (Backend)
No changes needed - content is just a string with `@type:id` inline.

#### Frontend Types
```typescript
// lib/chat/types.ts
export interface MentionEntity {
  id: string;
  type: 'player' | 'team' | 'season' | 'league';
  name: string;
  context?: string;
}

export interface AutocompleteResponse {
  results: MentionEntity[];
}

export interface BrowseResponse {
  items: MentionEntity[];
  parent?: MentionEntity;
}
```

## File Changes

### Backend (New Files)
- `src/api/v1/search.py` - Autocomplete endpoint
- `src/api/v1/browse.py` - Hierarchical browse endpoints
- `src/schemas/search.py` - Search/browse schemas
- `src/services/search_service.py` - Search logic with optimization

### Backend (Modified Files)
- `src/api/v1/__init__.py` - Register new routers
- `src/models/player.py` - Add index on name fields (if not present)
- `src/models/team.py` - Add index on name field
- `src/models/league.py` - Add index on name field
- `src/models/season.py` - Add index on name field

### Frontend (New Files)
- `agent-chat/components/chat/MentionPicker.tsx` - Main picker component
- `agent-chat/components/chat/MentionInput.tsx` - Enhanced input wrapper
- `agent-chat/components/chat/BrowsePanel.tsx` - Hierarchical browser
- `agent-chat/components/chat/SearchResults.tsx` - Autocomplete results
- `agent-chat/components/chat/MentionTag.tsx` - Styled mention display
- `agent-chat/lib/chat/mention-utils.ts` - Transform utilities
- `agent-chat/hooks/useAutocomplete.ts` - Search hook with debounce
- `agent-chat/hooks/useBrowse.ts` - Browse navigation hook

### Frontend (Modified Files)
- `agent-chat/components/chat/ChatInput.tsx` - Integrate MentionInput
- `agent-chat/lib/chat/types.ts` - Add mention types
- `agent-chat/app/page.tsx` - Handle mention state

## Testing Requirements

### Backend Tests

#### Unit Tests (`tests/unit/api/test_search.py`)
```python
class TestAutocomplete:
    def test_search_player_by_first_name(self):
        """Search 'step' returns Stephen Curry."""

    def test_search_player_by_last_name(self):
        """Search 'curry' returns Stephen Curry."""

    def test_search_player_full_name(self):
        """Search 'stephen curry' returns exact match first."""

    def test_search_team_partial(self):
        """Search 'macc' returns Maccabi teams."""

    def test_search_mixed_results(self):
        """Search 'mac' returns players AND teams."""

    def test_search_limit_respected(self):
        """Results limited to requested count."""

    def test_search_empty_query(self):
        """Empty query returns empty results."""

    def test_search_no_matches(self):
        """No matches returns empty results."""

    def test_search_case_insensitive(self):
        """Search is case-insensitive."""

    def test_search_special_characters(self):
        """Handles special characters safely (SQL injection prevention)."""

    def test_search_unicode_names(self):
        """Handles unicode/accented characters."""
```

#### Unit Tests (`tests/unit/api/test_browse.py`)
```python
class TestBrowse:
    def test_get_leagues(self):
        """Returns all leagues."""

    def test_get_seasons_for_league(self):
        """Returns seasons for specific league."""

    def test_get_teams_for_season(self):
        """Returns teams for specific season."""

    def test_get_players_for_team(self):
        """Returns players for specific team."""

    def test_browse_invalid_league_id(self):
        """Returns 404 for invalid league."""

    def test_browse_invalid_season_id(self):
        """Returns 404 for invalid season."""

    def test_browse_includes_parent_breadcrumb(self):
        """Response includes parent entity for breadcrumb."""
```

#### Performance Tests (`tests/performance/test_search_performance.py`)
```python
class TestSearchPerformance:
    def test_search_response_time_under_100ms(self):
        """Autocomplete responds in <100ms with 10k players."""

    def test_search_with_many_results(self):
        """Search performs well when many matches exist."""

    def test_concurrent_search_requests(self):
        """Handles multiple concurrent searches."""
```

### Frontend Tests

#### Component Tests (`agent-chat/__tests__/MentionPicker.test.tsx`)
```typescript
describe('MentionPicker', () => {
  it('opens when @ is typed');
  it('shows browse mode by default');
  it('switches to search mode when typing continues');
  it('closes on escape key');
  it('closes on click outside');
  it('navigates with arrow keys');
  it('selects on enter key');
  it('shows loading state during search');
  it('shows empty state when no results');
});

describe('BrowsePanel', () => {
  it('shows leagues at root level');
  it('expands to show seasons on click');
  it('shows breadcrumb navigation');
  it('navigates back with breadcrumb click');
});

describe('SearchResults', () => {
  it('displays results grouped by type');
  it('shows context info for each result');
  it('highlights matching text');
  it('handles keyboard navigation');
});
```

#### Integration Tests (`agent-chat/__tests__/MentionInput.test.tsx`)
```typescript
describe('MentionInput', () => {
  it('inserts mention at cursor position');
  it('displays mention with highlight styling');
  it('deletes entire mention on backspace');
  it('allows multiple mentions in one message');
  it('transforms message correctly on submit');
  it('preserves mention positions during editing');
});

describe('Message Transformation', () => {
  it('replaces @Name with @type:id');
  it('handles multiple mentions');
  it('preserves non-mention text');
  it('handles mentions at start/middle/end');
  it('handles adjacent mentions');
});
```

#### E2E Tests (`agent-chat/__tests__/e2e/mention.spec.ts`)
```typescript
describe('Mention Flow E2E', () => {
  it('complete flow: type @, search, select, send');
  it('browse flow: navigate hierarchy, select player');
  it('message sent contains @type:id format');
  it('AI response acknowledges mentioned entity');
});
```

## Implementation Order

### Phase 1: Backend Foundation
1. Create search schemas
2. Implement autocomplete endpoint with basic LIKE search
3. Add database indexes on name columns
4. Implement browse endpoints
5. Write backend tests

### Phase 2: Frontend Core
1. Create MentionPicker component structure
2. Implement SearchResults with API integration
3. Implement BrowsePanel with navigation
4. Create useAutocomplete and useBrowse hooks
5. Write component tests

### Phase 3: Input Integration
1. Create MentionInput wrapper
2. Implement mention insertion and display
3. Implement message transformation on submit
4. Integrate with existing ChatInput
5. Write integration tests

### Phase 4: Polish & Performance
1. Add keyboard navigation
2. Style mention tags
3. Optimize search if needed (FTS5)
4. E2E tests
5. Performance testing

## Acceptance Criteria

- [ ] Typing `@` opens the mention picker
- [ ] Browse mode shows League → Season → Team → Player hierarchy
- [ ] Typing after `@` searches across all entity types
- [ ] Search returns results in <100ms
- [ ] Selected mention displays with styling in input
- [ ] Sent message contains `@type:id` format (not display name)
- [ ] Multiple mentions work in single message
- [ ] Keyboard navigation works (arrows, enter, escape)
- [ ] All tests pass
- [ ] Works with existing chat flow and AI tools

## Notes

- Start with LIKE-based search, optimize to FTS5 only if performance requires
- Consider caching popular/recent entities for faster access
- Mobile UX may need separate consideration (touch-friendly picker)
