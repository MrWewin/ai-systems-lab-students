
"""Asistente con tools: el LLM PIDE, el programa EJECUTA.

Cada pregunta sigue tres pasos (una sola ronda de tools):
    1. pedir: mensajes + definiciones de tools → LLM → texto o tool_calls
    2. ejecutar: el programa valida, confirma las acciones y ejecuta cada tool
    3. responder: mensajes + resultados (rol "tool") → LLM → respuesta final

CourseAssistant no sabe nada de la consola ni de si una tool es local o viene de un
servidor MCP: recibe una lista de `Tool` y una función para confirmar acciones.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from llm_client import LLMClient, LLMResponse, Message, ToolCall
from prompts import build_messages
from tools import Tool


# La interfaz del chatbot decide cómo pedir autorización al usuario.
ConfirmFn = Callable[[Tool, dict[str, Any]], Awaitable[bool]]

REJECTED = "El usuario NO autorizó esta acción, así que no se ejecutó."


@dataclass
class ToolRun:
    call: ToolCall
    status: Literal["ok", "error", "rechazada"]
    result: str


@dataclass
class AssistantAnswer:
    text: str
    tool_runs: list[ToolRun]
    messages: list[Message]
    responses: list[LLMResponse]


class CourseAssistant:
    def __init__(
        self,
        llm: LLMClient,
        tools: list[Tool],
        confirm: ConfirmFn,
    ):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}

        if len(self.tools) != len(tools):
            raise ValueError("Hay dos tools con el mismo nombre.")

        self.confirm = confirm

    async def answer(
        self,
        question: str,
        history: list[Message] | None = None,
    ) -> AssistantAnswer:

        messages = build_messages(history or [], question)
        definitions = [tool.definition() for tool in self.tools.values()]

        # 1. PEDIR:
        # El LLM decide si responde directamente o solicita herramientas.
        first = self.llm.chat(messages, tools=definitions)

        if not first.tool_calls:
            return AssistantAnswer(
                text=first.text,
                tool_runs=[],
                messages=messages,
                responses=[first],
            )

        # 2. EJECUTAR:
        # TODO 2 COMPLETADO.
        tool_runs: list[ToolRun] = []

        # Agregamos la petición original del LLM al historial.
        messages.append(first.as_message())

        for call in first.tool_calls:

            # Ejecutamos la herramienta solicitada.
            run = await self.execute(call)

            # Guardamos el resultado para depuración.
            tool_runs.append(run)

            # Devolvemos el resultado al LLM.
            # tool_call_id identifica la petición correspondiente.
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": run.result,
                }
            )

        # 3. RESPONDER:
        # Segunda llamada al LLM con los resultados de las herramientas.
        # No permitimos nuevas llamadas a tools en esta ronda.
        final = self.llm.chat(
            messages,
            tools=definitions,
            allow_tools=False,
        )

        return AssistantAnswer(
            text=final.text,
            tool_runs=tool_runs,
            messages=messages,
            responses=[first, final],
        )

    async def execute(self, call: ToolCall) -> ToolRun:
        """Ejecuta una herramienta y devuelve su resultado o un error."""

        # Buscamos la herramienta solicitada por el LLM.
        tool = self.tools.get(call.name)

        if tool is None:
            return ToolRun(
                call,
                "error",
                f"Error: no existe la tool {call.name!r}.",
            )

        # Interpretamos los argumentos generados por el LLM.
        try:
            arguments = call.arguments()

        except ValueError as exc:
            return ToolRun(
                call,
                "error",
                f"Error: {exc}",
            )

        # TODO 5 COMPLETADO:
        # Las herramientas que modifican información requieren autorización.
        # El programa debe confirmar antes de ejecutarlas.
        if not tool.read_only:

            authorized = await self.confirm(
                tool,
                arguments,
            )

            # Si el usuario rechaza la acción, no la ejecutamos.
            if not authorized:
                return ToolRun(
                    call,
                    "rechazada",
                    REJECTED,
                )

        # Ejecutamos la herramienta únicamente si es de solo lectura
        # o si el usuario autorizó la acción.
        try:
            result = await tool.run(arguments)

        except Exception as exc:
            # Errores de argumentos, reglas de negocio o conexión MCP.
            return ToolRun(
                call,
                "error",
                f"Error: {exc}",
            )

        return ToolRun(
            call,
            "ok",
            result,
        )

