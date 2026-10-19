
import time

import streamlit as st

from chatbot import StudentChatbot
from predictor import predict_marks
from google_search_link import create_google_search_url, is_live_query
from math_tools import (
    FORMULAS,
    format_number,
    safe_eval,
    solve,
    try_chat_calculation
)


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="AI Student Assistant",
    page_icon="🎓",
    layout="wide"
)

from ui_theme import apply_theme, render_hero

apply_theme()


# ==================================================
# LOAD CHATBOT
# ==================================================

@st.cache_resource
def load_chatbot():
    # First run: import the sample documents so the knowledge base
    # is not empty. Does nothing if documents already exist.
    try:
        from knowledge_loader import ensure_initial_knowledge
        ensure_initial_knowledge()
    except Exception as error:
        print(f"[Knowledge] Initial import skipped: {error}")

    return StudentChatbot()


from hosted import is_hosted, make_hosted_bot

if "hosted" not in st.session_state:
    st.session_state.hosted = is_hosted()

HOSTED = st.session_state.hosted

if HOSTED:
    # Public host: private per-visitor knowledge base, visitor's own keys.
    if "bot" not in st.session_state:
        st.session_state.bot, st.session_state.workspace = make_hosted_bot()
    bot = st.session_state.bot
    workspace = st.session_state.workspace
else:
    bot = load_chatbot()


# ==================================================
# SIDEBAR: ADD DOCUMENTS TO KNOWLEDGE BASE
# ==================================================

from knowledge_loader import (
    add_to_knowledge,
    list_documents,
    remove_document,
    read_document,
    SUPPORTED
)
import quiz
import study_helper
import wiki_search

if HOSTED:
    add_to_knowledge = workspace.add
    list_documents = workspace.list
    remove_document = workspace.remove
    read_document = workspace.read

with st.sidebar:

    if HOSTED:

        with st.expander("🔑 Connect your own keys", expanded=not bot.ai_engine.has_key()):

            st.caption(
                "This public demo has no built-in AI model. Paste a free Gemini key "
                "from aistudio.google.com. Keys stay in your browser session only "
                "and are never saved."
            )

            gemini_key = st.text_input(
                "Gemini API key", type="password", key="visitor_gemini_key"
            )
            tavily_key = st.text_input(
                "Tavily key (optional, for web search)", type="password",
                key="visitor_tavily_key"
            )

            bot.ai_engine.set_gemini_key(gemini_key)
            bot.web_search.api_key = (tavily_key or "").strip() or None

            if bot.ai_engine.has_key():
                st.success("Gemini connected")

        st.info(
            "Your documents are private to this session and are deleted "
            "when the app restarts.",
            icon="🔒"
        )

    st.header("📂 Knowledge base")

    uploaded_files = st.file_uploader(
        "Add PDF, Word, TXT or MD files",
        type=[ext.lstrip(".") for ext in sorted(SUPPORTED)],
        accept_multiple_files=True,
        key="knowledge_upload"
    )

    if uploaded_files and st.button(
        "📤 Add to knowledge base",
        key="add_knowledge",
        type="primary",
        use_container_width=True
    ):

        for uploaded in uploaded_files:

            bar = st.progress(0, text=f"Reading {uploaded.name}")

            def show_progress(done, total, _bar=bar, _name=uploaded.name):
                _bar.progress(
                    done / total,
                    text=f"Reading {_name}: page {done} of {total}"
                )

            try:

                result = add_to_knowledge(
                    uploaded.getvalue(),
                    uploaded.name,
                    progress=show_progress
                )

                bar.empty()

                st.success(f"Added: {uploaded.name}")

                if result.get("warning"):
                    st.warning(result["warning"])

            except Exception as error:

                bar.empty()

                st.error(f"{uploaded.name}: {error}")

        # Reload the chatbot's retriever so new
        # documents are used immediately.
        bot.knowledge.refresh_cache()

    documents = list_documents()

    bot.use_wikipedia = st.toggle(
        "📖 Use Wikipedia for topics not in my notes",
        value=True,
        key="use_wikipedia"
    )

    st.caption(f"{len(documents)} document(s) in the knowledge base")

    with st.expander("📄 Show documents"):

        for doc_name in documents:

            st.write(f"- {doc_name}")

    if documents:

        with st.expander("🗑️ Remove a document"):

            to_remove = st.selectbox(
                "Choose a document",
                documents,
                key="remove_choice"
            )

            if st.button("🗑️ Remove", key="remove_doc"):

                try:

                    remove_document(to_remove)

                    bot.knowledge.refresh_cache()

                    st.success(f"Removed: {to_remove}")

                    st.rerun()

                except Exception as error:

                    st.error(f"Could not remove: {error}")


