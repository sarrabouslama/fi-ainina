# 📋 Alert Service — Guide d'Implémentation Complet

Bienvenue ! Cette documentation explique chaque étape de l'implémentation du **Alert Service** et comment tester chaque composant.

---

## 🎯 Vue d'Ensemble

Le Alert Service est responsable de :

1. **Écouter Redis** → Recevoir événements de P3 (chutes) et P4 (émotions/inactivité)
2. **Dédupliquer** → Cooldown 5 min par type d'événement/utilisateur (anti-spam)
3. **Dispatcher** → Envoyer notifications via 3 canaux en parallèle :
   - **WebSocket** → Frontend (temps réel, <100ms)
   - **Email** → Proches (SMTP, ~5s)
   - **SMS** → Soignants (Twilio, ~3s)
4. **Logger** → Audit trail dans PostgreSQL (alertes_log table)

---

## 🔧 Architecture Technique

```
┌─────────────────────────────────────────────────────────────┐
│  Redis Channels (P3, P4 publient)                          │
│  • fall_events                                              │
│  • emotion_events                                           │
│  • inactivity_events                                        │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                                      ↓
┌─────────────────────────────────────────────────────────────┐
│  Alert Service Subscriber                                   │
│  (app/subscriber.py)                                        │
│  • Parse JSON AlertEvent                                   │
│  • Envoyer à handle_alert()                                 │
└─────────────────────────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ↓                       ↓                       ↓
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │   Cooldown Mgr   │  │    Recipients    │  │    Dispatch      │
    │   Redis cache    │  │   PostgreSQL DB  │  │    Parallel      │
    │   (5 min TTL)    │  │   (person_watcher)   │   asyncio       │
    └──────────────────┘  └──────────────────┘  └──────────────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ↓                       ↓                       ↓
    ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │    WebSocket     │  │      Email       │  │       SMS        │
    │    Broadcast     │  │      SMTP        │  │      Twilio      │
    │   → Frontend     │  │   → Proches      │  │   → Soignants    │
    └──────────────────┘  └──────────────────┘  └──────────────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
                                      ↓
                        ┌──────────────────────────┐
                        │  PostgreSQL alert_log    │
                        │  (audit trail)           │
                        └──────────────────────────┘
```

---

## 📁 Structure des Fichiers

```
services/alert_service/
├── app/
│   ├── __init__.py
│   ├── main.py                 ← FastAPI app (endpoints, startup)
│   ├── config.py               ← Configuration (env vars)
│   ├── models.py               ← Pydantic models
│   ├── subscriber.py           ← Redis pubsub listener
│   ├── database.py             ← SQLAlchemy async ORM
│   │
│   └── handlers/
│       ├── __init__.py
│       ├── cooldown_manager.py ← Déduplication (Redis cooldown)
│       ├── websocket_handler.py ← WebSocket ConnectionManager
│       ├── email_handler.py     ← SMTP email sender
│       └── sms_handler.py       ← Twilio SMS sender
│
├── requirements.txt            ← Python dependencies
├── Dockerfile                  ← Docker build
├── .env.example                ← Configuration template
└── README.md                   ← This file
```

---

## 🚀 Mise en Place

### 1️⃣ Configurer les Variables d'Environnement

```bash
# Copier le fichier template
cp services/alert_service/.env.example services/alert_service/.env

# Éditer .env avec vos credentials
# Sections importantes :
#   - REDIS_URL (déjà configuré dans docker-compose)
#   - DATABASE_URL (déjà configuré)
#   - SMTP_* (Gmail ou autre)
#   - TWILIO_* (SMS)
```

**Gmail SMTP (pour tester):**
- Activer l'authentification 2FA sur votre compte Google
- Aller sur https://myaccount.google.com/apppasswords
- Générer une clé d'app "Mail"
- Copier le mot de passe 16 caractères dans SMTP_PASS

**Twilio SMS (production):**
- S'inscrire : https://www.twilio.com/console
- Copier Account SID et Auth Token
- Obtenir un numéro Twilio pour TWILIO_FROM
- Budget : ~0.0075 USD par SMS

### 2️⃣ Démarrer le Service

```bash
# Depuis la racine du projet
docker-compose up alert_service

# Logs :
# ✓ Alert Service initialized successfully
# ✓ Subscribed to Redis channels: fall_events, emotion_events, inactivity_events
# ✓ WebSocket server listening on 0.0.0.0:8005
```

