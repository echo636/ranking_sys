"""
Temporal Client 工具

提供 Temporal Client 的全局实例管理，供 FastAPI 端点使用。
"""

import logging
from typing import Optional

from temporalio.client import Client

from app.core.config import settings

logger = logging.getLogger("ranking_sys.temporal")

# 全局 Temporal Client（懒加载）
_temporal_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    """
    获取 Temporal Client 单例

    懒加载：首次调用时连接 Temporal Server。
    后续调用复用已有连接。
    """
    global _temporal_client
    if _temporal_client is None:
        logger.info(f"连接 Temporal Server: {settings.TEMPORAL_HOST}")
        _temporal_client = await Client.connect(
            settings.TEMPORAL_HOST,
            namespace=settings.TEMPORAL_NAMESPACE,
        )
        logger.info("Temporal Client 连接成功")
    return _temporal_client