# ==================================================
# TITLE
# ==================================================

render_hero(hosted=HOSTED)


# ==================================================
# TABS
# ==================================================

chat_tab, formulas_tab, marks_tab, notes_tab, quiz_tab, write_tab = st.tabs(
    [
        "💬 Chat",
        "🧮 Formulas",
        "📈 Marks",
        "📝 Summarizer",
        "🎯 Quiz",
        "✍️ Write & learn"
    ]
)


# ==================================================
# ANSWER DETAILS (timer + sources)
# ==================================================

def render_meta(meta):
    """Small line under an answer: time taken, origin, and notes used."""
    if not meta:
        return

    parts = [f"⏱ {meta.get('seconds', 0):.1f} s"]
    origin = meta.get("origin")
    sources = meta.get("sources") or []

    if origin == "calc":
        parts.append("🧮 Exact calculator")
    elif origin == "web":
        parts.append("🌐 Web search")
    elif origin == "wikipedia":
        parts.append("📖 Wikipedia")
    elif sources:
        parts.append(f"📚 {len(sources)} note(s) used")

    st.caption("  ·  ".join(parts))

    if sources and origin == "wikipedia":
        with st.expander("📖 Wikipedia pages used for this answer"):
            for source in sources:
                st.markdown(f"[{source['filename']}]({source['url']})")
                st.caption(source["snippet"] + "…")
    elif sources and origin == "notes":
        with st.expander("📚 Notes used for this answer"):
            for source in sources:
                st.markdown(f"**{source['filename']}**")
                st.caption(source["snippet"] + "…")


# ==================================================
# CHATBOT
# ==================================================

with chat_tab:

    st.header("💬 Chat")

    # --------------------------------------------------
    # CREATE CHAT HISTORY
    # --------------------------------------------------

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


    # --------------------------------------------------
    # DISPLAY PREVIOUS MESSAGES
    # --------------------------------------------------

    for message in st.session_state.chat_history:

        with st.chat_message(message["role"]):
            st.write(message["content"])
            render_meta(message.get("meta"))


    # --------------------------------------------------
    # CHAT INPUT
    # --------------------------------------------------

    user_message = st.chat_input(
        "Ask me anything about your studies..."
    )


    # --------------------------------------------------
    # FREE GOOGLE SEARCH OPTION
    # --------------------------------------------------

    if user_message and is_live_query(user_message):

        google_url = create_google_search_url(
            user_message
        )

        st.info(
            "This question may need live information.",
            icon="🌐"
        )

        st.link_button(
            "🔎 Search Google for the latest information",
            google_url
        )


    # --------------------------------------------------
    # PROCESS USER MESSAGE
    # --------------------------------------------------

    if user_message:

        # Show user message
        with st.chat_message("user"):
            st.write(user_message)


        # Save user message
        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": user_message
            }
        )


        # --------------------------------------------------
        # GENERATE AI RESPONSE
        # --------------------------------------------------

        with st.chat_message("assistant"):

            with st.spinner("Thinking..."):

                try:

                    # Plain calculations are answered exactly by the
                    # built-in calculator; everything else goes to the AI.
                    started = time.time()

                    calc_answer = try_chat_calculation(user_message)

                    if calc_answer:
                        response = calc_answer
                        meta = {
                            "seconds": time.time() - started,
                            "origin": "calc",
                            "sources": [],
                        }
                    else:
                        info = bot.ask_with_info(user_message)
                        response = info["answer"]
                        meta = info

                    # No details for failures or the "connect a key" notice.
                    if "No answer engine is connected" in str(response):
                        meta = None

                    if str(response).startswith("I was unable to generate"):
                        meta = None
                        response = (
                            str(response)
                            + "\n\nIs the llama-server window still running? "
                            "Start it and ask again."
                        )

                    st.write(response)
                    render_meta(meta)


                    # Save AI response
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": response,
                            "meta": meta
                        }
                    )


                except Exception as error:

                    st.error(
                        f"Error: {error}"
                    )


    # --------------------------------------------------
    # CLEAR CONVERSATION
    # --------------------------------------------------

    if st.button(
        "🗑️ Clear chat",
        key="clear_chat"
    ):

        st.session_state.chat_history = []

        bot.clear_conversation()

        st.rerun()


