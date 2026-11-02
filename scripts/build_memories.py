"""Turn every not-yet-processed interaction into customer memories.

Run from the project root:  python -m scripts.build_memories
Safe to run again: it only processes interactions that failed or are new.
"""
from app.core.db import supabase
from app.services.memory import process_interaction


def main() -> None:
    result = (
        supabase.table("interactions")
        .select("id, customer_id, content, customers(name)")
        .eq("memory_extracted", False)
        .order("occurred_at")
        .execute()
    )
    pending = result.data or []
    if not pending:
        print("Nothing to do: every interaction has been processed.")
        return

    total_facts = failures = 0
    for number, row in enumerate(pending, start=1):
        name = row["customers"]["name"]
        try:
            saved = process_interaction(row["id"], row["customer_id"], name, row["content"])
            total_facts += saved
            print(f"[{number}/{len(pending)}] {name}: {saved} new facts")
        except Exception as exc:  # keep going; the failed one is retried next run
            failures += 1
            print(f"[{number}/{len(pending)}] {name}: FAILED ({exc.__class__.__name__}: {exc})")
    print(f"Done. {total_facts} facts saved, {failures} failures.")


if __name__ == "__main__":
    main()
