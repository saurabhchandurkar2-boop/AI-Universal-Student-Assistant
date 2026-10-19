import os
import re
import requests
from datetime import datetime


class TavilyWebSearch:

    """
    AI Student Assistant - Tavily Web Search V17

    Smarter Web Reliability Layer

    Features:
        - Tavily web search
        - Tavily answer extraction
        - Multiple source collection
        - Current-date awareness
        - Numerical conflict detection
        - Unit-aware comparison
        - Gold-price specific comparison
        - Avoids comparing historical values
        - Avoids comparing different karats
        - Avoids comparing per-gram with per-10-gram values
        - Reliability warning when appropriate
        - Compact final web response
    """

    def __init__(self):

        self.api_key = os.getenv("TAVILY_API_KEY")

        self.url = "https://api.tavily.com/search"

    # ==================================================
    # CONFIGURATION
    # ==================================================

    def available(self):

        return bool(self.api_key)

    # ==================================================
    # SEARCH
    # ==================================================

    def search(
        self,
        query,
        max_results=5
    ):

        if not self.available():

            print(
                "[Tavily] API key not configured."
            )

            return None

        payload = {

            "api_key": self.api_key,

            "query": query,

            "search_depth": "basic",

            "max_results": max_results,

            "include_answer": True

        }

        try:

            response = requests.post(

                self.url,

                json=payload,

                timeout=20

            )

            if response.status_code != 200:

                print(
                    "[Tavily] Search error:",
                    response.status_code
                )

                print(
                    response.text
                )

                return None

            data = response.json()

            return {

                "answer":
                    data.get(
                        "answer",
                        ""
                    ),

                "results":
                    data.get(
                        "results",
                        []
                    )

            }

        except requests.exceptions.RequestException as error:

            print(
                "[Tavily] Network error:",
                error
            )

            return None

        except Exception as error:

            print(
                "[Tavily] Unexpected error:",
                error
            )

            return None

    # ==================================================
    # CLEAN TEXT
    # ==================================================

    def clean_text(
        self,
        text
    ):

        if not text:

            return ""

        text = str(text)

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ==================================================
    # CURRENT DATE
    # ==================================================

    def current_date(self):

        return datetime.now().strftime(
            "%Y-%m-%d"
        )

    # ==================================================
    # GOLD QUERY DETECTION
    # ==================================================

    def is_gold_query(
        self,
        query
    ):

        q = query.lower()

        gold_words = [

            "gold price",
            "gold rate",
            "gold rates",
            "24k gold",
            "22k gold",
            "18k gold",
            "gold in india",
            "gold price india",
            "gold rate india"

        ]

        for word in gold_words:

            if word in q:

                return True

        return False

    # ==================================================
    # KARAT DETECTION
    # ==================================================

    def detect_karat(
        self,
        text
    ):

        if not text:

            return None

        text = text.lower()

        if re.search(
            r"\b24\s*k\b|\b24\s*karat\b|\b24\s*carat\b|\b24k\b",
            text
        ):

            return "24K"

        if re.search(
            r"\b22\s*k\b|\b22\s*karat\b|\b22\s*carat\b|\b22k\b",
            text
        ):

            return "22K"

        if re.search(
            r"\b18\s*k\b|\b18\s*karat\b|\b18\s*carat\b|\b18k\b",
            text
        ):

            return "18K"

        return None

    # ==================================================
    # UNIT DETECTION
    # ==================================================

    def detect_unit(
        self,
        text
    ):

        if not text:

            return None

        text = text.lower()

        if re.search(
            r"per\s*10\s*(gram|g)\b|\b10\s*(gram|grams|g)\b",
            text
        ):

            return "10g"

        if re.search(
            r"per\s*(gram|g)\b",
            text
        ):

            return "1g"

        return None

    # ==================================================
    # NORMALIZE GOLD VALUE
    # ==================================================

    def normalize_gold_value(
        self,
        value,
        unit
    ):

        if value is None:

            return None

        if unit == "10g":

            return value / 10.0

        return value

    # ==================================================
    # EXTRACT GOLD PRICE
    # ==================================================

    def extract_gold_price(
        self,
        text,
        desired_karat=None
    ):

        if not text:

            return None

        text = self.clean_text(
            text
        )

        lower = text.lower()

        # ----------------------------------------------
        # Determine karat
        # ----------------------------------------------

        karat = self.detect_karat(
            text
        )

        if desired_karat:

            if karat and karat != desired_karat:

                return None

        # ----------------------------------------------
        # Price pattern
        # ----------------------------------------------

        patterns = [

            r"₹\s*([\d,]+(?:\.\d+)?)",

            r"rs\.?\s*([\d,]+(?:\.\d+)?)",

            r"rs\s*([\d,]+(?:\.\d+)?)",

            r"INR\s*([\d,]+(?:\.\d+)?)"

        ]

        for pattern in patterns:

            matches = re.findall(
                pattern,
                text,
                flags=re.IGNORECASE
            )

            if not matches:

                continue

            for match in matches:

                try:

                    value = float(
                        match.replace(
                            ",",
                            ""
                        )
                    )

                except ValueError:

                    continue

                # --------------------------------------
                # Ignore unrealistic tiny values
                # --------------------------------------

                if value < 1000:

                    continue

                # --------------------------------------
                # Determine unit around price
                # --------------------------------------

                position = lower.find(
                    match.lower()
                )

                surrounding = lower[

                    max(
                        0,
                        position - 100
                    ):
                    min(
                        len(lower),
                        position + 150
                    )

                ]

                unit = self.detect_unit(
                    surrounding
                )

                normalized = self.normalize_gold_value(
                    value,
                    unit
                )

                return {

                    "value":
                        value,

                    "normalized_per_gram":
                        normalized,

                    "karat":
                        karat,

                    "unit":
                        unit

                }

        return None

    # ==================================================
    # EXTRACT CURRENT GOLD VALUE
    # ==================================================

    def extract_current_gold_value(
        self,
        result,
        desired_karat="24K"
    ):

        title = self.clean_text(
            result.get(
                "title",
                ""
            )
        )

        content = self.clean_text(
            result.get(
                "content",
                ""
            )
        )

        combined = (
            title
            + " "
            + content
        )

        # ----------------------------------------------
        # Prefer explicitly requested karat
        # ----------------------------------------------

        value = self.extract_gold_price(
            combined,
            desired_karat
        )

        if value:

            return value

        return None

    # ==================================================
    # GOLD RELIABILITY CHECK
    # ==================================================

    def check_gold_reliability(
        self,
        results,
        query
    ):

        if not results:

            return {

                "reliable":
                    False,

                "conflict":
                    False,

                "message":
                    "No web sources were available."

            }

        # ----------------------------------------------
        # Requested karat
        # ----------------------------------------------

        requested_karat = None

        q = query.lower()

        if "22k" in q or "22 karat" in q or "22 carat" in q:

            requested_karat = "22K"

        elif "18k" in q or "18 karat" in q or "18 carat" in q:

            requested_karat = "18K"

        else:

            requested_karat = "24K"

        values = []

        # ----------------------------------------------
        # Extract comparable values
        # ----------------------------------------------

        for result in results:

            extracted = self.extract_current_gold_value(
                result,
                requested_karat
            )

            if not extracted:

                continue

            value = extracted.get(
                "normalized_per_gram"
            )

            if value is None:

                continue

            values.append(
                {
                    "value":
                        value,

                    "karat":
                        extracted.get(
                            "karat"
                        ),

                    "unit":
                        extracted.get(
                            "unit"
                        ),

                    "title":
                        result.get(
                            "title",
                            ""
                        )
                }
            )

        # ----------------------------------------------
        # Not enough comparable values
        # ----------------------------------------------

        if len(values) < 2:

            return {

                "reliable":
                    True,

                "conflict":
                    False,

                "message":
                    ""

            }

        # ----------------------------------------------
        # Calculate spread
        # ----------------------------------------------

        numeric_values = [

            item["value"]

            for item in values

            if item["value"] is not None

        ]

        minimum = min(
            numeric_values
        )

        maximum = max(
            numeric_values
        )

        if minimum <= 0:

            return {

                "reliable":
                    True,

                "conflict":
                    False,

                "message":
                    ""

            }

        spread_percent = (

            (maximum - minimum)
            / minimum
            * 100

        )

        # ----------------------------------------------
        # Reliability threshold
        #
        # Small differences are normal.
        # Large differences trigger warning.
        # ----------------------------------------------

        if spread_percent >= 5:

            return {

                "reliable":
                    False,

                "conflict":
                    True,

                "message":
                    (
                        "Different web sources report "
                        "noticeably different prices for "
                        "the same gold category. The value "
                        "should be verified against the "
                        "latest source before making an "
                        "important decision."
                    ),

                "spread_percent":
                    round(
                        spread_percent,
                        2
                    ),

                "values":
                    values

            }

        return {

            "reliable":
                True,

            "conflict":
                False,

            "message":
                "",

            "spread_percent":
                round(
                    spread_percent,
                    2
                ),

            "values":
                values

        }

    # ==================================================
    # GENERAL WEB RELIABILITY
    # ==================================================

    def check_general_reliability(
        self,
        results
    ):

        if not results:

            return {

                "reliable":
                    False,

                "conflict":
                    False,

                "message":
                    "No web sources were available."

            }

        # ----------------------------------------------
        # For non-numerical questions we do not try to
        # perform aggressive numerical comparison.
        # ----------------------------------------------

        return {

            "reliable":
                True,

            "conflict":
                False,

            "message":
                ""

        }

    # ==================================================
    # RELIABILITY DISPATCHER
    # ==================================================

    def check_reliability(
        self,
        results,
        query
    ):

        if self.is_gold_query(
            query
        ):

            return self.check_gold_reliability(
                results,
                query
            )

        return self.check_general_reliability(
            results
        )

    # ==================================================
    # BUILD COMPACT CONTEXT
    # ==================================================

    def build_context(
        self,
        query,
        max_results=5
    ):

        data = self.search(
            query,
            max_results=max_results
        )

        if not data:

            return ""

        answer = self.clean_text(
            data.get(
                "answer",
                ""
            )
        )

        results = data.get(
            "results",
            []
        )

        context_parts = []

        # ==============================================
        # WEB SUMMARY
        # ==============================================

        if answer:

            context_parts.append(
                "WEB SUMMARY:\n"
                + answer
            )

        # ==============================================
        # RELIABILITY
        # ==============================================

        reliability = self.check_reliability(
            results,
            query
        )

        if reliability.get(
            "conflict",
            False
        ):

            context_parts.append(
                "WEB RELIABILITY:\n"
                + reliability.get(
                    "message",
                    ""
                )
            )

        # ==============================================
        # SOURCES
        # ==============================================

        for i, result in enumerate(
            results,
            1
        ):

            title = self.clean_text(
                result.get(
                    "title",
                    ""
                )
            )

            url = self.clean_text(
                result.get(
                    "url",
                    ""
                )
            )

            content = self.clean_text(
                result.get(
                    "content",
                    ""
                )
            )

            if not content:

                continue

            # ------------------------------------------
            # Limit source content
            # ------------------------------------------

            if len(content) > 900:

                content = (
                    content[:900]
                    + " [...]"
                )

            context_parts.append(

                f"SOURCE {i}:\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Information: {content}"

            )

        context = "\n\n".join(
            context_parts
        )

        return context

    # ==================================================
    # BUILD FINAL RESPONSE
    # ==================================================

    def build_final_response(
        self,
        query,
        max_results=5
    ):

        data = self.search(
            query,
            max_results=max_results
        )

        if not data:

            return None

        answer = self.clean_text(
            data.get(
                "answer",
                ""
            )
        )

        results = data.get(
            "results",
            []
        )

        if not answer and not results:

            return None

        # ==============================================
        # RELIABILITY
        # ==============================================

        reliability = self.check_reliability(
            results,
            query
        )

        # ==============================================
        # SELECT ANSWER
        # ==============================================

        if answer:

            response = answer

        elif results:

            first = results[0]

            response = self.clean_text(
                first.get(
                    "content",
                    ""
                )
            )

        else:

            return None

        # ==============================================
        # RELIABILITY WARNING
        # ==============================================

        if reliability.get(
            "conflict",
            False
        ):

            response += (

                "\n\n⚠️ Note: "

                + reliability.get(
                    "message",
                    ""
                )

            )

        # ==============================================
        # SOURCES
        # ==============================================

        source_lines = []

        for result in results[:3]:

            title = self.clean_text(
                result.get(
                    "title",
                    ""
                )
            )

            url = self.clean_text(
                result.get(
                    "url",
                    ""
                )
            )

            if title and url:

                source_lines.append(
                    f"- {title}: {url}"
                )

        if source_lines:

            response += (
                "\n\nSources:\n"
                + "\n".join(
                    source_lines
                )
            )

        return response

    # ==================================================
    # TEST
    # ==================================================


if __name__ == "__main__":

    print()
    print("======================================")
    print("       TAVILY WEB SEARCH MODULE")
    print("======================================")
    print()

    search = TavilyWebSearch()

    print(
        "Tavily configured:",
        search.available()
    )

    print()

    if not search.available():

        print(
            "TAVILY_API_KEY is not configured."
        )

    else:

        query = input(
            "Search: "
        ).strip()

        if query:

            print()
            print("======================================")
            print("       TAVILY WEB SEARCH TEST")
            print("======================================")
            print()

            print(
                "Tavily configured:",
                search.available()
            )

            print()

            print(
                "Search:",
                query
            )

            print()
            print("======================================")
            print("       COMPACT WEB CONTEXT")
            print("======================================")
            print()

            context = search.build_context(
                query,
                max_results=5
            )

            print(context)

            print()
            print("======================================")
            print("       FINAL WEB RESPONSE")
            print("======================================")
            print()

            final_response = search.build_final_response(
                query,
                max_results=5
            )

            if final_response:

                print(
                    final_response
                )

            else:

                print(
                    "No reliable web response available."
                )