# ==================================================
# FORMULAS AND CALCULATOR
# ==================================================

with formulas_tab:

    st.header("🧮 Formulas and calculator")

    st.caption(
        "Results are calculated exactly with Python, "
        "not guessed by the AI model."
    )


    # --------------------------------------------------
    # CALCULATOR
    # --------------------------------------------------

    st.subheader("🔢 Calculator")

    expression = st.text_input(
        "Expression",
        placeholder="Example: (12 + 8) * 3 / 4, sqrt(144), 20% of 150",
        key="calc_expression"
    )

    if expression.strip():

        try:

            st.success(
                f"`{expression.strip()}` = "
                f"**{format_number(safe_eval(expression))}**"
            )

        except ValueError as error:

            st.error(str(error))

    st.caption(
        "Supports + - * / ^ ( ), sqrt, sin, cos, tan, sind, cosd, tand, "
        "ln, log, exp, factorial, pi and percentages. "
        "sin, cos and tan use radians; sind, cosd and tand use degrees."
    )


    # --------------------------------------------------
    # FORMULA SOLVER
    # --------------------------------------------------

    st.subheader("📐 Formula solver")

    formula_key = st.selectbox(
        "Formula",
        list(FORMULAS),
        format_func=lambda key: (
            f"{FORMULAS[key]['name']}  ({FORMULAS[key]['equation']})"
        ),
        key="formula_choice"
    )

    formula = FORMULAS[formula_key]

    unknown = st.selectbox(
        "Find",
        list(formula["solve"]),
        format_func=lambda var: formula["vars"][var],
        key=f"unknown_{formula_key}"
    )

    known_values = {}

    columns = st.columns(2)

    others = [v for v in formula["vars"] if v != unknown]

    for index, var in enumerate(others):

        with columns[index % 2]:

            known_values[var] = st.number_input(
                formula["vars"][var],
                value=formula.get("defaults", {}).get(var),
                format="%g",
                placeholder="Enter a value",
                key=f"{formula_key}_{unknown}_{var}"
            )

    if st.button(
        "🧮 Calculate",
        key="solve_formula",
        type="primary"
    ):

        try:

            answer = solve(formula_key, unknown, known_values)

            st.success(
                f"{unknown} = **{format_number(answer['value'])}**"
            )

            with st.expander("📋 Show working"):

                st.code("\n".join(answer["working"]), language=None)

        except ValueError as error:

            st.error(str(error))


# ==================================================
# MARKS PREDICTION
# ==================================================

with marks_tab:

    st.header(
        "📈 Marks prediction"
    )


    st.info(
        "This is an estimate from a small sample dataset. "
        "It is not a guarantee of your marks.",
        icon="ℹ️"
    )


    study_hours = st.number_input(
        "Study hours per day",
        min_value=0.0,
        max_value=24.0,
        value=6.0
    )


    attendance = st.number_input(
        "Attendance (%)",
        min_value=0.0,
        max_value=100.0,
        value=85.0
    )


    assignments = st.number_input(
        "Assignments completed",
        min_value=0.0,
        value=8.0
    )


    if st.button(
        "📈 Predict marks",
        key="prediction_button",
        type="primary"
    ):

        try:

            marks = predict_marks(
                study_hours,
                attendance,
                assignments
            )

            st.success(
                f"Predicted marks: {marks}"
            )


        except Exception as error:

            st.error(
                f"Error: {error}"
            )


# ==================================================
# NOTES SUMMARIZER
# ==================================================