### 3️⃣ Vérifier la Santé

```bash
curl http://localhost:8005/health

# Réponse attendue :
{
  "service": "alert_service",
  "status": "ok",
  "redis_connected": true,
  "database_connected": true,
  "timestamp": "2025-05-01T12:00:00"
}
```

---

## 🧪 Étapes de Test — Chaque Composant

### Étape 1 : Tester Redis Pubsub (Simuler P3/P4)

**Scénario** : Simuler une alerte de chute depuis Redis, s'assurer que le service la reçoit.

**Terminal 1** - Se connecter au container Redis :
```bash
docker exec -it fi_ainina_redis redis-cli
```

**Terminal 1** - Publier un événement de chute (P3) :
```redis
PUBLISH fall_events '{"event_type":"fall_detected","user_id":"elder_001","timestamp":"2025-05-01T12:00:00Z","severity":"high","confidence":0.95,"metadata":{"pose_keypoints":[]}}'
```

**Terminal 2** - Vérifier les logs du service :
```bash
docker logs fi_ainina_alert -f

# Attendu :
# Parsed alert: fall_detected from elder_001 with severity high
# Processing alert: fall_detected from elder_001 (severity: high)
# Alert processed successfully: fall_detected/elder_001
```

**✅ Étape 1 réussie** si :
- L'alerte est reçue et parsée
- Log "Processing alert" s'affiche

---

### Étape 2 : Tester Cooldown (Déduplication)

**Scénario** : Envoyer 2 alertes similaires rapidement, vérifier que la 2e est ignorée.

**Terminal 1** - Redis CLI (du terminal précédent) :
```redis
# 1ère alerte (doit être envoyée)
PUBLISH fall_events '{"event_type":"fall_detected","user_id":"elder_001","timestamp":"2025-05-01T12:00:00Z","severity":"high","confidence":0.95,"metadata":{}}'

# Attendre 1 seconde, puis 2e alerte (doit être skippée)
PUBLISH fall_events '{"event_type":"fall_detected","user_id":"elder_001","timestamp":"2025-05-01T12:00:01Z","severity":"high","confidence":0.92,"metadata":{}}'
```

**Terminal 2** - Logs :
```bash
docker logs fi_ainina_alert -f

# Attendu :
# Processing alert: fall_detected from elder_001 (severity: high)
# Alert processed successfully: fall_detected/elder_001
# 
# [2e alerte arrive] 
# Can_send_alert: Still in cooldown: 0.1 min < 5 min (skipping alert for elder_001:fall_detected)
```

**✅ Étape 2 réussie** si :
- 1ère alerte traitée
- 2e alerte skippée (message "Still in cooldown")

---

### Étape 3 : Tester WebSocket (Frontend)

**Scénario** : S'ouvrir une connexion WebSocket, recevoir une alerte en temps réel.

**Terminal 1** - Lancer un client WebSocket (Python) :
```bash
python3 << 'EOF'
import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8005/ws"
    async with websockets.connect(uri) as ws:
        print("✓ Connected to WebSocket")
        
        # Attendre les messages
        for i in range(5):  # Écouter 5 messages max
            msg = await asyncio.wait_for(ws.recv(), timeout=30)
            data = json.loads(msg)
            print(f"\n📨 Reçu : {data['event_type']} ({data['severity']})")
            print(f"   User: {data['user_id']}")
            print(f"   Timestamp: {data['timestamp']}")

asyncio.run(test_ws())
EOF
```

**Terminal 2** - Publier une alerte depuis Redis :
```bash
docker exec -it fi_ainina_redis redis-cli
PUBLISH fall_events '{"event_type":"fall_detected","user_id":"elder_001","timestamp":"2025-05-01T12:00:00Z","severity":"high","confidence":0.95,"metadata":{}}'
```

**✅ Étape 3 réussie** si :
- Le client WebSocket reçoit le message JSON dans les 100ms
- Les champs event_type, user_id, severity, timestamp sont présents

---

### Étape 4 : Tester Email (SMTP)

**Scénario** : Envoyer une alerte, vérifier qu'un email est envoyé aux proches.

⚠️ **Prérequis** : 
- SMTP_USER et SMTP_PASS configurés dans .env
- Au moins 1 utilisateur avec role="family" dans person_watchers pour elder_001

