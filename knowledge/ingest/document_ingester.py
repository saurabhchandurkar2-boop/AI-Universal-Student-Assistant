import os
import re
import sys


class DocumentIngester:

    """
    AI Student Assistant
    Automatic Knowledge Pipeline V3

    SAFE MODE:
    Only scans:
        AI_Student_Assistant/documents_to_import

    Pipeline:
        documents_to_import
                ↓
        Document Ingester
                ↓
        knowledge/documents
                ↓
        Knowledge Manager
                ↓
        knowledge_index.txt
    """

    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".md",
        ".pdf"
    }

    def __init__(
        self,
        source_folder=None,
        knowledge_folder=None
    ):

        # =========================================
        # PROJECT ROOT
        # =========================================

        self.project_root = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        # =========================================
        # SAFE SOURCE FOLDER
        # =========================================

        if source_folder is None:

            source_folder = os.path.join(
                self.project_root,
                "documents_to_import"
            )

        # =========================================
        # KNOWLEDGE FOLDER
        # =========================================

        if knowledge_folder is None:

            knowledge_folder = os.path.join(
                self.project_root,
                "knowledge",
                "documents"
            )

        self.source_folder = os.path.abspath(
            source_folder
        )

        self.knowledge_folder = os.path.abspath(
            knowledge_folder
        )

    # =========================================
    # CREATE SOURCE FOLDER
    # =========================================

    def create_source_folder(self):

        os.makedirs(
            self.source_folder,
            exist_ok=True
        )

    # =========================================
    # CREATE KNOWLEDGE FOLDER
    # =========================================

    def create_knowledge_folder(self):

        os.makedirs(
            self.knowledge_folder,
            exist_ok=True
        )

    # =========================================
    # FIND FILES
    # =========================================

    def find_files(self):

        self.create_source_folder()

        files = []

        for root, _, filenames in os.walk(
            self.source_folder
        ):

            for filename in filenames:

                extension = os.path.splitext(
                    filename
                )[1].lower()

                if extension in self.SUPPORTED_EXTENSIONS:

                    filepath = os.path.join(
                        root,
                        filename
                    )

                    files.append(
                        os.path.abspath(filepath)
                    )

        files.sort()

        return files

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

        # Remove excessive spaces/tabs
        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # Remove excessive blank lines
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    # =========================================
    # READ TXT / MD
    # =========================================

    def read_text_file(
        self,
        filepath
    ):

        encodings = [
            "utf-8",
            "utf-8-sig",
            "cp1252"
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
                    f"  Text read error: {error}"
                )

                return ""

        print(
            "  Could not decode text file."
        )

        return ""

    # =========================================
    # READ PDF
    # =========================================

    def read_pdf_file(
        self,
        filepath
    ):

        try:

            from pypdf import PdfReader

        except ImportError:

            print(
                "  PDF support requires pypdf."
            )

            return ""

        try:

            reader = PdfReader(
                filepath
            )

            pages = []

            for page in reader.pages:

                try:

                    text = page.extract_text()

                except Exception:

                    text = ""

                if text:

                    pages.append(text)

            return "\n\n".join(
                pages
            )

        except Exception as error:

            print(
                f"  PDF read error: {error}"
            )

            return ""

    # =========================================
    # READ FILE
    # =========================================

    def read_file(
        self,
        filepath
    ):

        extension = os.path.splitext(
            filepath
        )[1].lower()

        if extension in {
            ".txt",
            ".md"
        }:

            return self.read_text_file(
                filepath
            )

        if extension == ".pdf":

            return self.read_pdf_file(
                filepath
            )

        return ""

    # =========================================
    # DESTINATION PATH
    # =========================================

    def destination_path(
        self,
        filepath
    ):

        filename = os.path.basename(
            filepath
        )

        relative_dir = os.path.relpath(
            os.path.dirname(filepath),
            self.source_folder
        )

        if relative_dir == ".":

            destination_dir = (
                self.knowledge_folder
            )

        else:

            destination_dir = os.path.join(
                self.knowledge_folder,
                relative_dir
            )

        os.makedirs(
            destination_dir,
            exist_ok=True
        )

        base_name = os.path.splitext(
            filename
        )[0]

        return os.path.join(
            destination_dir,
            base_name + ".txt"
        )

    # =========================================
    # IMPORT ONE FILE
    # =========================================

    def import_file(
        self,
        filepath
    ):

        text = self.read_file(
            filepath
        )

        text = self.clean_text(
            text
        )

        if not text:

            return False

        destination = self.destination_path(
            filepath
        )

        try:

            with open(
                destination,
                "w",
                encoding="utf-8"
            ) as file:

                file.write(text)

            return True

        except Exception as error:

            print(
                f"  Write error: {error}"
            )

            return False

    # =========================================
    # IMPORT ALL
    # =========================================

    def import_all(self):

        files = self.find_files()

        imported = 0
        failed = 0

        for number, filepath in enumerate(
            files,
            start=1
        ):

            filename = os.path.basename(
                filepath
            )

            print(
                f"[{number}/{len(files)}] Processing: "
                f"{filename}"
            )

            if self.import_file(
                filepath
            ):

                imported += 1

                print(
                    "  Imported successfully."
                )

            else:

                failed += 1

                print(
                    "  Import failed."
                )

        return {
            "found": len(files),
            "imported": imported,
            "failed": failed
        }

    # =========================================
    # AUTOMATIC RAG INDEX UPDATE
    # =========================================

    def update_rag_index(self):

        print()
        print(
            "======================================"
        )
        print(
            "       AUTOMATIC RAG INDEX UPDATE"
        )
        print(
            "======================================"
        )

        try:

            # -------------------------------------
            # Add PROJECT ROOT to Python path
            # -------------------------------------

            if self.project_root not in sys.path:

                sys.path.insert(
                    0,
                    self.project_root
                )

            # -------------------------------------
            # Import KnowledgeManager
            # -------------------------------------

            from knowledge.knowledge_manager import (
                KnowledgeManager
            )

            # -------------------------------------
            # Create manager
            # -------------------------------------

            manager = KnowledgeManager(
                documents_path=self.knowledge_folder
            )

            # -------------------------------------
            # Find documents
            # -------------------------------------

            documents = manager.find_documents()

            print(
                f"Documents found: {len(documents)}"
            )

            # -------------------------------------
            # Build index
            # -------------------------------------

            index = manager.build_index()

            print(
                f"Knowledge chunks created: "
                f"{len(index)}"
            )

            if not index:

                print(
                    "No knowledge chunks found."
                )

                return False

            # -------------------------------------
            # Save index
            # -------------------------------------

            saved = manager.save_index(
                index
            )

            if not saved:

                print(
                    "Knowledge index could not be saved."
                )

                return False

            print(
                "Knowledge index updated successfully."
            )

            return True

        except Exception as error:

            print(
                f"Knowledge index update failed:"
            )

            print(
                error
            )

            return False

    # =========================================
    # COMPLETE PIPELINE
    # =========================================

    def run_pipeline(self):

        print()
        print(
            "======================================"
        )
        print(
            "     AI STUDENT ASSISTANT"
        )
        print(
            "     AUTOMATIC KNOWLEDGE PIPELINE"
        )
        print(
            "======================================"
        )

        print()
        print(
            "SAFE MODE:"
        )
        print(
            "Only documents_to_import will be scanned."
        )

        print()
        print(
            "Source folder:"
        )
        print(
            self.source_folder
        )

        print()
        print(
            "Knowledge folder:"
        )
        print(
            self.knowledge_folder
        )

        # =====================================
        # FIND FILES
        # =====================================

        files = self.find_files()

        print()
        print(
            f"Supported files found: {len(files)}"
        )

        # =====================================
        # IMPORT
        # =====================================

        result = self.import_all()

        print()
        print(
            "======================================"
        )
        print(
            "        IMPORT SUMMARY"
        )
        print(
            "======================================"
        )

        print(
            f"Files found:     {result['found']}"
        )

        print(
            f"Files imported:  {result['imported']}"
        )

        print(
            f"Files failed:    {result['failed']}"
        )

        # =====================================
        # UPDATE RAG INDEX
        # =====================================

        index_success = False

        if result["imported"] > 0:

            index_success = (
                self.update_rag_index()
            )

        else:

            print()
            print(
                "No new documents were imported."
            )

            # Still rebuild index so the system
            # remains synchronized.

            index_success = (
                self.update_rag_index()
            )

        # =====================================
        # FINAL STATUS
        # =====================================

        print()
        print(
            "======================================"
        )
        print(
            "        PIPELINE STATUS"
        )
        print(
            "======================================"
        )

        if result["failed"] == 0:

            print(
                "Document import: SUCCESS"
            )

        else:

            print(
                "Document import: PARTIAL"
            )

        if index_success:

            print(
                "RAG index update: SUCCESS"
            )

        else:

            print(
                "RAG index update: FAILED"
            )

        print()

        return {
            "import": result,
            "index_success": index_success
        }


# =============================================
# DIRECT TEST
# =============================================

if __name__ == "__main__":

    ingester = DocumentIngester()

    ingester.run_pipeline()