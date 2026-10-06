"""Prompts del asistente y construcción de la lista de mensajes.

Los prompts son parte del diseño de la aplicación: se versionan y se revisan
como cualquier otro código.
"""

from llm_client import Message


# TODO 4: prompt de sistema del asistente.
SYSTEM_PROMPT = """Eres el Asistente Inteligente del Curso de Inteligencia Artificial.

Tu función es apoyar a los estudiantes del curso resolviendo dudas y explicando conceptos
de Inteligencia Artificial de forma clara, precisa y pedagógica.

Responde siempre en español.

Los estudiantes tienen un nivel universitario y ya conocen conceptos fundamentales de
Inteligencia Artificial, incluyendo Transformers. Por lo tanto, adapta tus explicaciones
a ese nivel y evita explicaciones excesivamente básicas cuando no sean necesarias.

Puedes responder preguntas de conocimiento general sobre Inteligencia Artificial utilizando
tu conocimiento, pero debes distinguirlas de las preguntas que dependan de información
específica del curso.

Nunca inventes información específica del curso, incluyendo fechas de parciales o entregas,
notas, calificaciones, horarios, programa, contenidos programados, políticas, actividades
o material propio del profesor.

Si una pregunta requiere información específica del curso que no ha sido proporcionada
en la conversación, indica claramente que no tienes esa información y que debe consultarse
en la fuente oficial del curso. No supongas ni fabriques datos para completar la respuesta.

Mantén tus respuestas claras, útiles y directamente relacionadas con la pregunta del estudiante."""


ANALYSIS_PROMPT = """Analiza la pregunta de un estudiante del curso de IA.

Debes responder únicamente en formato json válido.

El objeto json debe contener exactamente estas claves:
- "tema": tema principal de la pregunta, en pocas palabras.
- "dificultad": uno de "basica", "intermedia" o "avanzada".
- "requiere_documentos_del_curso": true si la respuesta depende de información específica
del curso (fechas, notas, programa, material propio) que no es conocimiento general;
false en otro caso.
- "respuesta_corta": respuesta en máximo dos frases; si requiere documentos del curso,
escribe "No tengo esa información".

No agregues texto antes ni después del objeto json."""


def build_messages(history: list[Message], user_input: str) -> list[Message]:
    """Construye lo que realmente recibe el LLM: system + historial + pregunta actual."""
    messages: list[Message] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    messages.extend(history)

    messages.append(
        {"role": "user", "content": user_input}
    )

    return messages