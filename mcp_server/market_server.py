from __future__ import annotations
import json
import os
from typing import Any

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "local_suppliers.json")


def _load_suppliers() -> list[dict]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def find_local_treatment(diagnosis: str, category: str, region: str) -> dict[str, Any]:

    suppliers = _load_suppliers()


    region_matches = [s for s in suppliers if s["region"].lower() == region.lower()]
    pool = region_matches if region_matches else suppliers  

    category_matches = [s for s in pool if s["category"] == category]
    if not category_matches:
        return {"options": []}

    diagnosis_lower = diagnosis.lower()
    ranked = sorted(
        category_matches,
        key=lambda s: (diagnosis_lower not in s["product"].lower()),
    )

    options = [
        {
            "supplier_name": s["supplier_name"],
            "product": s["product"],
            "approx_price": s["approx_price"],
            "distance_km": s["distance_km"],
            "region": s["region"],
        }
        for s in ranked[:3]
    ]
    return {"options": options}


def _build_mcp_app():

    from mcp.server.fastmcp import FastMCP

    app = FastMCP("fieldwise-market-server")
    app.tool()(find_local_treatment)
    return app


if __name__ == "__main__":

    mcp_app = _build_mcp_app()
    mcp_app.run()
