"""
ActionFlow - Seed Policies
THY, Pegasus ve genel seyahat politikalari (Turkce & Ingilizce)

Kullanim:
    python -m app.scripts.seed_policies

    from app.scripts.seed_policies import seed_all_policies
    await seed_all_policies(db_session)
"""
import asyncio
import json
import logging
import pathlib
from typing import List, Dict, Any

logger = logging.getLogger("ActionFlow-SeedPolicies")

_DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "policies"
_POLICY_FILES = ["thy_policies.json", "pegasus_policies.json", "general_policies.json"]


def _load_raw() -> List[Dict[str, Any]]:
    all_policies = []
    for filename in _POLICY_FILES:
        path = _DATA_DIR / filename
        if not path.exists():
            logger.warning(f"Policy file not found: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            all_policies.extend(json.load(f))
    return all_policies


def get_all_policies() -> List[Dict[str, Any]]:
    result = []
    for p in _load_raw():
        result.append({
            "title": p["title"],
            "content": p["content"].strip(),
            "category": p["category"],
            "provider": p["provider"],
            "source_url": p.get("source_url"),
        })
        if "title_en" in p and "content_en" in p:
            result.append({
                "title": p["title_en"],
                "content": p["content_en"].strip(),
                "category": p["category"],
                "provider": p["provider"],
                "source_url": p.get("source_url"),
            })
    return result


async def seed_all_policies(db_session):
    from app.services.policy_service import PolicyService
    logger.info("Starting policy seeding...")
    service = PolicyService(db_session)
    policies = get_all_policies()
    created_ids = await service.bulk_create(policies)
    logger.info(f"Seeded {len(created_ids)} policies")
    return created_ids


async def main():
    from app.core.database import get_db_session
    policies = get_all_policies()
    print(f"Seeding {len(policies)} policies...")
    async with get_db_session() as db:
        ids = await seed_all_policies(db)
        print(f"Created {len(ids)} policies")


if __name__ == "__main__":
    asyncio.run(main())
