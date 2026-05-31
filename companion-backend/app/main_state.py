class HealthState:
    def __init__(self):
        self.status = {'alerts': 'unknown', 'llm': 'unknown', 'voice_assistant': 'unknown'}
        self.latency_ms = {'alerts': None, 'llm': None, 'voice_assistant': None}


health_state = HealthState()
