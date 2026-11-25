import asyncio
import os
import httpx
import ollama
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://localhost:8443/mcp")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")


async def run_agent(prompt: str) -> None:
    # Custom httpx client supporting self-signed SSL certificates on EC2
    def insecure_client_factory(**kwargs):
        return httpx.AsyncClient(verify=False, **kwargs)

    async with streamablehttp_client(
        MCP_SERVER_URL, httpx_client_factory=insecure_client_factory
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Connesso a TEDx-Lingo-MCP Server!")

            tools_response = await session.list_tools()
            ollama_tools = []
            for tool in tools_response.tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                })

            messages = [{"role": "user", "content": prompt}]
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                tools=ollama_tools,
            )

            if response.message.tool_calls:
                messages.append(response.message)
                for call in response.message.tool_calls:
                    fn_name = call.function.name
                    fn_args = call.function.arguments
                    print(f"-> Chiamata al tool MCP: {fn_name}({fn_args})")
                    tool_result = await session.call_tool(fn_name, fn_args)
                    result_text = "\n".join(
                        c.text for c in tool_result.content if hasattr(c, "text")
                    )
                    messages.append({
                        "role": "tool",
                        "content": result_text,
                    })

                final_response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
                print("\nRisposta di Ollama:\n" + final_response.message.content)
            else:
                print("\nRisposta di Ollama:\n" + response.message.content)


if __name__ == "__main__":
    sample_prompt = (
        "Suggeriscimi 3 talk brevi (sotto i 420 secondi) "
        "per completare la mia Daily Streak di oggi su TEDx Lingo."
    )
    asyncio.run(run_agent(sample_prompt))
