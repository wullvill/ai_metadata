"""Import column data from design-ui/asset_detail.html into ES"""
import json, re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.elasticsearch import ensure_columns_index, index_columns, COLUMNS_INDEX, get_es_client

HTML_PATH = os.path.join(os.path.dirname(__file__), "../../design-ui/asset_detail.html")


def _js_to_json(js: str) -> str:
    """Convert JavaScript object literal to valid JSON by protecting strings first."""
    # Step 1: protect double-quoted strings so colons inside them are safe
    string_re = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"')
    strings: list[str] = []

    def protect(m: re.Match) -> str:
        strings.append(m.group(0))
        return f"\x00STRING_{len(strings) - 1}\x00"

    protected = string_re.sub(protect, js)

    # Step 2: quote unquoted keys (word chars followed by colon)
    protected = re.sub(r"(\w+):", r'"\1":', protected)

    # Step 3: remove trailing commas
    protected = re.sub(r",\s*]", "]", protected)
    protected = re.sub(r",\s*}", "}", protected)

    # Step 4: restore strings
    def restore(m: re.Match) -> str:
        return strings[int(m.group(1))]

    return re.sub(r"\x00STRING_(\d+)\x00", restore, protected)


def extract_assets(html: str) -> list[dict]:
    """Extract ASSETS array from HTML script tag"""
    match = re.search(r"const ASSETS = (\[[\s\S]*?\]);", html)
    if not match:
        raise ValueError("ASSETS array not found in HTML")
    js = match.group(1)
    js = _js_to_json(js)
    return json.loads(js)


def main():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    assets = extract_assets(html)

    es = get_es_client()
    if es.indices.exists(index=COLUMNS_INDEX):
        es.indices.delete(index=COLUMNS_INDEX)

    ensure_columns_index()

    total = 0
    for a in assets:
        entity_type = a.get("type", "")
        entity_id = a.get("id", "")
        columns = a.get("columns", [])
        if entity_type in ("表", "视图") and columns:
            index_columns(entity_id, columns)
            total += len(columns)
            print(f"  {entity_id}: {len(columns)} columns")

    print(f"\nTotal: {total} columns indexed")


if __name__ == "__main__":
    main()
