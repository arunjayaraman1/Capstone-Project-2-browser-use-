from dotenv import load_dotenv
from browser_use import Browser

from langchain_agent.tools import (
    OpenURLTool,
    ObserveDOMTool,
    ClickTool,
    TypeTool,
    ScrollTool,
)
from langchain_agent.agent import create_agent

load_dotenv()


def run(goal: str):
    session = Browser(headless=False)

    tools = [
        OpenURLTool(session),
        ObserveDOMTool(session),
        ClickTool(session),
        TypeTool(session),
        ScrollTool(session),
    ]

    agent = create_agent(tools)

    agent.invoke({"input": goal})


if __name__ == "__main__":
    run(
      """Go to https://www.amazon.in
    Search for "smart tv 32"
    Observe the search results page.
    Skip sponsored links.
    Find a first valid product link.
    Click the FIRST valid product title.
    Wait for the product detail page.
    Add the product to cart."""
    )
