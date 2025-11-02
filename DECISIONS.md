# Architecture Decisions

## 2025-11-01: n8n-Centric Architecture

**Decision:** Use n8n workflows with direct PostgreSQL access instead of Python-based evaluation/notification logic.

**Rationale:**
- Simpler architecture with fewer moving parts
- n8n handles orchestration, scheduling, retries, and error handling out-of-the-box
- Direct PostgreSQL connections eliminate unnecessary API middleware
- Visual workflows are easier to debug and modify than distributed Python scripts
- Better separation of concerns: Flask API for scraping, n8n for automation, PostgreSQL for state

**Architecture:**
```
n8n Workflows → Flask API (scraping) → Blocket API
      ↓
PostgreSQL (direct connection)
```

**Components:**
- **Flask API**: Scrapes Blocket, returns JSON (no DB writes except post storage)
- **n8n Workflow 1**: Fetch posts via API → Store in PostgreSQL (every 30-60 min)
- **n8n Workflow 2**: Query unevaluated posts → AI evaluation → Store results (every 15 min)
- **n8n Workflow 3**: Query high-value deals → Send notifications → Mark as notified (every 10 min)
- **PostgreSQL**: Single source of truth, uses views for queries (`unevaluated_posts`, `pending_notifications`)

**Changes:**
- Remove notification/evaluation methods from `PostTracker`
- Keep Flask API minimal (scraping endpoints only)
- n8n owns evaluation and notification workflows entirely

**Trade-offs:**
- ✅ Simpler, more maintainable
- ✅ No authentication needed for internal workflows
- ✅ Easy to monitor and debug in n8n UI
- ❌ Dependency on n8n availability
- ❌ SQL in workflows instead of Python abstractions
