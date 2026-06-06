"""重置 ES 中 entity_type=column 的数据和 fact_finance/dim_market 的补全状态"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from elasticsearch import Elasticsearch

from app.config import get_settings
from app.services.elasticsearch import INDEX_NAME, COLUMNS_INDEX

settings = get_settings()


def reset_es_columns():
    """删除 metadata_index 中 entity_type=column 的数据"""
    es = Elasticsearch(
        settings.es_host,
        basic_auth=(settings.es_user, settings.es_password),
    )

    count_resp = es.count(
        index=INDEX_NAME,
        body={"query": {"term": {"entity_type": "column"}}},
    )
    count = count_resp["count"]
    print(f"metadata_index 中 entity_type=column 的文档数: {count}")

    if count > 0:
        resp = es.delete_by_query(
            index=INDEX_NAME,
            body={"query": {"term": {"entity_type": "column"}}},
            refresh=True,
        )
        deleted = resp.get("deleted", 0)
        failures = resp.get("failures", [])
        print(f"已从 metadata_index 删除 {deleted} 条文档")
        if failures:
            print(f"失败: {failures}")
    else:
        print("没有需要删除的 column 文档")

    try:
        col_count = es.count(index=COLUMNS_INDEX)["count"]
        print(f"\nmetadata_columns 索引的文档数: {col_count}（未删除，如需删除请告知）")
    except Exception:
        print(f"\nmetadata_columns 索引不存在或无法访问")


async def reset_completion_status():
    """将 fact_finance 和 dim_market 的补全记录状态重置为未补全"""
    engine = create_async_engine(settings.database_url)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    entities = ["fact_finance", "dim_market"]

    async with AsyncSessionLocal() as session:
        for entity_name in entities:
            result = await session.execute(
                text(
                    "SELECT id, entity_id, entity_type, review_status, completion_result "
                    "FROM completion_records WHERE entity_id LIKE :pattern"
                ),
                {"pattern": f"%{entity_name}%"},
            )
            records = result.fetchall()
            print(f"\n=== {entity_name} ===")
            print(f"找到 {len(records)} 条补全记录:")

            if not records:
                print(f"  未找到 {entity_name} 相关的补全记录")
                continue

            for row in records:
                print(f"  id={row[0]}, entity_id={row[1]}, type={row[2]}, status={row[3]}")

            update_result = await session.execute(
                text(
                    "UPDATE completion_records "
                    "SET completion_result = NULL, "
                    "    quality_check = NULL, "
                    "    review_status = 'pending_review', "
                    "    reviewer = NULL, "
                    "    review_comment = NULL, "
                    "    reviewed_at = NULL, "
                    "    synced_to_om = FALSE, "
                    "    synced_at = NULL "
                    "WHERE entity_id LIKE :pattern"
                ),
                {"pattern": f"%{entity_name}%"},
            )
            print(f"  已重置 {update_result.rowcount} 条记录为未补全状态")

        await session.commit()
        print("\n数据库更新已提交")


async def main():
    print("=" * 60)
    print("1. 删除 ES metadata_index 中 entity_type=column 的数据")
    print("=" * 60)
    reset_es_columns()

    print("\n" + "=" * 60)
    print("2. 重置 fact_finance / dim_market 的补全状态")
    print("=" * 60)
    await reset_completion_status()

    print("\n完成!")


if __name__ == "__main__":
    asyncio.run(main())
