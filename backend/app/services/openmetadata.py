"""OpenMetadata API 封装"""
import httpx
from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger(__name__)
settings = get_settings()


class OpenMetadataClient:
    """OpenMetadata REST API 客户端"""

    def __init__(self):
        self.base_url = settings.om_base_url.rstrip("/")
        self.jwt_token = settings.om_jwt_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.jwt_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    @async_retry(max_retries=2, delay=2.0)
    async def list_tables(
        self, database: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict]:
        """列出表"""
        client = await self._get_client()
        params = {"limit": limit, "offset": offset}
        if database:
            params["database"] = database
        resp = await client.get("/v1/tables", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])

    @async_retry(max_retries=2, delay=2.0)
    async def get_table(self, fqn: str) -> dict:
        """获取单个表详情（含字段）"""
        client = await self._get_client()
        resp = await client.get(f"/v1/tables/name/{fqn}", params={"include": "columns"})
        resp.raise_for_status()
        return resp.json()

    @async_retry(max_retries=2, delay=2.0)
    async def patch_table(self, fqn: str, patch: list[dict]) -> dict:
        """JSON Patch 更新表元数据"""
        client = await self._get_client()
        resp = await client.patch(f"/v1/tables/name/{fqn}", json=patch)
        resp.raise_for_status()
        logger.info(f"Patched table: {fqn}")
        return resp.json()

    @async_retry(max_retries=2, delay=2.0)
    async def patch_column(self, table_fqn: str, column_name: str, patch: list[dict]) -> dict:
        """JSON Patch 更新字段元数据"""
        client = await self._get_client()
        resp = await client.patch(
            f"/v1/tables/name/{table_fqn}/columns/{column_name}", json=patch
        )
        resp.raise_for_status()
        logger.info(f"Patched column: {table_fqn}.{column_name}")
        return resp.json()

    async def sync_to_om(self, record) -> None:
        """将补全结果同步回 OpenMetadata"""
        result = record.completion_result
        entity_id = record.entity_id

        if record.entity_type == "table":
            patch = _build_table_patch(result)
            await self.patch_table(entity_id, patch)
        else:
            parts = entity_id.rsplit(".", 1)
            table_fqn = parts[0]
            column_name = parts[1]
            patch = _build_column_patch(result)
            await self.patch_column(table_fqn, column_name, patch)


def _build_table_patch(result: dict) -> list[dict]:
    """构建表的 JSON Patch"""
    patch = []
    if result.get("description"):
        patch.append({"op": "add", "path": "/description", "value": result["description"]})
    if result.get("display_name"):
        patch.append({"op": "add", "path": "/displayName", "value": result["display_name"]})
    if result.get("tags"):
        tag_labels = [{"tagFQN": t} for t in result["tags"]]
        patch.append({"op": "add", "path": "/tags", "value": tag_labels})
    return patch


def _build_column_patch(result: dict) -> list[dict]:
    """构建字段的 JSON Patch"""
    patch = []
    if result.get("description"):
        patch.append({"op": "add", "path": "/description", "value": result["description"]})
    if result.get("display_name"):
        patch.append({"op": "add", "path": "/displayName", "value": result["display_name"]})
    if result.get("tags"):
        tag_labels = [{"tagFQN": t} for t in result["tags"]]
        patch.append({"op": "add", "path": "/tags", "value": tag_labels})
    return patch
