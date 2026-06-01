class HealthState:
    def __init__(self):
        self.status = {
            'llm': 'unknown', 'voice_assistant': 'unknown',
            'fall_detection': 'unknown', 'emotion': 'unknown', 'alerts': 'unknown',
        }
        self.latency_ms = {
            'llm': None, 'voice_assistant': None,
            'fall_detection': None, 'emotion': None, 'alerts': None,
        }


health_state = HealthState()
