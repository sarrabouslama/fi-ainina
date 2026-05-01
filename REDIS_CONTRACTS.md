// P3+P4 : le format JSON que vous allez publier sur Redis. Voici le template — remplissez juste les champs event_type et metadata selon votre service 

# Redis Event Contracts — ElderLink

## Format commun (tous les canaux)
```json
{
  "event_type": "fall_detected",
  "user_id": "elder_001",
  "timestamp": "2025-01-15T14:30:00Z",
  "severity": "high",
  "confidence": 0.92,
  "metadata": {}
}
```

## Canaux et champs spécifiques

### fall_events (P3 remplit)
- event_type: "fall_detected"
- severity: "high" | "medium"
- metadata: { "pose_keypoints": [...] }  ← P3 complète

### emotion_events (P4 remplit)
- event_type: "emotion_distress"
- severity: "high" | "medium" | "low"
- metadata: { "emotion": "sad", "score": 0.87 }  ← P4 complète

### inactivity_events (P4 remplit)
- event_type: "inactivity_detected"
- severity: "medium"
- metadata: { "duration_seconds": 1800 }  ← P4 complète