
import json
import aiohttp
import aiofiles
import ssl
from typing import Dict, List, Optional
from datetime import datetime
from src.logger import logger

# File for storing proxies
PROXIES_FILE = "./data/proxies.json"

class ProxyManager:
    def __init__(self):
        self.proxies: Dict[str, Dict] = {}
        # Initialization will be async
    
    async def initialize(self):
        """Async initialization"""
        await self.load_proxies()
    
    async def load_proxies(self):
        """Async loads proxies from JSON file"""
        try:
            async with aiofiles.open(PROXIES_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                self.proxies = json.loads(content)
        except FileNotFoundError:
            self.proxies = {}
            await self.save_proxies()
    
    async def save_proxies(self):
        """Async saves proxies to JSON file"""
        async with aiofiles.open(PROXIES_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.proxies, ensure_ascii=False, indent=2))
    
    async def add_proxy(self, name: str, proxy_url: str, country: str, user_id: int) -> bool:
        """Async adds new proxy"""
        if name in self.proxies:
            return False
        
        self.proxies[name] = {
            "proxy_url": proxy_url,
            "country": country,
            "added_by": user_id,
            "added_at": datetime.now().isoformat(),
            "last_used": None,
            "is_active": True,
            "success_count": 0,
            "fail_count": 0
        }
        await self.save_proxies()
        return True
    
    async def remove_proxy(self, name: str) -> bool:
        """Async removes proxy"""
        if name in self.proxies:
            del self.proxies[name]
            await self.save_proxies()
            return True
        return False
    
    def get_proxies(self) -> Dict[str, Dict]:
        """Returns all proxies (sync method for compatibility)"""
        return self.proxies
    
    def get_proxies_by_country(self, country: str) -> List[Dict]:
        """Returns proxies by country"""
        return [
            {"name": name, **proxy_info} 
            for name, proxy_info in self.proxies.items() 
            if proxy_info["country"].lower() == country.lower() and proxy_info["is_active"]
        ]
    
    def get_active_proxies(self) -> List[Dict]:
        """Returns active proxies"""
        return [
            {"name": name, **proxy_info} 
            for name, proxy_info in self.proxies.items() 
            if proxy_info["is_active"]
        ]
    
    async def update_proxy_stats(self, name: str, success: bool):
        """Async updates proxy statistics"""
        if name in self.proxies:
            self.proxies[name]["last_used"] = datetime.now().isoformat()
            if success:
                self.proxies[name]["success_count"] += 1
            else:
                self.proxies[name]["fail_count"] += 1
            await self.save_proxies()
    
    async def test_proxy(self, proxy_url: str) -> bool:
        """Tests proxy asynchronously"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)  # increase timeout
            
            # Create SSL context for working with proxy
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(
                    'https://api.ipify.org',  # use another service that supports HTTPS
                    proxy=proxy_url
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Error testing proxy {proxy_url}: {e}")
            return False
    
    def get_proxy_url(self, name: str) -> Optional[str]:
        """Returns proxy URL by name"""
        if name in self.proxies and self.proxies[name]["is_active"]:
            return self.proxies[name]["proxy_url"]
        return None
    
    def get_random_proxy(self) -> Optional[Dict]:
        """Returns random active proxy"""
        import random
        active_proxies = self.get_active_proxies()
        if active_proxies:
            return random.choice(active_proxies)
        return None
    
    def get_proxy_by_country(self, country: str) -> Optional[Dict]:
        """Returns random proxy from specified country"""
        import random
        country_proxies = self.get_proxies_by_country(country)
        if country_proxies:
            return random.choice(country_proxies)
        return None 