**Setup (SQL)** - Ajouter des testeurs à la base :
```sql
-- Se connecter à PostgreSQL
docker exec -it fi_ainina_postgres psql -U postgres -d fi_ainina

-- Insérer une personne monitorée
INSERT INTO monitored_persons (name, room) 
VALUES ('Test Person', 'Room 101')
RETURNING id;

-- Copier l'ID retourné (ex: 123e4567-e89b-12d3-a456-426614174000)

-- Ajouter un utilisateur (family member)
INSERT INTO users (name, email, role, password_hash) 
VALUES ('Alice Family', 'alice@example.com', 'family', 'hash')
RETURNING id;

-- Copier l'ID de l'utilisateur

-- Lier l'utilisateur à la personne monitorée
INSERT INTO person_watchers (user_id, person_id) 
VALUES ('USER_ID', 'PERSON_ID');
```

**Terminal** - Publier une alerte :
```bash
docker exec -it fi_ainina_redis redis-cli
PUBLISH fall_events '{"event_type":"fall_detected","user_id":"123e4567-e89b-12d3-a456-426614174000","timestamp":"2025-05-01T12:00:00Z","severity":"high","confidence":0.95,"metadata":{}}'
```

**Vérifier les logs** :
```bash
docker logs fi_ainina_alert -f

# Attendu :
# Email sent to 1 recipients for fall_detected
```

**✅ Étape 4 réussie** si :
- Email envoyé sans erreur dans les logs
- (Optionnel) Email reçu par alice@example.com

---

### Étape 5 : Tester SMS (Twilio)

**Scénario** : Envoyer une alerte à un soignant via SMS.

⚠️ **Prérequis** :
- Twilio SID, Token, From number configurés
- Utilisateur avec role="caregiver" et phone défini dans la base

**Setup (SQL)** :
```sql
-- Ajouter un utilisateur caregiver
INSERT INTO users (name, email, role, password_hash) 
VALUES ('Bob Caregiver', 'bob@example.com', 'caregiver', 'hash')
RETURNING id;

-- Copier l'ID, puis lier à la personne monitorée
INSERT INTO person_watchers (user_id, person_id) 
VALUES ('CAREGIVER_ID', 'PERSON_ID');

-- Note: phone field not in users table by default
-- À étendre si SMS pour soignants est requis
```

**Vérifier les logs** :
```bash
docker logs fi_ainina_alert -f

# Attendu :
# SMS sent to +216XXXXXXXX (SID: SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
```

**✅ Étape 5 réussie** si :
- SMS envoyé sans erreur (Twilio SID visible dans logs)

---

### Étape 6 : Tester Historique (GET /alerts)

**Scénario** : Récupérer l'historique paginé des alertes depuis PostgreSQL.

**Terminal** :
```bash
# Récupérer les 10 dernières alertes
curl "http://localhost:8005/alerts?limit=10&offset=0" | jq

# Réponse attendue :
{
  "total": 5,
  "limit": 10,
  "offset": 0,
  "alerts": [
    {
      "id": "123...",
      "event_type": "fall_detected",
      "channel": "websocket",
      "recipient": "broadcast",
      "status": "sent",
      "created_at": "2025-05-01T12:00:00Z"
    },
    ...
  ]
}
```

**✅ Étape 6 réussie** si :
- Réponse 200 OK
- "total" > 0 (alertes envoyées précédemment)
- Champs corrects : event_type, channel, status

---

### Étape 7 : Tester Alerte Manuelle (POST /alerts/test)

**Scénario** : Créer une alerte sans attendre P3/P4, utile pour tester.

**Terminal** :
```bash
curl -X POST http://localhost:8005/alerts/test \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "emotion_distress",
    "user_id": "elder_001",
    "severity": "medium",
    "metadata": {"emotion": "sad", "score": 0.85}
  }' | jq

# Réponse attendue :
{
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "event_type": "emotion_distress",
  "user_id": "elder_001"
}
```

**Vérifier les logs** :
```bash
docker logs fi_ainina_alert -f

# Attendu :
# Test alert created: 550e8400-e29b-41d4-a716-446655440000
# Processing alert: emotion_distress from elder_001 (severity: medium)
# Alert processed successfully: emotion_distress/elder_001
```

**✅ Étape 7 réussie** si :
- Réponse 200 + alert_id
- Alerte traitée normalement

---

