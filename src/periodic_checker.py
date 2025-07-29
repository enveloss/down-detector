import asyncio
from datetime import datetime
from src.logger import logger
from src.site_monitor import SiteMonitor
from src.proxy_manager import ProxyManager
from src import config
from aiogram import Bot

# Bot initialization for sending notifications
bot = Bot(token=config.BOT_TOKEN)

async def send_down_notification(site_name: str, url: str, error: str = None, proxy_used: str = None, status_code: int = None):
    """Sends notification about site unavailability to REPORT_CHAT"""
    if not config.REPORT_CHAT_ID:
        logger.warning("REPORT_CHAT_ID not configured, notifications not sent")
        return
    
    try:
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        notification = f"🚨 **САЙТ НЕДОСТУПЕН!**\n\n"
        notification += f"📱 **Сайт:** {site_name}\n"
        notification += f"🔗 **URL:** {url}\n"
        notification += f"⏰ **Время:** {current_time}\n"
        
        if status_code:
            notification += f"📊 **Код ответа:** {status_code}\n"
        
        if proxy_used:
            notification += f"🌍 **Прокси:** {proxy_used}\n"
        
        if error:
            notification += f"❌ **Ошибка:** {error}\n"
        
        await bot.send_message(
            chat_id=config.REPORT_CHAT_ID,
            text=notification,
            parse_mode="Markdown"
        )
        logger.info(f"Notification about {site_name} unavailability sent to REPORT_CHAT")
        
    except Exception as e:
        logger.error(f"Error sending notification to REPORT_CHAT: {e}")

async def send_up_notification(site_name: str, url: str, proxy_used: str = None, status_code: int = None):
    """Sends notification about site recovery to REPORT_CHAT"""
    if not config.REPORT_CHAT_ID:
        logger.warning("REPORT_CHAT_ID not configured, notifications not sent")
        return
    
    try:
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        notification = f"✅ **САЙТ ВОССТАНОВЛЕН!**\n\n"
        notification += f"📱 **Сайт:** {site_name}\n"
        notification += f"🔗 **URL:** {url}\n"
        notification += f"⏰ **Время:** {current_time}\n"
        
        if status_code:
            notification += f"📊 **Код ответа:** {status_code}\n"
        
        if proxy_used:
            notification += f"🌍 **Прокси:** {proxy_used}\n"
        
        await bot.send_message(
            chat_id=config.REPORT_CHAT_ID,
            text=notification,
            parse_mode="Markdown"
        )
        logger.info(f"Notification about {site_name} recovery sent to REPORT_CHAT")
        
    except Exception as e:
        logger.error(f"Error sending notification to REPORT_CHAT: {e}")

async def periodic_check(site_monitor: SiteMonitor, proxy_manager: ProxyManager):
    """Periodic site checking every 5 minutes"""
    while True:
        try:
            # Reload sites from file on each iteration
            await site_monitor.load_sites()
            await proxy_manager.load_proxies()

            sites = site_monitor.get_sites()

            if sites:
                logger.info("Performing periodic site checking...")
                results = await site_monitor.check_all_sites(proxy_manager)
                
                # Log results and send notifications
                for result in results:
                    site_name = result['name']
                    current_status = result["is_up"]
                    previous_status = sites[site_name].get("is_up", True)
                    
                    status = "🟢 Available" if current_status else "🔴 Unavailable"
                    logger.info(f"{site_name}: {status}")
                    
                    # Send notifications on status change
                    if not current_status and previous_status:
                        # Site became unavailable
                        await send_down_notification(
                            site_name=site_name,
                            url=result['url'],
                            error=result.get('error'),
                            proxy_used=result.get('proxy_used'),
                            status_code=result.get('status_code')
                        )
                    elif current_status and not previous_status:
                        # Site recovered
                        await send_up_notification(
                            site_name=site_name,
                            url=result['url'],
                            proxy_used=result.get('proxy_used'),
                            status_code=result.get('status_code')
                        )
                
        except Exception as e:
            logger.error(f"Error during periodic checking: {e}")
        
        # Wait 5 minutes in production, 10 seconds in development
        sleep_time = 10 if config.MODE == "dev" else 300
        await asyncio.sleep(sleep_time) 