"""
Streamlit Demo UI for GenshinRetrievalAgent.

Run with: streamlit run src/ui/streamlit_app.py
"""

import asyncio
import sys
from pathlib import Path

import streamlit as st

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import create_agent

# ============================================================================
# Configuration
# ============================================================================

DEMO_QUERIES = [
    "少女是如何重回世界的？",
    "努昂诺塔和少女是什么关系？",
    "玛薇卡的称号是什么？",
    "旅行者在纳塔经历了什么？",
]

TOOL_ICONS = {
    "lookup_knowledge": "📖",
    "find_connection": "🔗",
    "track_journey": "📅",
    "get_character_events": "⭐",
    "search_memory": "🔍",
}

# ============================================================================
# Async Helper
# ============================================================================


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================================================
# Session State Initialization
# ============================================================================


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "grading_history" not in st.session_state:
        st.session_state.grading_history = []


def get_agent():
    """Get or create the agent (lazy loading)."""
    if st.session_state.agent is None:
        with st.spinner("Initializing agent..."):
            st.session_state.agent = create_agent(
                session_id="streamlit_demo",
                verbose=False,
                enable_grader=True,
            )
    return st.session_state.agent


# ============================================================================
# UI Components
# ============================================================================


def render_sidebar():
    """Render sidebar with settings and example queries."""
    with st.sidebar:
        st.header("Settings")

        # Max retries slider
        max_retries = st.slider(
            "Max Retries",
            min_value=1,
            max_value=5,
            value=3,
            help="Maximum number of retry attempts for grading",
        )

        # Reset button
        if st.button("Reset Conversation", type="secondary"):
            st.session_state.messages = []
            st.session_state.grading_history = []
            if st.session_state.agent:
                st.session_state.agent.reset_context()
            st.rerun()

        st.divider()

        # Example queries
        st.subheader("Example Queries")
        for query in DEMO_QUERIES:
            if st.button(query, key=f"example_{query[:10]}"):
                return query, max_retries

    return None, max_retries


def render_tool_calls(tool_calls: list):
    """Render tool calls with icons and details."""
    if not tool_calls:
        return

    with st.expander(f"Thinking Process ({len(tool_calls)} tool calls)", expanded=False):
        for tc in tool_calls:
            tool_name = tc.get("tool", "unknown")
            kwargs = tc.get("kwargs", {})
            output = tc.get("output", "")

            icon = TOOL_ICONS.get(tool_name, "🔧")

            # Tool header
            st.markdown(f"**{icon} {tool_name}**")

            # Tool input (kwargs)
            if kwargs:
                kwargs_str = ", ".join(f'{k}="{v}"' for k, v in kwargs.items())
                st.code(kwargs_str, language=None)

            # Tool output (truncated)
            if output:
                truncated = output[:500] + "..." if len(output) > 500 else output
                st.text(truncated)

            st.divider()


def render_grading_panel(history: list):
    """Render the grading history panel."""
    if not history:
        return

    with st.expander("Grading Details", expanded=True):
        for item in history:
            attempt = item["attempt"]
            grade = item.get("grade", {})
            score = grade.get("score", 0)
            passed = item.get("passed", False)
            fail_reason = item.get("fail_reason", "")
            scores = grade.get("scores", {})
            tool_calls = item.get("tool_calls", [])

            # Attempt header with status
            if passed:
                st.success(f"**Attempt {attempt}**: {score}/100 - PASSED")
            else:
                reason_text = f" ({fail_reason})" if fail_reason else ""
                st.warning(f"**Attempt {attempt}**: {score}/100 - FAILED{reason_text}")

            # Tool calls (thinking process)
            if isinstance(tool_calls, list) and tool_calls:
                render_tool_calls(tool_calls)

            # Score breakdown
            cols = st.columns(4)
            with cols[0]:
                st.metric("Tool Usage", f"{scores.get('tool_usage', 0)}/25")
            with cols[1]:
                st.metric("Completeness", f"{scores.get('completeness', 0)}/25")
            with cols[2]:
                st.metric("Citation", f"{scores.get('citation', 0)}/25")
            with cols[3]:
                depth = scores.get("depth", 0)
                st.metric("Depth", f"{depth}/25", delta="PASS" if depth >= 10 else "FAIL")

            st.divider()


def render_tool_calls_summary(history: list):
    """Render a summary of tool calls from all attempts."""
    all_tools = []
    for item in history:
        tool_calls = item.get("tool_calls", [])
        # Handle both list (new) and int (old) formats
        tool_count = len(tool_calls) if isinstance(tool_calls, list) else tool_calls
        if tool_count > 0:
            all_tools.append(f"Attempt {item['attempt']}: {tool_count} tools")

    if all_tools:
        st.caption(f"Tool calls: {', '.join(all_tools)}")


def process_query(query: str, max_retries: int):
    """Process a query with the agent."""
    agent = get_agent()

    with st.status("Processing query...", expanded=True) as status:
        st.write(f"Query: {query}")
        st.write("Running agent with grading...")

        try:
            response, history = run_async(
                agent.chat_with_grading(query, max_retries=max_retries)
            )

            # Update status based on result
            final_passed = history[-1].get("passed", False) if history else False
            if final_passed:
                status.update(label="Completed!", state="complete")
            else:
                status.update(label="Completed (max retries reached)", state="error")

            return response, history

        except Exception as e:
            status.update(label="Error!", state="error")
            st.error(f"Error: {str(e)}")
            return None, []


# ============================================================================
# Main App
# ============================================================================


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Genshin Story QA",
        layout="wide",
    )

    # Initialize session state
    init_session_state()

    # Title
    st.title("Genshin Story QA Agent")
    st.caption("Ask questions about Genshin Impact story using Knowledge Graph + Vector Search")

    # Sidebar
    example_query, max_retries = render_sidebar()

    # Chat messages container
    chat_container = st.container()

    # Display chat history
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "grading_history" in msg:
                    render_grading_panel(msg["grading_history"])

    # Chat input
    user_input = st.chat_input("Ask a question about Genshin story...")

    # Handle input (from chat input or example button)
    query = example_query or user_input

    if query:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query})

        # Display user message
        with chat_container:
            with st.chat_message("user"):
                st.markdown(query)

        # Process query
        with chat_container:
            with st.chat_message("assistant"):
                response, history = process_query(query, max_retries)

                if response:
                    st.markdown(response)
                    render_grading_panel(history)
                    render_tool_calls_summary(history)

                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "grading_history": history,
                    })
                    st.session_state.grading_history = history


if __name__ == "__main__":
    main()
