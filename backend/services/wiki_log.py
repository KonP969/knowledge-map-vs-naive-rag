from datetime import datetime
from typing import Optional

from services.wiki_store import WikiStore


def append_log_entry(
    store: WikiStore,
    op: str,
    source_id: Optional[str],
    details: str,
    timestamp: Optional[datetime] = None,
) -> None:
    ts = timestamp or datetime.now()
    ts_fmt = ts.strftime("%Y-%m-%d %H:%M")
    src_part = f" | {source_id}" if source_id else ""
    line = f"## [{ts_fmt}] {op}{src_part} | {details}\n"

    log_path = store.root / "wiki" / "log.md"
    if not log_path.exists():
        log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)
