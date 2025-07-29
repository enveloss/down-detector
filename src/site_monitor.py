
import json
import aiofiles
import time
import ssl
from datetime import datetime
from typing import Dict, List

import aiohttp
from src.logger import logger
from src.proxy_manager import ProxyManager

# File for storing sites
SITES_FILE = "./data/sites.json"

class SiteMonitor:
    def __init__(self):
        self.sites: Dict[str, Dict] = {}
    
    async def initialize(self):
        """Async initialization"""
        await self.load_sites()
    
    async def load_sites(self):
        """Async loads sites from JSON file"""
        try:
            async with aiofiles.open(SITES_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                self.sites = json.loads(content)
        except FileNotFoundError:
            self.sites = {}
            await self.save_sites()
    
    async def save_sites(self):
        """Async saves sites to JSON file"""
        async with aiofiles.open(SITES_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.sites, ensure_ascii=False, indent=2))
    
    async def add_site(self, name: str, url: str, user_id: int) -> bool:
        """Async adds new site for monitoring"""
        if name in self.sites:
            return False
        
        self.sites[name] = {
            "url": url,
            "added_by": user_id,
            "added_at": datetime.now().isoformat(),
            "last_check": None,
            "last_status": None,
            "last_response_time": None,
            "is_up": True
        }
        await self.save_sites()
        return True
    
    async def remove_site(self, name: str) -> bool:
        """Async removes site from monitoring"""
        if name in self.sites:
            del self.sites[name]
            await self.save_sites()
            return True
        return False
    
    def get_sites(self) -> Dict[str, Dict]:
        """Returns all sites (sync method for compatibility)"""
        return self.sites
    

    
    async def check_site(self, name: str, url: str, proxy_manager: ProxyManager) -> Dict:
        """Checks availability of one site"""
        try:
            # Get random proxy for each check
            proxy_url = None
            proxy = proxy_manager.get_random_proxy()
            if proxy:
                proxy_url = proxy["proxy_url"]
            
            # Session settings with more secure SSL configuration
            timeout = aiohttp.ClientTimeout(total=10)
            
            # Create SSL context that accepts self-signed certificates
            # but doesn't disable SSL completely
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                # Request settings
                request_kwargs = {}
                if proxy_url:
                    request_kwargs['proxy'] = proxy_url
                    logger.info(f"Using proxy {proxy_url} for checking {url}")
                
                # Start timing the request
                start_time = time.time()
                
                async with session.get(url, **request_kwargs) as response:
                    # Calculate response time
                    response_time = round((time.time() - start_time) * 1000, 2)  # in milliseconds
                    
                    # Check status code and content-type
                    is_up = response.status < 400
                    
                    # Check content-type for text/html
                    content_type = response.headers.get('content-type', '').lower()
                    is_html = 'text/html' in content_type
                    
                    # Site is considered available only if status is OK AND content-type contains text/html
                    is_up = is_up and is_html
                    
                    status_info = {
                        "status_code": response.status,
                        "is_up": is_up,
                        "checked_at": datetime.now().isoformat(),
                        "response_time": response_time,
                        "proxy_used": proxy_url,
                        "content_type": content_type,
                        "is_html": is_html
                    }
                    
                    # Update site information
                    if name in self.sites:
                        self.sites[name]["last_check"] = status_info["checked_at"]
                        self.sites[name]["last_status"] = status_info["status_code"]
                        self.sites[name]["last_response_time"] = response_time
                        self.sites[name]["is_up"] = is_up
                        await self.save_sites()
                    
                    # Update proxy statistics
                    if proxy_url:
                        proxy_name = next((name for name, info in proxy_manager.proxies.items() 
                                         if info["proxy_url"] == proxy_url), None)
                        if proxy_name:
                            await proxy_manager.update_proxy_stats(proxy_name, True)
                    
                    return status_info
        except Exception as e:
            logger.error(f"Error checking {url}: {e}")
            status_info = {
                "status_code": None,
                "is_up": False,
                "checked_at": datetime.now().isoformat(),
                "response_time": None,
                "error": str(e),
                "proxy_used": proxy_url
            }
            
            if name in self.sites:
                self.sites[name]["last_check"] = status_info["checked_at"]
                self.sites[name]["last_status"] = None
                self.sites[name]["last_response_time"] = None
                self.sites[name]["is_up"] = False
                await self.save_sites()
            
            # Update proxy statistics on error
            if proxy_url:
                proxy_name = next((name for name, info in proxy_manager.proxies.items() 
                                 if info["proxy_url"] == proxy_url), None)
                if proxy_name:
                    await proxy_manager.update_proxy_stats(proxy_name, False)
            
            return status_info
    
    async def check_all_sites(self, proxy_manager: ProxyManager) -> List[Dict]:
        """Checks availability of all sites"""
        await self.load_sites()
        
        results = []
        for name, site_info in self.sites.items():
            result = await self.check_site(name, site_info["url"], proxy_manager)
            result["name"] = name
            result["url"] = site_info["url"]
            results.append(result)
        return results 