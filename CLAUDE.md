# DealRadar Project Context

## Project Overview

DealRadar is a Blocket.se scraper with PostgreSQL tracking and n8n AI evaluation integration. The system prevents duplicate processing of listings and enables automated deal hunting with AI-powered value scoring (1-10 scale).

## Architecture

**n8n-Centric Design** (See [DECISIONS.md](DECISIONS.md) for rationale)

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   n8n       │────▶│  Flask API   │────▶│  Blocket   │
│  Workflows  │     │  (scraper)   │     │    API     │
└─────────────┘     └──────────────┘     └────────────┘
      │
      ▼
┌─────────────┐
│ PostgreSQL  │
│  (direct)   │
└─────────────┘
```

### Components

1. **Flask API** (`src/dealradar/web/`, `web_server.py`)
   - **Purpose:** Scrapes Blocket.se and returns JSON data
   - Uses direct HTTP API calls to Blocket (no browser needed)
   - Fetches listings by category or individual ad ID
   - Fast batch processing with async/await
   - **No database writes** (except basic post storage)

2. **n8n Workflows** (See [N8N_WORKFLOWS.md](N8N_WORKFLOWS.md))
   - **Workflow 1:** Scraper - Calls Flask API, stores posts in PostgreSQL (every 30-60 min)
   - **Workflow 2:** Evaluator - Queries unevaluated posts, AI evaluation, stores results (every 15 min)
   - **Workflow 3:** Notifier - Queries high-value deals, sends alerts, marks as notified (every 10 min)
   - Direct PostgreSQL connections (no API middleware)
   - Built-in scheduling, error handling, and retries

3. **PostgreSQL Database** (`schema.sql`)
   - PostgreSQL 18 (Bitnami image) - matches production
   - Three main tables: posts, evaluations, notifications
   - Three views: unevaluated_posts, high_value_deals, pending_notifications
   - Single source of truth for all state

4. **PostTracker** (`src/dealradar/database/tracker.py`)
   - Lightweight Python database interface
   - Used by CLI for monitoring and stats
   - **Simplified:** No evaluation/notification methods (n8n handles these)

5. **CLI Tool** (`src/dealradar/cli/`, `cli.py`)
   - Command-line interface for manual scraping and monitoring
   - Supports single listing, category search, stats, and deals
   - Optional tool for development/debugging

### File Structure

```
dealradar/
├── src/
│   └── dealradar/
│       ├── __init__.py
│       ├── api/                    # Blocket API interaction
│       │   ├── __init__.py
│       │   ├── client.py          # HTTP client & authentication
│       │   └── scraper.py         # Scraping functions
│       ├── database/               # Database layer
│       │   ├── __init__.py
│       │   ├── models.py          # Data models/types
│       │   └── tracker.py         # PostTracker class
│       ├── config/                 # Configuration
│       │   ├── __init__.py
│       │   └── settings.py        # Environment variables & constants
│       ├── cli/                    # CLI interface
│       │   ├── __init__.py
│       │   ├── commands.py        # Command handlers
│       │   └── main.py            # CLI entry point
│       └── web/                    # Web API (Flask)
│           ├── __init__.py
│           ├── app.py             # Flask app factory
│           └── routes.py          # API endpoints
├── tests/                          # Test suite
├── scripts/                        # Utility scripts
├── cli.py                          # CLI entry point
├── web_server.py                   # Web server entry point
├── schema.sql                      # Database schema
├── docker-compose.yml              # PostgreSQL 18 setup
├── requirements.txt                # Python dependencies
├── N8N_WORKFLOWS.md                # n8n workflow guide (detailed)
├── DECISIONS.md                    # Architecture decisions log
├── .env.example                    # Environment template
└── CLAUDE.md                       # This file
```

## Database Schema

### Tables

- **posts**: All discovered Blocket listings
  - Stores: ad_id, title, price, description, seller, location, images, etc.
  - Auto-populated by scraper

- **evaluations**: AI evaluation results
  - Links to posts via ad_id
  - Tracks: status (pending/completed/error), value_score (1-10), evaluation_notes
  - Prevents duplicate evaluations with UNIQUE constraint

- **notifications**: Notification tracking
  - Records which high-value deals have been notified about
  - Prevents duplicate notifications

### Views

- `unevaluated_posts`: Posts needing evaluation
- `high_value_deals`: Posts with score >= 8
- `pending_notifications`: High-value deals not yet notified

## Workflow (Automated via n8n)

### 1. Scraping Phase (n8n Workflow 1 - Every 30-60 min)

1. n8n calls Flask API: `GET /api/search?category=5021&limit=20`
2. Flask API fetches listings from Blocket
3. n8n stores posts directly in PostgreSQL
4. Duplicate posts handled via `ON CONFLICT` (ad_id primary key)

### 2. Evaluation Phase (n8n Workflow 2 - Every 15 min)

1. n8n queries PostgreSQL: `SELECT * FROM unevaluated_posts LIMIT 10`
2. For each post, n8n sends to AI (OpenAI/Claude)
3. AI returns score (1-10) and reasoning
4. n8n saves to evaluations table: `INSERT INTO evaluations ...`

### 3. Notification Phase (n8n Workflow 3 - Every 10 min)

1. n8n queries PostgreSQL: `SELECT * FROM pending_notifications`
2. For each high-value deal (score >= 8):
   - Send notification (Email/Slack/Telegram)
   - Mark as notified: `INSERT INTO notifications ...`

**Manual Scraping (Optional):**
```bash
python cli.py --search 5021 --limit 20  # For testing/development
```

## Key Features

### Duplicate Prevention

The scraper automatically filters out already-evaluated posts:

```python
# Before fetching full details
ad_ids = tracker.get_unevaluated_posts(ad_ids)
```

This ensures:
- No wasted API calls
- No duplicate AI evaluations
- Efficient processing

### Database Tracking

```python
from dealradar.database import PostTracker

