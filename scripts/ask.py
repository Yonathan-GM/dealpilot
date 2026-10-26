"""Ask a question from the command line.

Examples (run from the project root):
  python -m scripts.ask "What is the minimum order for plastic pallets?"
  python -m scripts.ask "Is the stretch film UV stable?" --mode vector
"""
import argparse

from app.services.rag import answer_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask DealPilot a question.")
    parser.add_argument("question")
    parser.add_argument("--mode", choices=["hybrid", "vector", "keyword"], default="hybrid")
    parser.add_argument("-k", type=int, default=5, help="how many chunks to retrieve")
    args = parser.parse_args()

    result = answer_question(args.question, k=args.k, mode=args.mode)

    print("\nANSWER\n------")
    print(result.answer)
    print("\nSOURCES\n-------")
    for number, source in enumerate(result.sources, start=1):
        print(f"[{number}] {source['filename']} (chunk {source['chunk_index']}) score={source['score']:.4f}")


if __name__ == "__main__":
    main()
