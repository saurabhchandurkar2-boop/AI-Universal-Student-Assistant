import os
import re


class KnowledgeManager:

    """
    AI Student Assistant
    Knowledge Manager V2

    Responsibilities:
        1. Find all imported educational documents.
        2. Read TXT/MD documents.
        3. Clean text.
        4. Split large documents into chunks.
        5. Build the RAG knowledge index.
        6. Save knowledge_index.txt.

    IMPORTANT:
        This class only works with the project's
        knowledge/documents folder.

        It does NOT scan the user's personal PC.
    """

    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".md"
    }

    def __init__(self, documents_path=None):

        # =========================================
        # PROJECT KNOWLEDGE DIRECTORY
        # =========================================

        if documents_path is None:

            documents_path = os.path.join(
                os.path.dirname(__file__),
                "documents"
            )

        self.documents_path = os.path.abspath(
            documents_path
        )

        # =========================================
        # INDEX FILE
        # =========================================

        self.index_file = os.path.join(
            os.path.dirname(__file__),
            "knowledge_index.txt"
        )

    # =========================================
    # FIND DOCUMENTS
    # =========================================

    def find_documents(self):

        documents = []

        if not os.path.exists(
            self.documents_path
        ):

            return documents

        for root, _, files in os.walk(
            self.documents_path
        ):

            for filename in files:

                extension = os.path.splitext(
                    filename
                )[1].lower()

                if extension in self.SUPPORTED_EXTENSIONS:

                    filepath = os.path.abspath(
                        os.path.join(
                            root,
                            filename
                        )
                    )

                    documents.append(
                        filepath
                    )

        documents.sort(
            key=lambda path: path.lower()
        )

        return documents

    # =========================================
    # READ DOCUMENT
    # =========================================

    def read_document(self, filepath):

        encodings = [
            "utf-8",
            "utf-8-sig",
            "cp1252",
            "latin-1"
        ]

        for encoding in encodings:

            try:

                with open(
                    filepath,
                    "r",
                    encoding=encoding
                ) as file:

                    return file.read()

            except UnicodeDecodeError:

                continue

            except Exception as error:

                print(
                    f"Read error: {error}"
                )

                return ""

        return ""

    # =========================================
    # CLEAN TEXT
    # =========================================

    def clean_text(self, text):

        if not text:

            return ""

        text = text.replace(
            "\r\n",
            "\n"
        )

        text = text.replace(
            "\r",
            "\n"
        )

        # Remove null characters

        text = text.replace(
            "\x00",
            ""
        )

        # Normalize spaces

        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # Reduce excessive blank lines

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    # =========================================
    # SPLIT INTO CHUNKS
    # =========================================

    def split_into_chunks(
        self,
        text,
        chunk_size=1200,
        overlap=200
    ):

        text = self.clean_text(
            text
        )

        if not text:

            return []

        if len(text) <= chunk_size:

            return [text]

        chunks = []

        start = 0
        text_length = len(text)

        while start < text_length:

            end = min(
                start + chunk_size,
                text_length
            )

            chunk = text[
                start:end
            ].strip()

            if chunk:

                chunks.append(
                    chunk
                )

            if end >= text_length:

                break

            start = max(
                end - overlap,
                start + 1
            )

        return chunks

    # =========================================
    # BUILD KNOWLEDGE INDEX
    # =========================================

    def build_index(self):

        documents = self.find_documents()

        index = []

        for filepath in documents:

            text = self.read_document(
                filepath
            )

            text = self.clean_text(
                text
            )

            if not text:

                continue

            chunks = self.split_into_chunks(
                text
            )

            relative_path = os.path.relpath(
                filepath,
                self.documents_path
            )

            # Normalize Windows paths

            relative_path = relative_path.replace(
                "\\",
                "/"
            )

            for number, chunk in enumerate(
                chunks,
                start=1
            ):

                index.append({

                    "source": relative_path,

                    "chunk_id": number,

                    "text": chunk

                })

        return index

    # =========================================
    # SAVE INDEX
    # =========================================

    def save_index(
        self,
        index,
        output_file=None
    ):

        if output_file is None:

            output_file = self.index_file

        try:

            with open(
                output_file,
                "w",
                encoding="utf-8"
            ) as file:

                for item in index:

                    file.write(
                        f"SOURCE: {item['source']}\n"
                    )

                    file.write(
                        f"CHUNK: {item['chunk_id']}\n"
                    )

                    file.write(
                        item["text"]
                    )

                    file.write(
                        "\n\n"
                        + "=" * 70
                        + "\n\n"
                    )

            return True

        except Exception as error:

            print(
                f"Index write error: {error}"
            )

            return False

    # =========================================
    # REBUILD INDEX
    # =========================================

    def rebuild_index(self):

        print()
        print(
            "======================================"
        )

        print(
            "       REBUILDING KNOWLEDGE INDEX"
        )

        print(
            "======================================"
        )

        documents = self.find_documents()

        print()
        print(
            f"Documents found: {len(documents)}"
        )

        index = self.build_index()

        print(
            f"Knowledge chunks created: {len(index)}"
        )

        if not index:

            print()
            print(
                "No knowledge chunks were created."
            )

            return False

        saved = self.save_index(
            index
        )

        if saved:

            print()
            print(
                "Knowledge index updated successfully."
            )

            print(
                f"Index file: {self.index_file}"
            )

            return True

        print()
        print(
            "Could not save knowledge index."
        )

        return False

    # =========================================
    # ADD DOCUMENTS + REBUILD
    # =========================================

    def refresh(self):

        """
        Refresh the complete RAG knowledge index.

        This should be called after documents have
        been imported into knowledge/documents.
        """

        return self.rebuild_index()

    # =========================================
    # MAIN TEST
    # =========================================

    def run(self):

        print()
        print(
            "======================================"
        )

        print(
            "       KNOWLEDGE MANAGER V2"
        )

        print(
            "======================================"
        )

        print()
        print(
            "Knowledge folder:"
        )

        print(
            self.documents_path
        )

        print()
        print(
            "Index file:"
        )

        print(
            self.index_file
        )

        print()
        print(
            "Supported formats:"
        )

        print(
            "TXT, MD"
        )

        print()

        success = self.rebuild_index()

        print()

        if success:

            print(
                "Knowledge management completed."
            )

        else:

            print(
                "Knowledge management failed."
            )

        print()


# =============================================
# DIRECT TEST
# =============================================

if __name__ == "__main__":

    manager = KnowledgeManager()

    manager.run()