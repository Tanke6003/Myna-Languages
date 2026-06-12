"""Constantes compartidas por la API (escenarios de conversación)."""

# Escenarios: etiqueta (la ve el usuario) -> instrucción de rol en inglés para el LLM
SCENARIOS = {
    "💬 Charla libre": "",
    "💼 Entrevista de trabajo": "You are role-playing a job interview; act as the interviewer and stay in character.",
    "🍽️ En un restaurante": "You are role-playing a restaurant scene; act as the waiter and stay in character.",
    "✈️ En el aeropuerto": "You are role-playing airport check-in; act as the airline agent and stay in character.",
    "🛍️ De compras": "You are role-playing shopping in a store; act as the shop assistant and stay in character.",
    "🩺 En el médico": "You are role-playing a doctor's appointment; act as the doctor and stay in character.",
    "🤝 Conociendo gente": "You are role-playing meeting someone new at a social event; act as a friendly new acquaintance.",
}

# Umbral de confianza de Whisper: por debajo, la palabra se marca como posible fallo de pronunciación
LOW_CONF = 0.55
