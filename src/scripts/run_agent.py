#!/usr/bin/env python3
"""
Demo script for the Genshin Retrieval Agent.

Usage:
    # Single query
    python -m src.scripts.run_agent "Who is Mavuika?"

    # Interactive mode
    python -m src.scripts.run_agent --interactive

    # Verbose mode (shows tool calls)
    python -m src.scripts.run_agent --verbose "玛薇卡是谁？"
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )
    # Reduce noise from other libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


async def run_single_query(query: str, verbose: bool = False, grading: bool = False):
    """Run a single query against the agent."""
    from src.agent import create_agent

    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Mode: {'grading' if grading else 'verbose' if verbose else 'simple'}")
    print(f"{'='*60}\n")

    agent = create_agent(verbose=verbose, enable_grader=grading)

    if grading:
        response, history = await agent.chat_with_grading(query)
        print(f"\n{'='*60}")
        print("Grading History:")
        print(f"{'='*60}")
        for h in history:
            print(f"\n--- Attempt {h['attempt']} (limit={h['limit']}) ---")
            grade = h['grade']
            scores = grade.get('scores', {})
            print(f"  Question Type: {grade.get('question_type', '?')}")
            print(f"  Scores: tool={scores.get('tool_usage', 0)}, "
                  f"evidence={scores.get('evidence', 0)}, "
                  f"complete={scores.get('completeness', 0)}, "
                  f"cite={scores.get('citation', 0)}, "
                  f"depth={scores.get('depth', 0)}")
            print(f"  Total: {grade.get('score', 0)}/100")
            print(f"  Passed: {h.get('passed', False)}")
            if h.get('fail_reason'):
                print(f"  Fail Reason: {h['fail_reason']}")
            print(f"  Reason: {grade.get('reason', '')}")
            if grade.get('suggestion'):
                print(f"  Suggestion: {grade.get('suggestion')}")
    elif verbose:
        response = await agent.chat_verbose(query)
    else:
        response = await agent.chat(query)

    print(f"\n{'='*60}")
    print("Final Response:")
    print(f"{'='*60}")
    print(response)
    print()


async def run_interactive(verbose: bool = False):
    """Run an interactive chat session."""
    from src.agent import create_agent

    print("\n" + "="*60)
    print("Genshin Story QA - Interactive Mode")
    print("="*60)
    print("Type your questions about Genshin Impact story.")
    print("Commands:")
    print("  /reset  - Reset conversation context")
    print("  /quit   - Exit the session")
    print("="*60 + "\n")

    agent = create_agent(verbose=verbose)

    while True:
        try:
            query = input("\nYou: ").strip()

            if not query:
                continue

            if query.lower() in ["/quit", "/exit", "quit", "exit"]:
                print("Goodbye!")
                break

            if query.lower() == "/reset":
                agent.reset_context()
                print("[Context reset. Starting new conversation.]")
                continue

            print("\nAgent: ", end="", flush=True)

            if verbose:
                response = await agent.chat_verbose(query)
            else:
                response = await agent.chat(query)

            # Print response (might already be partially printed in verbose mode)
            if not verbose:
                print(response)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            if verbose:
                import traceback
                traceback.print_exc()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Genshin Story QA Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Single query
    python -m src.scripts.run_agent "Who is Mavuika?"
    python -m src.scripts.run_agent "玛薇卡是谁？"

    # Interactive mode
    python -m src.scripts.run_agent --interactive
    python -m src.scripts.run_agent -i

    # Verbose mode (shows tool calls)
    python -m src.scripts.run_agent --verbose "恰斯卡怎么认识旅行者？"

Test Scenarios:
    # Fact lookup (Graph: lookup_knowledge)
    "Who is Mavuika?"
    "玛薇卡的称号是什么？"

    # Connection finding (Graph: find_connection)
    "How does Kinich know Chasca?"
    "恰斯卡和旅行者有什么关系？"

    # Journey tracking (Graph: track_journey)
    "What is the Traveler's journey in Natlan?"
    "旅行者在纳塔的经历"

    # Story search (Vector: search_memory)
    "Describe the arena battle scene"
    "描述竞技场的战斗"
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Question to ask (omit for interactive mode)",
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show tool calls and intermediate results",
    )

    parser.add_argument(
        "-g", "--grading",
        action="store_true",
        help="Enable Hard Grader with retry (tests depth threshold)",
    )

    args = parser.parse_args()

    setup_logging(args.verbose or args.grading)

    if args.interactive or args.query is None:
        asyncio.run(run_interactive(args.verbose))
    else:
        asyncio.run(run_single_query(args.query, args.verbose, args.grading))


if __name__ == "__main__":
    main()
