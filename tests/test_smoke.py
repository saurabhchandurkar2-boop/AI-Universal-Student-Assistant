"""Basic checks. Run from the project folder:  python -m pytest tests -q
(or just: python tests/test_smoke.py)"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def test_predictor_range():
    from predictor import predict_marks
    low = predict_marks(1, 50, 3)
    high = predict_marks(9, 95, 10)
    assert 0 <= low <= 100 and 0 <= high <= 100
    assert high > low


def test_upload_and_remove(monkeypatch=None):
    import knowledge_loader as kl

    tmp = tempfile.mkdtemp()
    src, docs = os.path.join(tmp, "src"), os.path.join(tmp, "docs")
    os.makedirs(src); os.makedirs(docs)
    old = (kl.SOURCE_DIR, kl.DOCS_DIR)
    kl.SOURCE_DIR, kl.DOCS_DIR = src, docs
    try:
        from knowledge.ingest.document_ingester import DocumentIngester
        orig_init = DocumentIngester.__init__

        def patched(self, source_folder=None, knowledge_folder=None):
            orig_init(self, source_folder or src, knowledge_folder or docs)

        DocumentIngester.__init__ = patched
        try:
            res = kl.add_to_knowledge(b"Ohm's law: V = I R", "My Notes.txt")
            assert res["saved_as"] == "My_Notes.txt"
            assert "My_Notes.txt" in kl.list_documents()

            try:
                kl.add_to_knowledge(b"x", "bad.exe")
                assert False, "should reject .exe"
            except ValueError:
                pass

            assert kl.remove_document("My_Notes.txt") is True
            assert kl.list_documents() == []
            assert not os.path.exists(os.path.join(src, "My_Notes.txt"))
        finally:
            DocumentIngester.__init__ = orig_init
    finally:
        kl.SOURCE_DIR, kl.DOCS_DIR = old
        shutil.rmtree(tmp, ignore_errors=True)


def test_summarizer_chunking():
    import summarize
    text = ("A sentence about physics. " * 40 + "\n\n") * 10
    chunks = summarize._split_chunks(text)
    assert len(chunks) > 1
    assert all(len(c) <= summarize.CHUNK_CHARS + 1 for c in chunks)


def test_math_calculator():
    from math_tools import safe_eval, try_chat_calculation, solve
    assert safe_eval("(12 + 8) * 3 / 4") == 15
    assert safe_eval("2^3 + sqrt(16)") == 12
    assert abs(safe_eval("sind(30)") - 0.5) < 1e-9
    assert safe_eval("20% of 150") == 30
    assert "30" in try_chat_calculation("what is 15% of 200")
    assert try_chat_calculation("what is python") is None
    assert try_chat_calculation("what is 5") is None
    for bad in ("__import__('os')", "10 / 0", "2**99999"):
        try:
            safe_eval(bad)
            assert False, f"should reject {bad}"
        except ValueError:
            pass
    assert solve("ohms_law", "I", {"V": 10, "R": 5})["value"] == 2
    assert abs(solve("kinematics_v2", "v", {"u": 0, "a": 2, "s": 25})["value"] - 10) < 1e-9
    try:
        solve("ohms_law", "I", {"V": 10})
        assert False, "should ask for R"
    except ValueError:
        pass


def test_large_pdf():
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        print("reportlab not installed: skipping large PDF test")
        return
    import io
    import knowledge_loader as kl

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for page in range(1, 121):
        pdf.drawString(72, 750, f"Page {page}: KE = 1/2 x m x v^2 and F = m x a")
        pdf.showPage()
    pdf.save()

    steps = []
    text, total, with_text = kl._pdf_to_text(
        buffer.getvalue(), lambda done, count: steps.append((done, count))
    )
    assert total == 120 and with_text == 120
    assert steps[-1] == (120, 120) and len(steps) == 120
    assert "KE = 1/2" in text


if __name__ == "__main__":
    test_predictor_range()
    test_upload_and_remove()
    test_summarizer_chunking()
    test_math_calculator()
    test_large_pdf()
    print("All smoke tests passed.")
