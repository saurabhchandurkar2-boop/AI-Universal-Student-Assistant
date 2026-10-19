import os
import requests


class WebSearch:

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        self.url = "https://www.googleapis.com/customsearch/v1"

    def available(self):

        return bool(
            self.api_key and
            self.search_engine_id
        )

    def search(self, query, num_results=5):

        if not self.available():
            print("Google Web Search is not configured.")
            return []

        try:

            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": min(num_results, 10),
                "safe": "active",
                "gl": "in",
                "hl": "en"
            }

            response = requests.get(
                self.url,
                params=params,
                timeout=15
            )

            # Show Google's actual response if there is an error
            if response.status_code != 200:

                print()
                print("======================================")
                print("       GOOGLE SEARCH ERROR")
                print("======================================")
                print("HTTP Status:", response.status_code)
                print("Google response:")
                print(response.text)
                print()

                return []

            data = response.json()

            results = []

            for item in data.get("items", []):

                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })

            return results

        except requests.exceptions.RequestException as error:

            print("Network error:", error)
            return []

        except Exception as error:

            print("Unexpected error:", error)
            return []

    def build_context(self, query, num_results=5):

        results = self.search(
            query,
            num_results=num_results
        )

        if not results:
            return ""

        context_parts = []

        for i, result in enumerate(results, 1):

            context_parts.append(
                f"Web Result {i}\n"
                f"Title: {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Summary: {result['snippet']}"
            )

        return "\n\n".join(context_parts)


if __name__ == "__main__":

    search = WebSearch()

    print()
    print("======================================")
    print("       GOOGLE WEB SEARCH TEST")
    print("======================================")

    print()
    print("API key configured:", bool(search.api_key))
    print("Search Engine ID configured:", bool(search.search_engine_id))
    print()

    if not search.available():

        print("Google Web Search is not configured.")

    else:

        query = input("Search: ")

        results = search.search(query)

        print()

        if not results:
            print("No search results returned.")
        else:

            print("Results found:", len(results))
            print()

            for result in results:

                print("Title:", result["title"])
                print("URL:", result["url"])
                print("Summary:", result["snippet"])
                print("-" * 60)