with notes_tab:

    st.header(
        "📝 Notes summarizer"
    )


    notes = st.text_area(
        "Paste your study notes here:",
        height=300,
        placeholder="Paste your notes here..."
    )


    if st.button(
        "✨ Summarize notes",
        key="summary_button",
        type="primary"
    ):

        if notes.strip():

            with st.spinner(
                "Summarizing your notes..."
            ):

                try:

                    # ------------------------------------------
                    # LAZY IMPORT
                    #
                    # Summarizer model loads ONLY when
                    # the user actually uses this feature.
                    # ------------------------------------------

                    from summarize import summarize_text


                    summary = summarize_text(
                        notes,
                        ask=bot.ai_engine.simple_ask if HOSTED else None
                    )


                    st.subheader(
                        "Summary"
                    )


                    st.write(summary)


                except Exception as error:

                    st.error(
                        f"Error: {error}"
                    )


        else:

            st.warning(
                "Please enter your study notes first."
            )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "AI Universal Student Assistant: chat, formulas, marks prediction and notes summarizer"
)


# ==================================================
# QUIZ FROM YOUR NOTES
# ==================================================

with quiz_tab:

    st.header("🎯 Quiz from your notes")

    st.caption(
        "Pick a document and practise. Fill-in-the-blank questions are made "
        "straight from your notes, so they are instant and need no AI."
    )

    quiz_docs = list_documents()

    if not quiz_docs:

        st.info("Add a document in the sidebar first.", icon="📂")

    else:

        quiz_doc = st.selectbox(
            "Document",
            quiz_docs,
            key="quiz_doc"
        )

        quiz_count = st.slider(
            "Number of questions",
            3, 10, 5,
            key="quiz_count"
        )

        quiz_modes = [
            "Fill in the blank (instant)",
            "AI questions (slower)"
        ]

        quiz_mode = st.radio(
            "Question type",
            quiz_modes,
            horizontal=True,
            key="quiz_mode"
        )

        if st.button("🎯 Make quiz", key="make_quiz", type="primary"):

            try:

                text = read_document(quiz_doc)

                wants_ai = quiz_mode == quiz_modes[1]
                ask = None
                extra_note = ""

                if wants_ai:

                    if HOSTED:

                        if bot.ai_engine.has_key():
                            ask = bot.ai_engine.simple_ask
                        else:
                            extra_note = (
                                "Connect a Gemini key in the sidebar to use AI "
                                "questions. Showing fill-in-the-blank instead."
                            )

                    else:
                        ask = quiz.ask_llama_server

                with st.spinner("Making your quiz..."):

                    questions, note = quiz.make_quiz(
                        text,
                        quiz_count,
                        "ai" if ask else "blank",
                        ask=ask,
                        seed=time.time_ns()
                    )

                for key in [k for k in st.session_state.keys()
                            if str(k).startswith("quiz_answer_")]:
                    del st.session_state[key]

                st.session_state.quiz = {
                    "doc": quiz_doc,
                    "questions": questions,
                    "note": extra_note or note,
                    "checked": False
                }

            except Exception as error:

                st.error(f"Could not make a quiz: {error}")

        state = st.session_state.get("quiz")

        if state:

            if state["note"]:
                st.info(state["note"], icon="ℹ️")

            if state["questions"]:

                st.subheader(f"Questions from {state['doc']}")

                for number, item in enumerate(state["questions"]):

                    st.markdown(f"**{number + 1}.** {item['question']}")

                    st.text_input(
                        "Your answer",
                        key=f"quiz_answer_{number}",
                        label_visibility="collapsed",
                        placeholder="Type your answer"
                    )

                    if state["checked"]:

                        given = st.session_state.get(f"quiz_answer_{number}", "")

                        if item["kind"] == "qa":
                            st.caption(f"💡 Model answer: {item['answer']}")
                        elif quiz.check_blank(given, item["answer"], item["kind"]):
                            st.success("Correct", icon="✅")
                        else:
                            st.error(f"Answer: {item['answer']}", icon="❌")

                if st.button("✅ Check answers", key="check_quiz"):

                    state["checked"] = True
                    st.rerun()

                if state["checked"]:

                    gradable = [
                        (n, q) for n, q in enumerate(state["questions"])
                        if q["kind"] != "qa"
                    ]

                    if gradable:

                        correct = sum(
                            quiz.check_blank(
                                st.session_state.get(f"quiz_answer_{n}", ""),
                                q["answer"],
                                q["kind"]
                            )
                            for n, q in gradable
                        )

                        st.subheader(f"Score: {correct} / {len(gradable)}")


