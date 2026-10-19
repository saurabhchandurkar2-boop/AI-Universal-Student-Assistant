import urllib.parse


def create_google_search_url(query):
    """
    Create a Google Search URL without using
    Google Search API or Google Cloud billing.
    """

    encoded_query = urllib.parse.quote_plus(query)

    return f"https://www.google.com/search?q={encoded_query}"


def is_live_query(query):
    """
    Detect questions that are likely to require
    current/live information.
    """

    live_keywords = [
        "latest",
        "today",
        "current",
        "now",
        "live",
        "price",
        "weather",
        "news",
        "recent",
        "stock price",
        "gold price",
        "silver price",
        "exchange rate",
        "score",
        "result",
        "results",
        "schedule",
        "2026"
    ]

    query_lower = query.lower()

    return any(
        keyword in query_lower
        for keyword in live_keywords
    )


if __name__ == "__main__":

    print()
    print("======================================")
    print("       GOOGLE SEARCH LINK TEST")
    print("======================================")
    print()

    query = input("Search: ").strip()

    if not query:
        print("No search query entered.")
    else:

        url = create_google_search_url(query)

        print()
        print("Google Search URL:")
        print(url)

        print()
        print("Live query:", is_live_query(query))