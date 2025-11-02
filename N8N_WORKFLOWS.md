# n8n Workflows for DealRadar

This document provides complete n8n workflow configurations for the DealRadar system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   n8n Workflows                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Workflow 1: Scraper (every 30-60 min)                  │
│    → Calls Flask API                                     │
│    → Stores posts in PostgreSQL                          │
│                                                          │
│  Workflow 2: Evaluator (every 15 min)                   │
│    → Queries unevaluated posts from PostgreSQL           │
│    → AI evaluates each post                              │
│    → Stores results in PostgreSQL                        │
│                                                          │
│  Workflow 3: Notifier (every 10 min)                    │
│    → Queries high-value deals from PostgreSQL            │
│    → Sends notifications (Email/Slack/Telegram)          │
│    → Marks as notified in PostgreSQL                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. PostgreSQL Credential in n8n

Add a PostgreSQL credential with these settings:

- **Name:** `dealradar-postgres`
- **Host:** `localhost` (development) or `blocket-postgres-postgresql.postgres.svc.cluster.local` (production)
- **Port:** `5432`
- **Database:** `dealradar`
- **User:** `dealradar`
- **Password:** Your database password
- **SSL:** Disabled (for local) or Enabled (for production)

### 2. OpenAI/Claude Credential (for AI evaluation)

Add an AI credential:
- **Name:** `openai-api` or `anthropic-api`
- **API Key:** Your API key

### 3. Notification Credentials (optional)

Configure one or more:
- **Email (SMTP)**
- **Slack**
- **Telegram**

---

## Workflow 1: Scraper - Fetch & Store Posts

**Schedule:** Every 30-60 minutes

### Workflow Description

1. Fetches listings from Blocket via Flask API
2. Loops through each listing
3. Stores in PostgreSQL (skips duplicates automatically)

### Nodes Configuration

#### Node 1: Schedule Trigger
```
Type: Schedule Trigger
Cron: 0 */30 * * * *  (every 30 minutes)
```

#### Node 2: HTTP Request - Fetch Listings
```
Type: HTTP Request
Method: GET
URL: http://localhost:5000/api/search
Query Parameters:
  - category: 5021
  - limit: 20

Authentication: None
```

#### Node 3: Check If Success
```
Type: IF
Condition: {{ $json.success }} equals true
```

#### Node 4: Extract Listings Array
```
Type: Code
JavaScript:
return $json.data.listings.map(listing => ({ json: listing }));
```

#### Node 5: Loop Through Listings
```
Type: Loop (comes from Code node)
```

#### Node 6: PostgreSQL - Insert Post
```
Type: Postgres
Operation: Execute Query
Query:
INSERT INTO posts (
    ad_id, title, price, description, seller, location,
    category, company_ad, type, region, images, raw_data
)
VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
)
ON CONFLICT (ad_id) DO UPDATE SET
    title = EXCLUDED.title,
    price = EXCLUDED.price,
    description = EXCLUDED.description,
    raw_data = EXCLUDED.raw_data;

Query Parameters:
  $1: {{ $json.ad_id }}
  $2: {{ $json.title }}
  $3: {{ $json.price }}
  $4: {{ $json.description }}
  $5: {{ $json.seller }}
  $6: {{ $json.location }}
  $7: {{ $json.category }}
  $8: {{ $json.company_ad }}
  $9: {{ $json.type }}
  $10: {{ $json.region }}
  $11: {{ JSON.stringify($json.images) }}
  $12: {{ JSON.stringify($json) }}
```

---

## Workflow 2: Evaluator - AI Evaluation

**Schedule:** Every 15 minutes

### Workflow Description

1. Queries posts that need evaluation
2. For each post, sends to AI for evaluation
3. Saves evaluation results back to database

### Nodes Configuration

#### Node 1: Schedule Trigger
```
Type: Schedule Trigger
Cron: 0 */15 * * * *  (every 15 minutes)
```

#### Node 2: PostgreSQL - Get Unevaluated Posts
```
Type: Postgres
Operation: Execute Query
Query:
SELECT * FROM unevaluated_posts
ORDER BY discovered_at DESC
LIMIT 10;
```

#### Node 3: Check If Posts Exist
```
Type: IF
Condition: {{ $json.length }} > 0
```

#### Node 4: Loop Through Posts
```
Type: Loop (from IF node True branch)
```

#### Node 5: Build AI Prompt
```
Type: Code
JavaScript:
const post = $input.item.json;

const prompt = `Evaluate this Swedish marketplace listing and provide a value score from 1-10.

Title: ${post.title}
Price: ${post.price} SEK
Description: ${post.description}
Location: ${post.location}
Category: ${post.category}
Seller: ${post.seller}
Company Ad: ${post.company_ad ? 'Yes' : 'No'}

Consider:
- Is the price reasonable compared to market value?
- Is the item in good condition based on the description?
- Is this a genuine good deal or just average?
- Are there any red flags (too good to be true, vague description)?