# ==================================================
# WRITE AND LEARN
# ==================================================

with write_tab:

    st.header("✍️ Write & learn")

    st.caption(
        "Get a topic explained, an essay or answer written, your own writing "
        "improved, or study notes made from text."
    )

    write_task = st.radio(
        "What do you need?",
        study_helper.TASKS,
        horizontal=True,
        key="write_task"
    )

    col_level, col_language, col_length = st.columns(3)

    with col_level:
        write_level = st.selectbox(
            "Level",
            list(study_helper.LEVELS.keys()),
            index=1,
            key="write_level"
        )

    with col_language:
        language_options = list(study_helper.LANGUAGES)
        if write_task == "Improve my writing":
            language_options = ["Same as my text"] + language_options
        write_language = st.selectbox(
            "Language",
            language_options,
            key="write_language"
        )

    with col_length:
        write_length = st.selectbox(
            "Length",
            list(study_helper.LENGTHS.keys()),
            index=1,
            key="write_length"
        )

    write_text = st.text_area(
        "Your text or topic",
        height=180,
        placeholder=study_helper.PLACEHOLDERS[write_task],
        key="write_text"
    )

    use_wiki_facts = False

    if write_task in ("Explain a topic", "Write an essay or answer"):
        use_wiki_facts = st.checkbox(
            "📖 Add facts from Wikipedia",
            value=True,
            key="write_wiki"
        )

    doc_text = ""

    if write_task == "Make study notes":

        write_docs = ["None"] + list_documents()

        write_doc = st.selectbox(
            "Or use one of your documents",
            write_docs,
            key="write_doc"
        )

        if write_doc != "None":
            try:
                doc_text = read_document(write_doc)
            except Exception as error:
                st.error(f"Could not read the document: {error}")

    if not HOSTED:
        st.caption(
            "Longer answers take more time on a CPU-only computer."
        )

    if st.button("✨ Generate", key="write_generate", type="primary"):

        source = (write_text or "").strip() or doc_text.strip()

        if HOSTED:
            writer_ask = (
                bot.ai_engine.simple_ask if bot.ai_engine.has_key() else None
            )
        else:
            writer_ask = quiz.ask_llama_server

        if not source:

            st.warning("Type or paste something first.", icon="✍️")

        elif writer_ask is None:

            st.warning(
                "Paste a free Gemini key in the sidebar to use this online.",
                icon="🔑"
            )

        else:

            try:

                started = time.time()
                facts = ""
                wiki_pages = []

                if use_wiki_facts and len(source) < 200:
                    wiki_pages = wiki_search.lookup(source)
                    facts = wiki_search.as_context(wiki_pages)

                with st.spinner("Writing..."):

                    written = study_helper.run(
                        write_task,
                        source,
                        write_level,
                        None if write_language == "Same as my text" else write_language,
                        write_length,
                        writer_ask,
                        facts=facts,
                        max_input_chars=8000 if HOSTED else 4000
                    )

                st.session_state.write_result = {
                    "text": written,
                    "task": write_task,
                    "seconds": time.time() - started,
                    "wiki": wiki_pages
                }

            except Exception as error:

                message = str(error)

                if "Connection" in message or "refused" in message:
                    message = (
                        "Cannot reach the local model. Is the llama-server "
                        "window still running?"
                    )

                st.error(f"Could not write: {message}")

    result = st.session_state.get("write_result")

    if result:

        st.subheader("Result")

        st.markdown(result["text"])

        caption = f"⏱ {result['seconds']:.1f} s"

        if result["wiki"]:
            caption += "  ·  📖 Wikipedia used"

        st.caption(caption)

        for page in result["wiki"]:
            st.markdown(f"[{page['title']}]({page['url']})")

        st.download_button(
            "⬇️ Download as text",
            data=result["text"],
            file_name="study_helper.txt",
            key="write_download"
        )
