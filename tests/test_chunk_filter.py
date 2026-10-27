"""Tests for cover/contents filtering and PDF page numbers. Run: python tests/test_chunk_filter.py"""
import io
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import chunk_filter as cf  # noqa: E402
import knowledge_loader as kl  # noqa: E402

TOC = """Table of Contents
Chapter 1  Introduction ........ 1
Chapter 2  Motion in a straight line ........ 14
Chapter 3  Laws of motion ........ 32
Chapter 4  Work, energy and power ........ 51
"""

TOC_NO_DOTS = """Contents
1 Introduction 1
2 Kinematics 14
3 Newton's laws 32
4 Energy 51
5 Waves 70
"""

COPYRIGHT = """Physics for Class 11
Copyright (c) 2020 Example Publishers. All rights reserved.
ISBN 978-0-00-000000-0. First published 2020. Printed in India.
"""

REAL = (
    "Newton's second law states that the acceleration of an object is directly "
    "proportional to the net force acting on it and inversely proportional to its mass. "
    "In symbols, F = m a. A force of 10 N on a 2 kg trolley gives an acceleration of 5 m/s2."
)


def test_detects_contents_and_cover_pages():
    assert cf.is_low_value(TOC)
    assert cf.is_low_value(TOC_NO_DOTS)
    assert cf.is_low_value(COPYRIGHT)
    assert cf.is_low_value("   \n  ")


def test_keeps_real_explanations():
    assert not cf.is_low_value(REAL)
    assert not cf.is_low_value("Ohm's Law\nV = I R\nV = voltage in volts")
    # A real sentence that merely mentions contents is kept.
    assert not cf.is_low_value("The contents of a cell include the nucleus and the cytoplasm.")


def test_sample_notes_are_never_filtered():
    folder = os.path.join(ROOT, "documents_to_import")
    for name in os.listdir(folder):
        if not name.endswith(".txt"):
            continue
        text = open(os.path.join(folder, name), encoding="utf-8").read()
        for part in text.split("\n\n"):
            if len(part.split()) >= 6:
                assert not cf.is_low_value(part), (name, part[:60])


def test_filter_results_keeps_order_and_drops_junk():
    results = [
        {"filename": "a.txt", "text": TOC, "score": 9},
        {"filename": "a.txt", "text": REAL, "score": 8},
        {"filename": "b.txt", "text": COPYRIGHT, "score": 7},
    ]
    kept = cf.filter_results(results)
    assert [r["text"] for r in kept] == [REAL]
    assert cf.filter_results([]) == []
    assert cf.filter_results("not a list") == "not a list"


def test_contents_followed_by_real_text_keeps_the_real_text():
    mixed = TOC + REAL
    keep, cleaned = cf.clean_chunk(mixed)
    assert keep
    assert "........" not in cleaned and "Table of Contents" not in cleaned
    assert "Newton's second law" in cleaned
    result = cf.filter_results([{"filename": "a.txt", "text": mixed, "score": 5}])
    assert len(result) == 1 and result[0]["text"] == cleaned
    assert result[0] is not None and mixed != cleaned


def _make_pdf():
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 750, "Contents  Chapter 1 ........ 3")      # page 1
    pdf.showPage()
    pdf.showPage()                                                  # page 2 is blank (like a scanned page)
    pdf.drawString(72, 750, "Photosynthesis happens inside the chloroplasts of green plant cells.")  # page 3
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_page_numbers_follow_the_real_pdf_pages():
    sink = []
    name, out_name, payload, pages, warning = kl.convert_upload(_make_pdf(), "Book.pdf", page_sink=sink)
    assert pages == 3 and len(sink) == 3 and sink[1].strip() == ""

    with tempfile.TemporaryDirectory() as folder:
        txt = os.path.join(folder, name + ".txt")
        with open(txt, "wb") as f:
            f.write(payload)
        cf.write_page_index(folder, name, sink)

        chunk = "Photosynthesis happens inside the chloroplasts of green plant cells."
        assert cf.page_of(txt, chunk) == 3          # blank page 2 did not shift the number
        assert cf.page_of(txt, "Contents Chapter 1") == 1
        assert cf.page_of(txt, "A sentence that is nowhere in this book at all") is None

        cf.remove_page_index(folder, name)
        assert not os.path.exists(os.path.join(folder, name + cf.PAGE_INDEX_SUFFIX))


def test_old_documents_without_an_index_have_no_page():
    with tempfile.TemporaryDirectory() as folder:
        txt = os.path.join(folder, "old.txt")
        open(txt, "w").write(REAL)
        assert cf.page_of(txt, REAL) is None
        assert cf.page_of(None, REAL) is None


def test_chatbot_skips_contents_and_reports_the_page():
    import shutil
    from reportlab.pdfgen import canvas
    import hosted

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 750, "Table of Contents")
    for number, title in enumerate(["Xylem and phloem transport", "Xylem vessels in stems", "Xylem and water"]):
        pdf.drawString(72, 730 - 20 * number, f"{title} ........ {3 + 6 * number}")
    pdf.showPage()
    pdf.showPage()
    pdf.drawString(72, 750, "Xylem carries water and dissolved minerals upward from the roots to the leaves of the plant.")
    pdf.showPage()
    pdf.save()

    bot, workspace = hosted.make_hosted_bot()
    bot.use_wikipedia = False
    try:
        workspace.add(buffer.getvalue(), "Biology.pdf")
        bot.knowledge.refresh_cache()
        bot.get_knowledge("What does xylem carry?")
        assert bot.last_sources, "the real page should be found"
        first = bot.last_sources[0]
        assert first["filename"] == "Biology.txt" and first["page"] == 3
        assert "........" not in first["snippet"]
    finally:
        shutil.rmtree(workspace.dir, ignore_errors=True)


def test_hosted_workspace_saves_and_removes_page_index():
    import hosted

    workspace = hosted.Workspace()
    try:
        result = workspace.add(_make_pdf(), "Book.pdf")
        index = os.path.join(workspace.dir, "Book" + cf.PAGE_INDEX_SUFFIX)
        assert os.path.exists(index)
        assert "Book.pdf.txt" not in workspace.list()
        assert result["saved_as"] in workspace.list()
        assert workspace.remove(result["saved_as"])
        assert not os.path.exists(index)
    finally:
        import shutil
        shutil.rmtree(workspace.dir, ignore_errors=True)


if __name__ == "__main__":
    test_detects_contents_and_cover_pages()
    test_keeps_real_explanations()
    test_sample_notes_are_never_filtered()
    test_filter_results_keeps_order_and_drops_junk()
    test_contents_followed_by_real_text_keeps_the_real_text()
    test_page_numbers_follow_the_real_pdf_pages()
    test_old_documents_without_an_index_have_no_page()
    test_chatbot_skips_contents_and_reports_the_page()
    test_hosted_workspace_saves_and_removes_page_index()
    print("All chunk filter tests passed.")
