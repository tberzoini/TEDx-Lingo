import os
import re
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from mcp.server.fastmcp import FastMCP

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "unibg_tedx_lingo")
MCP_PORT = int(os.getenv("MCP_PORT", "8443"))

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DB_NAME]

mcp = FastMCP("TEDx-Lingo-MCP Server", host="0.0.0.0", port=MCP_PORT)


@mcp.tool()
async def search_by_keyword(keyword: str, limit: int = 5) -> list[dict]:
    """Cerca talk TEDx per parola chiave nel titolo o nella descrizione."""
    regex = re.compile(re.escape(keyword), re.IGNORECASE)
    cursor = db.talks.find(
        {"$or": [{"title": regex}, {"description": regex}]},
        {"_id": 1, "title": 1, "speakers": 1, "duration": 1, "url": 1},
    ).limit(int(limit))
    return await cursor.to_list(length=int(limit))


@mcp.tool()
async def suggest_daily_practice(max_duration_sec: int = 600, limit: int = 3) -> list[dict]:
    """Suggerisce talk brevi con trascrizione, ideali per completare la Daily Streak di TEDx Lingo."""
    cursor = db.talks.find(
        {"transcript_info": {"$exists": True, "$ne": []}},
        {"_id": 1, "title": 1, "speakers": 1, "duration": 1, "url": 1},
    ).limit(200)
    results = []
    async for doc in cursor:
        try:
            dur = int(doc.get("duration", 0))
            if 0 < dur <= int(max_duration_sec):
                doc["duration_sec"] = dur
                results.append(doc)
                if len(results) >= int(limit):
                    break
        except (ValueError, TypeError):
            continue
    return results


@mcp.tool()
async def get_talk_transcript(talk_id: str, limit: int = 10) -> list[dict]:
    """Restituisce le prime frasi della trascrizione di un talk per creare esercizi o flashcard."""
    doc = await db.talks.find_one({"_id": str(talk_id)}, {"transcript_info": 1})
    if not doc:
        return []
    return (doc.get("transcript_info") or [])[: int(limit)]


@mcp.tool()
async def get_watch_next(talk_id: str) -> list[dict]:
    """Restituisce i video correlati (watch_next) suggeriti a partire da un talk."""
    doc = await db.talks.find_one({"_id": str(talk_id)}, {"watch_next": 1})
    if not doc:
        return []
    return doc.get("watch_next") or []


@mcp.tool()
async def get_user_flashcards(user_id: str) -> list[dict]:
    """Recupera il mazzo di flashcard salvate da un utente su TEDx Lingo per il ripasso."""
    cursor = db.flashcards.find({"user_id": user_id}).sort("created_at", -1)
    cards = []
    async for card in cursor:
        card["_id"] = str(card["_id"])
        cards.append(card)
    return cards


if __name__ == "__main__":
    cert_file = os.getenv("SSL_CERT_PATH")
    key_file = os.getenv("SSL_KEY_PATH")
    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        mcp.run(
            transport="streamable-http",
            ssl_certfile=cert_file,
            ssl_keyfile=key_file,
        )
    else:
        mcp.run(transport="streamable-http")
