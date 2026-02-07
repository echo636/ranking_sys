"""
URL Fetch Service

提供 URL 自动抓取功能，用于批量对抗测试系统。
当候选项包含 URL 时，自动抓取网页内容并填充到 description 字段。
"""
import logging
from typing import List
from app.schemas.ranking import Candidate
from app.services.web_scraper import WebScraperService

logger = logging.getLogger("ranking_sys")


class URLFetchService:
    """
    URL 自动抓取服务
    
    检测候选项中的 URL 字段，自动抓取网页内容并填充描述。
    复用 WebScraperService 进行实际的网页抓取。
    """
    
    def __init__(self):
        self.scraper = WebScraperService()
    
    async def enrich_candidates_with_urls(
        self, 
        candidates: List[Candidate]
    ) -> List[Candidate]:
        """
        检查候选项列表，自动抓取包含 URL 的候选项内容
        
        Args:
            candidates: 候选项列表
            
        Returns:
            内容已填充的候选项列表
            
        逻辑：
            1. 遍历所有候选项
            2. 如果 info 包含 url 字段且 description 为空
            3. 使用 WebScraperService 抓取内容
            4. 将抓取的内容填充到 description
        """
        # 收集需要抓取的 URL
        urls_to_fetch = []
        url_indices = []
        
        for i, candidate in enumerate(candidates):
            if self._should_fetch_url(candidate):
                url = self._get_url_from_candidate(candidate)
                if url:
                    urls_to_fetch.append(url)
                    url_indices.append(i)
                    logger.info(f"检测到需要抓取的 URL: {url}")
        
        # 如果没有需要抓取的 URL，直接返回
        if not urls_to_fetch:
            logger.debug("没有检测到需要抓取的 URL")
            return candidates
        
        logger.info(f"开始抓取 {len(urls_to_fetch)} 个 URL...")
        
        # 并发抓取所有 URL
        results = await self.scraper.scrape_urls(urls_to_fetch)
        
        # 填充抓取的内容到候选项
        for idx, result in zip(url_indices, results):
            candidate = candidates[idx]
            
            if result['status'] == 'success':
                # 成功抓取：填充完整内容
                content = self._format_scraped_content(result)
                candidate.info.description = content
                logger.info(f"成功抓取并填充 {candidate.id}: {result['title']}")
                
            elif result['status'] == 'error':
                # 抓取失败：使用错误信息作为描述
                candidate.info.description = f"[URL 抓取失败] {result['content']}"
                logger.warning(f"抓取失败 {candidate.id}: {result['content']}")
                
            else:
                # 部分成功：使用提取的文本
                candidate.info.description = result.get('content', 'URL 内容无法完整提取')
                logger.warning(f"部分抓取 {candidate.id}")
        
        logger.info(f"URL 抓取完成，成功填充 {len(results)} 个候选项")
        return candidates
    
    def _should_fetch_url(self, candidate: Candidate) -> bool:
        """
        判断候选项是否需要抓取 URL
        
        条件：
        1. info 包含 url 属性
        2. url 不为空
        3. description 为空（避免覆盖已有内容）
        """
        info = candidate.info
        
        # 检查是否有 url 字段
        has_url = hasattr(info, 'url') and info.url
        
        # 检查 description 是否为空
        has_no_description = not (hasattr(info, 'description') and info.description)
        
        return has_url and has_no_description
    
    def _get_url_from_candidate(self, candidate: Candidate) -> str:
        """从候选项中提取 URL"""
        if hasattr(candidate.info, 'url'):
            return candidate.info.url
        return None
    
    def _format_scraped_content(self, scraped_data: dict) -> str:
        """
        格式化抓取的内容
        
        Args:
            scraped_data: WebScraperService 返回的数据字典
            
        Returns:
            格式化后的描述文本
        """
        parts = []
        
        # 添加标题
        if scraped_data.get('title'):
            parts.append(f"标题: {scraped_data['title']}")
        
        # 添加描述（如果有）
        if scraped_data.get('description'):
            parts.append(f"简介: {scraped_data['description']}")
        
        # 添加作者（如果有）
        if scraped_data.get('author'):
            parts.append(f"作者: {scraped_data['author']}")
        
        # 添加主要内容
        if scraped_data.get('content'):
            parts.append(f"\n内容:\n{scraped_data['content']}")
        
        # 添加 URL 引用
        parts.append(f"\n来源: {scraped_data['url']}")
        
        return "\n".join(parts)
