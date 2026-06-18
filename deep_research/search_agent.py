import requests as http_requests
from bs4 import BeautifulSoup
from agents import Agent, ModelSettings, function_tool
from vertex_client import vertex_flash_model


@function_tool
def search_web(query: str) -> str:
    """Search the web for the given query using DuckDuckGo and return the top results."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    try:
        url = f"https://html.duckduckgo.com/html/?q={http_requests.utils.quote(query)}"
        resp = http_requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result")[:6]:
            title   = r.select_one(".result__title")
            snippet = r.select_one(".result__snippet")
            if title and snippet:
                results.append(
                    f"• {title.get_text(strip=True)}\n  {snippet.get_text(strip=True)}"
                )
        return "\n\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search error: {e}"


INSTRUCTIONS = (
    "You are a research assistant. Given a search term, you search the web for that term and "
    "produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 "
    "words. Capture the main points. Write succintly, no need to have complete sentences or good "
    "grammar. This will be consumed by someone synthesizing a report, so its vital you capture the "
    "essence and ignore any fluff. Do not include any additional commentary other than the summary itself."
)

search_agent = Agent(
    name="Search agent",
    instructions=INSTRUCTIONS,
    tools=[search_web],
    model=vertex_flash_model,
    model_settings=ModelSettings(tool_choice="required"),
)