
"""Cliente MCP: conecta el asistente con el servidor "Servicios académicos".

Responsabilidades:
  1. Lanzar el servidor como subproceso y hablarle por stdin/stdout (transporte stdio).
  2. Descubrir sus tools (list_tools) y CONVERTIRLAS en el mismo `Tool` que las tools locales.
     Ese adaptador es lo que hace que el asistente no distinga una tool local de una remota.
  3. Leer resources cuando la aplicación lo decide.

Es el único módulo del asistente que importa `mcp` (el servidor es otro programa).
El SDK de MCP es asíncrono: el cliente espera respuestas de otro proceso.

Uso (sin LLM ni API key):
    uv run python labs/03-mcp/mcp_client.py
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult
from mcp.types import Tool as MCPTool

from tools import Tool, ToolExecutionError


SERVER_SCRIPT = Path(__file__).resolve().parent / "mcp_server.py"


def server_parameters() -> StdioServerParameters:
    # El servidor se ejecuta con el mismo intérprete que el asistente.
    return StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )


def result_to_text(result: CallToolResult) -> str:
    """El resultado MCP es una lista de bloques de contenido; el LLM recibirá su texto."""

    text = "\n".join(
        block.text
        for block in result.content
        if block.type == "text"
    )

    if result.is_error:
        raise ToolExecutionError(text)

    return text


def to_tool(client: Client, mcp_tool: MCPTool) -> Tool:
    """Adaptador: definición MCP → Tool (la misma clase que usan las tools locales)."""

    # TODO 3 COMPLETADO:
    # Convertimos una herramienta MCP en una herramienta compatible
    # con CourseAssistant.

    async def run(arguments: dict[str, Any]) -> str:
        """Ejecuta una herramienta remota utilizando el cliente MCP."""

        result = await client.call_tool(
            mcp_tool.name,
            arguments,
        )

        return result_to_text(result)

    # Una herramienta solo es de lectura si el servidor lo declara.
    # Si no existe esa anotación, se considera una acción con efectos.
    read_only = (
        mcp_tool.annotations is not None
        and mcp_tool.annotations.read_only_hint is True
    )

    # Identificamos el servidor que proporciona la herramienta.
    origin = (
        client.server_info.name
        if client.server_info is not None
        else "mcp"
    )

    return Tool(
        name=mcp_tool.name,
        description=mcp_tool.description or "",
        parameters=mcp_tool.input_schema,
        run=run,
        read_only=read_only,
        origin=origin,
    )


async def load_mcp_tools(client: Client) -> list[Tool]:
    """Descubre y convierte las herramientas del servidor MCP."""

    listed = await client.list_tools()

    return [
        to_tool(client, mcp_tool)
        for mcp_tool in listed.tools
    ]


async def read_resource_text(client: Client, uri: str) -> str:
    """Lee el contenido de un recurso publicado por el servidor MCP."""

    result = await client.read_resource(uri)

    return "\n".join(
        content.text
        for content in result.contents
        if hasattr(content, "text")
    )


async def _demo() -> None:
    """Demostración de conexión y descubrimiento MCP sin utilizar un LLM."""

    async with Client(server_parameters()) as client:

        info = client.server_info

        print(
            f"Conectado a {info.name if info else '?'} "
            f"(protocolo MCP {client.protocol_version})\n"
        )

        tools = await load_mcp_tools(client)

        print("Tools descubiertas (list_tools), ya convertidas a Tool:")

        for tool in tools:

            kind = "solo lectura" if tool.read_only else "ACCIÓN"

            print(
                f"\n- {tool.name} [{kind}]\n"
                f"  {tool.description.splitlines()[0]}"
            )

            print(
                "  parameters:",
                json.dumps(tool.parameters, ensure_ascii=False),
            )

        print("\nResources (list_resources):")

        for resource in (await client.list_resources()).resources:
            print(
                f"- {resource.uri}: {resource.description}"
            )

        print("\nContenido de academico://calendario:")

        print(
            await read_resource_text(
                client,
                "academico://calendario",
            )
        )

        by_name = {
            tool.name: tool
            for tool in tools
        }

        if "consultar_notas" not in by_name:

            print(
                "\n(consultar_notas aún no existe "
                "en el servidor: TODO 4)"
            )

            return

        print(
            "\nconsultar_notas('2026001') →",
            await by_name["consultar_notas"].run(
                {"codigo": "2026001"}
            ),
        )

        try:
            await by_name["consultar_notas"].run(
                {"codigo": "9999"}
            )

        except ToolExecutionError as exc:
            print(
                "consultar_notas('9999')    → error:",
                exc,
            )


if __name__ == "__main__":
    asyncio.run(_demo())