with PostTracker() as tracker:
    # Check if evaluated
    if tracker.is_evaluated('1213821530'):
        print("Already processed")

    # Get stats
    stats = tracker.get_stats()

    # Get high-value deals
    deals = tracker.get_high_value_deals(min_score=8)
```

### CLI Commands

```bash
# Scraping
python cli.py <ad_id>                           # Single listing
python cli.py --search <category> [--limit N]   # Category search
python cli.py --search 5021 --skip-db           # Skip database

# Database queries
python cli.py --stats                           # Statistics
python cli.py --deals [--min-score N]           # High-value deals
```

### Web API

```bash
# Start the web server
python web_server.py

# API endpoints
GET /api/listing/<ad_id>                        # Fetch single listing
GET /api/search?category=5021&limit=10          # Search by category
GET /health                                      # Health check
```

## Development Notes

### Environment Variables

Default values work with Docker Compose:
- DB_HOST=localhost
- DB_PORT=5432
- DB_NAME=dealradar
- DB_USER=dealradar
- DB_PASSWORD=dealradar

For production:
- DB_HOST=blocket-postgres-postgresql.postgres.svc.cluster.local

### Common Blocket Category IDs

- `5021` - Computers
- `5020` - Computer Accessories
- `5040` - Mobile Phones
- `5060` - Gaming Consoles
- `40` - Furniture & Home
- `10` - Vehicles

### Database Connection

Using Docker Compose:
```bash
docker-compose up -d
docker-compose exec postgres psql -U dealradar -d dealradar
```

Using kubectl (production):
```bash
kubectl exec -n postgres blocket-postgres-postgresql-0 -- \
  psql -U dealradar -d dealradar
```

## n8n Integration

**Complete guide:** See [N8N_WORKFLOWS.md](N8N_WORKFLOWS.md)

### Quick Setup

1. **Configure n8n credentials:**
   - PostgreSQL: Host, port, database, user, password
   - AI Provider: OpenAI or Anthropic API key
   - Notifications: Email/Slack/Telegram credentials

2. **Import 3 workflows:**
   - **Workflow 1:** Scraper (calls Flask API, stores in DB)
   - **Workflow 2:** Evaluator (queries DB, AI eval, saves results)
   - **Workflow 3:** Notifier (queries DB, sends alerts, marks notified)

3. **Activate workflows** and monitor executions

### Key PostgreSQL Views (Used by n8n)

**Unevaluated posts:**
```sql
SELECT * FROM unevaluated_posts LIMIT 10;
```

**Pending notifications:**
```sql
SELECT * FROM pending_notifications;
```

**High-value deals:**
```sql
SELECT * FROM high_value_deals;
```

### Direct Database Access

n8n connects directly to PostgreSQL (no API middleware needed):
- **Faster:** No HTTP overhead
- **Simpler:** No authentication required
- **Reliable:** Built-in connection pooling and retries

## Production Deployment

### Deploy Schema to Kubernetes

```bash
kubectl exec -n postgres blocket-postgres-postgresql-0 -- \
  psql -U dealradar -d dealradar < schema.sql
```

### Update Environment

Create `.env` with production values:
```bash
DB_HOST=blocket-postgres-postgresql.postgres.svc.cluster.local
DB_PORT=5432
DB_NAME=dealradar
DB_USER=dealradar
DB_PASSWORD=your_secure_password
```

### n8n Configuration

Configure n8n to use same PostgreSQL instance and deploy evaluation workflow.

## Technical Stack

- **Python**: 3.9+
- **Database**: PostgreSQL 18 (Bitnami)
- **HTTP Client**: httpx (async)
- **Database Driver**: psycopg2-binary
- **Concurrency**: asyncio with batched requests
- **Rate Limiting**: 3 parallel requests per batch, 0.5s delays

## Important Notes

### n8n Owns Automation

- **n8n handles:** Scheduling, evaluation, notifications, error handling
- **Python handles:** Blocket API scraping, data transformation
- **PostgreSQL handles:** State, deduplication, querying
- PostTracker is simplified (no evaluation/notification methods)

### AI Evaluation Context

When evaluating posts, consider:
- Swedish marketplace prices
- Condition vs. price ratio
- Typical market values for categories
- Location (shipping costs)
- Seller type (company vs. individual)

### Rate Limiting

Be respectful of Blocket's servers:
- Default: 3 parallel requests per batch
- 0.5s delay between batches
- Can be adjusted in `scraper.py`

## Troubleshooting

### Database connection failed
```bash
docker-compose ps        # Check if running
docker-compose logs      # Check logs
docker-compose restart   # Restart services
```

### Posts not being filtered
- Check evaluations table: `SELECT * FROM evaluations;`
- Verify status is 'completed' not 'pending'
- Check ad_id matches exactly

### n8n workflow not working
- Verify database credentials in n8n
- Test SQL queries in psql first
- Check n8n execution logs
- Ensure status updates are happening