Respond with ONLY a JSON object in this format:
{
  "score": 7,
  "reasoning": "Brief explanation of the score"
}`;

return {
  json: {
    ad_id: post.ad_id,
    prompt: prompt,
    post: post
  }
};
```

#### Node 6: OpenAI/Claude - Evaluate
```
Type: OpenAI (or Anthropic)
Resource: Message
Model: gpt-4o-mini (or claude-3-haiku)
Prompt: {{ $json.prompt }}
Response Format: JSON
Temperature: 0.3
Max Tokens: 200
```

#### Node 7: Parse AI Response
```
Type: Code
JavaScript:
const aiResponse = JSON.parse($json.message.content[0].text);
const ad_id = $('Build AI Prompt').item.json.ad_id;

return {
  json: {
    ad_id: ad_id,
    value_score: aiResponse.score,
    evaluation_notes: aiResponse.reasoning
  }
};
```

#### Node 8: PostgreSQL - Save Evaluation
```
Type: Postgres
Operation: Execute Query
Query:
INSERT INTO evaluations (ad_id, status, value_score, evaluation_notes, evaluated_at)
VALUES ($1, 'completed', $2, $3, NOW())
ON CONFLICT (ad_id) DO UPDATE SET
    status = 'completed',
    value_score = EXCLUDED.value_score,
    evaluation_notes = EXCLUDED.evaluation_notes,
    evaluated_at = NOW();

Query Parameters:
  $1: {{ $json.ad_id }}
  $2: {{ $json.value_score }}
  $3: {{ $json.evaluation_notes }}
```

#### Node 9: Error Handling (Optional)
```
Type: Set (on error trigger)
Save evaluation error to database
```

---

## Workflow 3: Notifier - Send High-Value Alerts

**Schedule:** Every 10 minutes

### Workflow Description

1. Queries high-value deals that haven't been notified
2. Sends notification via configured channel
3. Marks as notified in database

### Nodes Configuration

#### Node 1: Schedule Trigger
```
Type: Schedule Trigger
Cron: 0 */10 * * * *  (every 10 minutes)
```

#### Node 2: PostgreSQL - Get Pending Notifications
```
Type: Postgres
Operation: Execute Query
Query:
SELECT * FROM pending_notifications
LIMIT 10;
```

#### Node 3: Check If Deals Exist
```
Type: IF
Condition: {{ $json.length }} > 0
```

#### Node 4: Loop Through Deals
```
Type: Loop (from IF node True branch)
```

#### Node 5: Format Notification Message
```
Type: Code
JavaScript:
const deal = $input.item.json;
const blocketUrl = `https://www.blocket.se/annons/${deal.ad_id}`;

const message = `🔥 High-Value Deal Alert! (Score: ${deal.value_score}/10)

📦 ${deal.title}
💰 ${deal.price} SEK
📍 ${deal.location}

📝 AI Notes: ${deal.evaluation_notes}

🔗 View listing: ${blocketUrl}
`;

return {
  json: {
    ad_id: deal.ad_id,
    value_score: deal.value_score,
    message: message,
    url: blocketUrl
  }
};
```

#### Node 6a: Send Email (Option 1)
```
Type: Email Send
To: your-email@example.com
Subject: 🔥 DealRadar Alert: {{ $json.title }} ({{ $json.value_score }}/10)
Text: {{ $json.message }}
```

#### Node 6b: Send Slack (Option 2)
```
Type: Slack
Resource: Message
Channel: #deals
Text: {{ $json.message }}
```

#### Node 6c: Send Telegram (Option 3)
```
Type: Telegram
Resource: Message
Chat ID: your-chat-id
Text: {{ $json.message }}
Parse Mode: Markdown
```

#### Node 7: PostgreSQL - Mark as Notified
```
Type: Postgres
Operation: Execute Query
Query:
INSERT INTO notifications (ad_id, value_score, notification_channel, notified_at)
VALUES ($1, $2, $3, NOW());

Query Parameters:
  $1: {{ $json.ad_id }}
  $2: {{ $json.value_score }}
  $3: 'email'  (or 'slack', 'telegram')
```

---

## Advanced Configurations

### 1. Multi-Category Scraping

Update Workflow 1 to scrape multiple categories:

```javascript
// Node: Define Categories
const categories = [
  { id: '5021', name: 'Computers' },
  { id: '5020', name: 'Computer Accessories' },
  { id: '5040', name: 'Mobile Phones' },
  { id: '5060', name: 'Gaming Consoles' }
];

return categories.map(cat => ({ json: cat }));
```

Then loop through categories and fetch each.

### 2. Rate Limiting AI Calls

Add a delay between AI evaluations:

```
Type: Wait
Amount: 2
Unit: Seconds
```

Insert this between the AI evaluation node and the save node.

### 3. Error Handling for Failed Evaluations

Add an error workflow that catches failures:

```
Type: Error Trigger
Then: Execute Query
Query:
INSERT INTO evaluations (ad_id, status, error_message, evaluated_at)
VALUES ($1, 'error', $2, NOW())
ON CONFLICT (ad_id) DO UPDATE SET
    status = 'error',
    error_message = EXCLUDED.error_message,
    evaluated_at = NOW();
