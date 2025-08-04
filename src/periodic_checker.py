import asyncio
from datetime import datetime
from src.logger import logger
from src.site_monitor import SiteMonitor
from src.proxy_manager import ProxyManager
from src import config
from aiogram import Bot

# Bot initialization for sending notifications
bot = Bot(token=config.BOT_TOKEN)

async def send_down_notification(site_name: str, url: str, error: str = None, proxy_used: str = None, status_code: int = None, content_type: str = None, expected_content_type: str = None, content_type_matches: bool = None):
    """Sends notification about site unavailability to REPORT_CHAT"""
    if not config.REPORT_CHAT_ID:
        logger.warning("REPORT_CHAT_ID not configured, notifications not sent")
        return
    
    try:
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        notification = f"🚨 <b>САЙТ НЕДОСТУПЕН!</b>\n\n"
        notification += f"📱 <b>Сайт:</b> {site_name}\n"
        notification += f"🔗 <b>URL:</b> {url}\n"
        notification += f"⏰ <b>Время:</b> {current_time}\n"
        
        if status_code:
            notification += f"📊 <b>Код ответа:</b> {status_code}\n"
        
        if proxy_used:
            notification += f"🌍 <b>Прокси:</b> {proxy_used}\n"
        
        if content_type and expected_content_type:
            content_type_status = "✅" if content_type_matches else "❌"
            notification += f"📄 <b>Тип контента:</b> {content_type_status}\n"
            notification += f"   • Фактический: {content_type}\n"
            notification += f"   • Ожидаемый: {expected_content_type}\n"
        
        if error:
            notification += f"❌ <b>Ошибка:</b> {error}\n"
        
        await bot.send_message(
            chat_id=config.REPORT_CHAT_ID,
            text=notification,
            parse_mode="HTML"
        )
        logger.info(f"Notification about {site_name} unavailability sent to REPORT_CHAT")
        
    except Exception as e:
        logger.error(f"Error sending notification to REPORT_CHAT: {e}")

async def send_up_notification(site_name: str, url: str, proxy_used: str = None, status_code: int = None, content_type: str = None, expected_content_type: str = None, content_type_matches: bool = None):
    """Sends notification about site recovery to REPORT_CHAT"""
    if not config.REPORT_CHAT_ID:
        logger.warning("REPORT_CHAT_ID not configured, notifications not sent")
        return
    
    try:
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        notification = f"✅ <b>САЙТ ВОССТАНОВЛЕН!</b>\n\n"
        notification += f"📱 <b>Сайт:</b> {site_name}\n"
        notification += f"🔗 <b>URL:</b> {url}\n"
        notification += f"⏰ <b>Время:</b> {current_time}\n"
        
        if status_code:
            notification += f"📊 <b>Код ответа:</b> {status_code}\n"
        
        if proxy_used:
            notification += f"🌍 <b>Прокси:</b> {proxy_used}\n"
        
        if content_type and expected_content_type:
            content_type_status = "✅" if content_type_matches else "❌"
            notification += f"📄 <b>Тип контента:</b> {content_type_status}\n"
            notification += f"   • Фактический: {content_type}\n"
            notification += f"   • Ожидаемый: {expected_content_type}\n"
        
        await bot.send_message(
            chat_id=config.REPORT_CHAT_ID,
            text=notification,
            parse_mode="HTML"
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
                            status_code=result.get('status_code'),
                            content_type=result.get('content_type'),
                            expected_content_type=result.get('expected_content_type'),
                            content_type_matches=result.get('content_type_matches')
                        )
                    elif current_status and not previous_status:
                        # Site recovered
                        await send_up_notification(
                            site_name=site_name,
                            url=result['url'],
                            proxy_used=result.get('proxy_used'),
                            status_code=result.get('status_code'),
                            content_type=result.get('content_type'),
                            expected_content_type=result.get('expected_content_type'),
                            content_type_matches=result.get('content_type_matches')
                        )
                
        except Exception as e:
            logger.error(f"Error during periodic checking: {e}")
        
        # Wait 5 minutes in production, 10 seconds in development
        sleep_time = 10 if config.MODE == "dev" else 300
        await asyncio.sleep(sleep_time) 