## 🔍 Debugging

### Logs du Service

```bash
# Vue en temps réel
docker logs fi_ainina_alert -f

# Définir le niveau de logs en DEBUG
# Éditer .env :
LOG_LEVEL=DEBUG

# Redémarrer le service
docker-compose restart alert_service
```

### Vérifier Redis

```bash
# Se connecter à Redis
docker exec -it fi_ainina_redis redis-cli

# Vérifier les clés de cooldown (format: cooldown:{user_id}:{event_type})
KEYS cooldown:*

# Vérifier une clé spécifique
GET cooldown:elder_001:fall_detected

# Voir les canaux publiés
PUBSUB CHANNELS

# Écouter les messages en temps réel
SUBSCRIBE fall_events emotion_events inactivity_events
```

### Vérifier PostgreSQL

```bash
# Se connecter à PostgreSQL
docker exec -it fi_ainina_postgres psql -U postgres -d fi_ainina

-- Voir les dernières alertes
SELECT * FROM alert_log ORDER BY created_at DESC LIMIT 10;

-- Compter les alertes par channel
SELECT channel, COUNT(*) FROM alert_log GROUP BY channel;

-- Voir les watchers pour une personne
SELECT u.name, u.email, u.role 
FROM users u 
INNER JOIN person_watchers pw ON u.id = pw.user_id 
WHERE pw.person_id = '123e4567-e89b-12d3-a456-426614174000';
```

---

## ⚠️ Troubleshooting

| Problème | Cause | Solution |
|----------|-------|----------|
| WebSocket: "Connection refused" | Port 8005 non accessible | Vérifier docker-compose.yml expose 8005 |
| Email: "SMTP auth failed" | Credentials incorrects | Regénérer app password Gmail |
| SMS: "Twilio not initialized" | TWILIO_SID/TOKEN manquants | Remplir .env avec Twilio credentials |
| Redis: "Connection error" | Redis pas démarré | `docker-compose up redis` |
| Database: "Connection error" | PostgreSQL down | `docker-compose up postgres` |
| Alert ignored (cooldown) | 2e alerte < 5 min | Attendre 5 min ou lancer avec user_id différent |

---

## 📊 Monitoring en Production

### Prometheus Metrics (optionnel)

Ajouter à main.py :
```python
from prometheus_client import Counter, Histogram

alerts_received = Counter('alerts_received_total', 'Total alerts received', ['event_type'])
alerts_sent = Counter('alerts_sent_total', 'Total alerts sent', ['channel'])
alert_processing_time = Histogram('alert_processing_seconds', 'Alert processing duration')

# Utiliser :
alerts_received.labels(event_type='fall_detected').inc()
```

### Health Checks

```bash
# Container health check (docker-compose)
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
  interval: 10s
  timeout: 5s
  retries: 3
```

---

## 🎓 Résumé des Étapes Implémentées

| Étape | Fichier | Description |
|-------|---------|-------------|
| 1 | config.py | Variables d'environnement (SMTP, Twilio, DB) |
| 2 | models.py | Pydantic models (AlertEvent, AlertLogEntry, etc) |
| 3 | subscriber.py | Redis listener asynchrone (3 canaux) |
| 4 | cooldown_manager.py | Déduplication via Redis (TTL 5 min) |
| 5 | websocket_handler.py | ConnectionManager + broadcast |
| 6 | email_handler.py | SMTP async avec aiosmtplib |
| 7 | sms_handler.py | Twilio SDK sync (préférer async si besoin) |
| 8 | database.py | SQLAlchemy async ORM + queries |
| 9 | main.py | FastAPI app + endpoints + startup |
| 10 | requirements.txt | Dépendances (websockets, asyncpg, etc) |

---

## 🚀 Prochaines Étapes (Post-MVP)

- [ ] Authentication : bearer token sur WebSocket
- [ ] Rate limiting : anti-DDoS
- [ ] Alertes urgentes : bypass cooldown pour severity="critical"
- [ ] Slack integration : canal supplémentaire
- [ ] Prometheus metrics : monitoring production
- [ ] Unit tests : pytest + mocking
- [ ] Integration tests : docker-compose test env
- [ ] Webhook support : notifier third-party systems

---

**Questions ?** Consultez les commentaires dans les fichiers .py ou lancez `docker logs fi_ainina_alert -f` pour le debug.

Bon courage ! 🚀