```

### 4. Smart Filtering

Pre-filter obvious low-value items before AI evaluation:

```javascript
// Node: Quick Filter
const post = $json;

// Skip company ads for certain categories
if (post.company_ad && post.category === '5021') {
  return { skip: true };
}

// Skip if price is too high (configurable)
const priceMatch = post.price.match(/\d+/);
const price = priceMatch ? parseInt(priceMatch[0]) : 0;

if (price > 50000) {
  return { skip: true };
}

return { skip: false, post: post };
```

### 5. Batch Notifications

Instead of notifying immediately, collect deals and send a daily digest:

- Change notifier schedule to once per day
- Format as HTML email with all deals
- Include summary statistics

---

## Testing Workflows

### Test Workflow 1 (Scraper)
```bash
# Manually trigger via n8n UI or:
curl -X POST http://localhost:5678/webhook-test/scraper
```

### Test Workflow 2 (Evaluator)
```sql
-- Manually insert a test post
INSERT INTO posts (ad_id, title, price, description, category)
VALUES ('TEST123', 'Test Item', '500 SEK', 'Test description', '5021');

-- Then trigger workflow and check:
SELECT * FROM evaluations WHERE ad_id = 'TEST123';
```

### Test Workflow 3 (Notifier)
```sql
-- Manually insert high-value evaluation
INSERT INTO evaluations (ad_id, status, value_score, evaluation_notes)
VALUES ('TEST123', 'completed', 9, 'Test notification');

-- Then trigger workflow and check:
SELECT * FROM notifications WHERE ad_id = 'TEST123';
```

---

## Monitoring & Maintenance

### Check Workflow Health

**View execution logs:**
- Go to n8n UI → Executions
- Filter by workflow
- Check success/failure rates

**Database queries for monitoring:**

```sql
-- Total posts scraped today
SELECT COUNT(*) FROM posts WHERE discovered_at >= CURRENT_DATE;

-- Pending evaluations
SELECT COUNT(*) FROM unevaluated_posts;

-- High-value deals found today
SELECT COUNT(*) FROM evaluations
WHERE value_score >= 8
  AND evaluated_at >= CURRENT_DATE;

-- Notification statistics
SELECT
  notification_channel,
  COUNT(*) as total_sent,
  MAX(notified_at) as last_notification
FROM notifications
GROUP BY notification_channel;
```

### Common Issues

**Issue: AI evaluation fails**
- Check API key is valid
- Verify API rate limits not exceeded
- Check prompt returns valid JSON

**Issue: Duplicate notifications**
- Verify notifications table has entries
- Check IF condition in notifier workflow
- Ensure ad_id matches exactly

**Issue: No posts being scraped**
- Test Flask API manually: `curl http://localhost:5000/api/search?category=5021&limit=5`
- Check Flask logs for errors
- Verify Blocket API is accessible

---

## Cost Optimization

### Reduce AI Costs

1. **Use cheaper models:**
   - `gpt-4o-mini` instead of `gpt-4`
   - `claude-3-haiku` instead of `claude-3-sonnet`

2. **Filter before AI:**
   - Skip company ads for certain categories
   - Skip items outside price range
   - Skip items with keywords (e.g., "defekt", "trasig")

3. **Batch evaluations:**
   - Evaluate in larger batches less frequently
   - Prioritize newer posts

### Reduce Database Load

1. **Use views** (already created): `unevaluated_posts`, `pending_notifications`
2. **Add indexes** (already created in schema.sql)
3. **Archive old posts** (optional):

```sql
-- Archive posts older than 30 days
CREATE TABLE posts_archive AS
SELECT * FROM posts WHERE discovered_at < NOW() - INTERVAL '30 days';

DELETE FROM posts WHERE discovered_at < NOW() - INTERVAL '30 days';
```

---

## Production Deployment

### Environment Variables in n8n

Set these environment variables:

```bash
DB_HOST=blocket-postgres-postgresql.postgres.svc.cluster.local
DB_PORT=5432
DB_NAME=dealradar
DB_USER=dealradar
DB_PASSWORD=your_secure_password
FLASK_API_URL=http://dealradar-api:5000
```

### Workflow Activation

1. Import each workflow JSON
2. Update credentials references
3. Update environment-specific URLs
4. Test each workflow manually
5. Activate workflows

### Backup Strategy

**n8n workflows:**
- Export workflows regularly (Settings → Workflows → Export)
- Version control exported JSON files

**Database:**
```bash
# Backup script
kubectl exec -n postgres blocket-postgres-postgresql-0 -- \
  pg_dump -U dealradar dealradar > backup-$(date +%Y%m%d).sql
```

---

## Next Steps

1. **Import workflows** into n8n
2. **Configure credentials** (PostgreSQL, AI, notifications)
3. **Test each workflow** manually
4. **Monitor executions** for first 24 hours
5. **Adjust schedules** based on volume
6. **Fine-tune AI prompts** based on results
7. **Set up alerts** for workflow failures

For questions or issues, check the n8n community forum or the DealRadar documentation.
