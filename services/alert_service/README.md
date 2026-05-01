# Alert Service — FiAinina P5

Real-time alert dispatching service. Listens to Redis for events (chutes, émotions, inactivité) from P3 & P4, déduplicates, then dispatches via WebSocket, Email, and SMS.

## 🚀 Quick Start

```bash
# 1. Configure credentials
cp .env.example .env
# Edit .env with your Gmail SMTP and Twilio credentials

# 2. Start the service
docker-compose up alert_service

# 3. Check health
curl http://localhost:8005/health | jq

# 4. Send a test alert
curl -X POST http://localhost:8005/alerts/test \
  -H "Content-Type: application/json" \
  -d '{"event_type":"fall_detected","user_id":"elder_001","severity":"high"}'
```

## 📋 Architecture

```
Redis Events (P3/P4) 
        ↓
Redis Subscriber (subscriber.py)
        ↓
Cooldown Check (cooldown_manager.py) → 5 min cooldown per user/event
        ↓
Fetch Recipients (PostgreSQL person_watchers)
        ↓
Parallel Dispatch:
├─ WebSocket Broadcast (frontend)
├─ Email (family members)
└─ SMS (caregivers, Twilio)
        ↓
Log to alert_log (PostgreSQL audit trail)
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, endpoints, startup/shutdown |
| `app/subscriber.py` | Redis PubSub listener (fall_events, emotion_events, inactivity_events) |
| `app/handlers/cooldown_manager.py` | Deduplication (Redis cooldown, TTL) |
| `app/handlers/websocket_handler.py` | WebSocket ConnectionManager, broadcast |
| `app/handlers/email_handler.py` | SMTP email sending (aiosmtplib) |
| `app/handlers/sms_handler.py` | Twilio SMS sending |
| `app/database.py` | SQLAlchemy async ORM |
| `app/models.py` | Pydantic models (AlertEvent, AlertLogEntry, etc) |

## 🔌 REST Endpoints

```bash
# Health check
GET /health

# Get alert history (paginated)
GET /alerts?limit=50&offset=0

# Send test alert (no P3/P4 required)
POST /alerts/test
Body: {
  "event_type": "fall_detected|emotion_distress|inactivity_detected",
  "user_id": "elder_id",
  "severity": "high|medium|low",
  "metadata": {...}
}

# WebSocket (real-time alerts)
WS /ws
```

## 🔄 Event Flow Example

1. **P3 (Fall Detection)** publishes to Redis:
   ```json
   {
     "event_type": "fall_detected",
     "user_id": "elder_001",
     "timestamp": "2025-05-01T12:00:00Z",
     "severity": "high",
     "confidence": 0.95,
     "metadata": {"pose_keypoints": [...]}
   }
   ```

2. **Alert Service** subscriber receives it

3. **Cooldown Check** : Is this the 1st alert for elder_001:fall_detected in 5 min?
   - Yes → Continue
   - No → Skip (log as "Still in cooldown")

4. **Fetch Recipients** from PostgreSQL (person_watchers + users)
   - Alice (family) → alice@example.com
   - Bob (caregiver) → bob@example.com

5. **Dispatch in Parallel** :
   - WebSocket : Send to all connected clients (frontend)
   - Email : Send to alice@example.com and bob@example.com
   - SMS : Send to caregivers (if phone configured)

6. **Log** all 3 notifications to alert_log table

## 🧪 Testing

```bash
# Unit tests
make test-unit

# All tests
make test

# With coverage
make test-cov

# Send test alert via API
make test-alert

# Publish test event to Redis
make redis-pubsub-test

# Check health
make test-health

# View alert history
make test-history
```

## 🔧 Configuration

See `.env.example` for all available options:

| Var | Example | Note |
|-----|---------|------|
| REDIS_URL | redis://redis:6379 | Pub/sub channels |
| DATABASE_URL | postgresql://... | alert_log, person_watchers |
| SMTP_USER | your@gmail.com | Email sender |
| SMTP_PASS | app-password | Gmail app password |
| TWILIO_SID | AC... | Twilio account |
| TWILIO_TOKEN | ... | Twilio token |
| TWILIO_FROM | +1234567890 | Twilio phone number |
| ALERT_COOLDOWN_MINUTES | 5 | Deduplication window |
| ENABLE_EMAIL | true | Feature flag |
| ENABLE_SMS | true | Feature flag |
| ENABLE_WEBSOCKET | true | Feature flag |

## 📊 Monitoring

```bash
# View logs
docker logs fi_ainina_alert -f

# Set debug logging
# Edit .env: LOG_LEVEL=DEBUG

# Monitor Redis
make redis-cli
> KEYS cooldown:*     # See active cooldowns
> PUBSUB CHANNELS    # See published channels

# Monitor PostgreSQL
make psql
=# SELECT * FROM alert_log ORDER BY created_at DESC LIMIT 10;
```

## 🐛 Troubleshooting

**WebSocket not connecting?**
- Ensure port 8005 is exposed in docker-compose
- Check logs: `docker logs fi_ainina_alert -f`

**Email not sending?**
- Verify SMTP credentials in .env
- Gmail: Generate app password (not regular password)
- Check logs for SMTP errors

**SMS not sending?**
- Verify Twilio SID, token, and FROM number
- Check SMS recipients have valid phone numbers
- Test in sandbox first

**Redis not connecting?**
- `make redis-cli` should work
- If not, restart: `docker-compose restart redis`

**PostgreSQL not connecting?**
- `make psql` should work
- Check DATABASE_URL in .env

## 📚 Full Documentation

See `IMPLEMENTATION_GUIDE.md` for:
- Detailed step-by-step implementation
- Architecture diagrams
- Testing procedures for each component
- Debugging tips
- Post-MVP roadmap

## 🚀 Deployment

For production, ensure:
- [ ] All env vars configured (especially secrets)
- [ ] SMTP SPF/DKIM configured (avoid spam folder)
- [ ] Twilio SMS tested (costly!)
- [ ] Redis persistence enabled
- [ ] PostgreSQL backups enabled
- [ ] Monitoring (Prometheus, CloudWatch, etc.)
- [ ] Rate limiting configured
- [ ] Error alerting setup (Sentry, etc.)

## 📝 Notes

- Cooldown is 5 min per (user_id, event_type) pair
- All clients connected to WebSocket receive all alerts (frontend filters)
- Email/SMS only sent if recipients configured in PostgreSQL
- Alert_log is append-only (soft-delete only for admin)
- Subscriber is background asyncio task (runs continuously)

---

**Ready to test?** Run `make help` to see all commands!
