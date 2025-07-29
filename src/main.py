import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message

from src import config
from src.site_monitor import SiteMonitor
from src.proxy_manager import ProxyManager
from src.periodic_checker import periodic_check
from src.logger import logger

class AdminFilter(BaseFilter):
    """Filter for checking administrator access"""
    
    async def __call__(self, message: Message) -> bool:
        return str(message.from_user.id) in config.ADMINS

# Create filter instance
admin_filter = AdminFilter()

def get_speed_info(response_time: float) -> tuple[str, str]:
    """Returns emoji and description of response speed"""
    if response_time is None:
        return "❓", "unknown"
    elif response_time < 200:
        return "⚡", "very fast"
    elif response_time < 500:
        return "🟢", "fast"
    elif response_time < 1000:
        return "🟡", "medium"
    elif response_time < 3000:
        return "🟠", "slow"
    else:
        return "🔴", "very slow"

# Bot and dispatcher initialization
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

dp.message.filter(admin_filter)

# Create monitor instances
site_monitor = SiteMonitor()
proxy_manager = ProxyManager()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Command /start"""
    welcome_text = """
🤖 **DOWN DETECTOR**

**Доступные команды:**
• `/add <название> <url>` - добавить сайт для мониторинга
• `/remove <название>` - удалить сайт из мониторинга
• `/list` - показать все отслеживаемые сайты
• `/check` - проверить все сайты сейчас
• `/status` - показать статус всех сайтов

**Команды для прокси:**
• `/proxy_add <название> <url> <страна>` - добавить прокси
• `/proxy_remove <название>` - удалить прокси
• `/proxy_list` - показать все прокси
• `/proxy_test <название>` - протестировать прокси

**Примеры:**
• `/add google https://google.com`
• `/proxy_add us_proxy http://proxy.example.com:8080 us`
• `/remove google`
    """
    
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("add"))
async def cmd_add_site(message: Message):
    """Command for adding a site"""
    try:
        # Parse command: /add name url
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("❌ Неправильный формат команды!\n\nИспользуйте: `/add <название> <url>`\n\nПример: `/add google https://google.com`", parse_mode="Markdown")
            return
        
        name = parts[1].lower()
        url = parts[2]
        
        # Check URL format
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Add site
        if await site_monitor.add_site(name, url, message.from_user.id):
            response_text = f"✅ Сайт **{name}** успешно добавлен для мониторинга!\n\nURL: {url}\n🔄 При каждой проверке будет использоваться случайный прокси"
            await message.answer(response_text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ Сайт с названием **{name}** уже существует!", parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Error adding site: {e}")
        await message.answer("❌ Произошла ошибка при добавлении сайта")

@dp.message(Command("remove"))
async def cmd_remove_site(message: Message):
    """Command for removing a site"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("❌ Неправильный формат команды!\n\nИспользуйте: `/remove <название>`\n\nПример: `/remove google`", parse_mode="Markdown")
            return
        
        name = parts[1].lower()
        
        if await site_monitor.remove_site(name):
            await message.answer(f"✅ Сайт **{name}** удален из мониторинга!", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Сайт с названием **{name}** не найден!", parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Error removing site: {e}")
        await message.answer("❌ Произошла ошибка при удалении сайта")

@dp.message(Command("list"))
async def cmd_list_sites(message: Message):
    """Command for showing list of sites"""
    sites = site_monitor.get_sites()
    
    if not sites:
        await message.answer("📝 Список отслеживаемых сайтов пуст.\n\nДобавьте первый сайт командой `/add <название> <url>`", parse_mode="Markdown")
        return
    
    sites_text = "📝 **Отслеживаемые сайты:**\n\n"
    for name, info in sites.items():
        status_emoji = "🟢" if info.get("is_up", True) else "🔴"
        last_check = info.get("last_check")
        if last_check != None:
            last_check = datetime.fromisoformat(last_check).strftime("%d.%m.%Y %H:%M")
        
        sites_text += f"{status_emoji} **{name}**\n"
        sites_text += f"   URL: {info['url']}\n"
        sites_text += f"   Последняя проверка: {last_check}\n"
        
        # Add response time if available
        last_response_time = info.get("last_response_time")
        if last_response_time is not None:
            speed_emoji, speed_desc = get_speed_info(last_response_time)
            sites_text += f"   ⏱️ Время отклика: {speed_emoji} {last_response_time} мс ({speed_desc})\n"
        
        sites_text += "\n"
    
    await message.answer(sites_text, parse_mode="Markdown")

@dp.message(Command("check"))
async def cmd_check_sites(message: Message):
    """Command for checking all sites"""
    sites = site_monitor.get_sites()
    
    if not sites:
        await message.answer("📝 Нет сайтов для проверки.\n\nДобавьте сайты командой `/add <название> <url>`", parse_mode="Markdown")
        return
    
    # Send message about start of checking
    status_msg = await message.answer("🔍 Checking site availability...")
    
    # Check all sites
    results = await site_monitor.check_all_sites(proxy_manager)
    
    # Form report
    report = "📊 **Site check results:**\n\n"
    
    for result in results:
        status_emoji = "🟢" if result["is_up"] else "🔴"
        status_text = "Available" if result["is_up"] else "Unavailable"
        
        report += f"{status_emoji} **{result['name']}**\n"
        report += f"   URL: {result['url']}\n"
        report += f"   Статус: {status_text}\n"
        
        # Add response time with speed emoji
        if result.get("response_time") is not None:
            speed_emoji, speed_desc = get_speed_info(result['response_time'])
            report += f"   ⏱️ Время отклика: {speed_emoji} {result['response_time']} мс ({speed_desc})\n"
        else:
            report += f"   ⏱️ Время отклика: ❓ N/A\n"
        
        # Add proxy information
        if result.get("proxy_used"):
            report += f"   🌍 Прокси: {result['proxy_used']}\n"
        
        if result.get("status_code"):
            report += f"   Код ответа: {result['status_code']}\n"
        elif result.get("error"):
            report += f"   Ошибка: {result['error']}\n"
        
        report += "\n"
    
    # Update message with results
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=status_msg.message_id,
        text=report,
        parse_mode="Markdown"
    )

@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Command for showing current status of all sites"""
    sites = site_monitor.get_sites()
    
    if not sites:
        await message.answer("📝 Нет отслеживаемых сайтов.\n\nДобавьте сайты командой `/add <название> <url>`", parse_mode="Markdown")
        return
    
    status_text = "📊 **Текущий статус сайтов:**\n\n"
    
    for name, info in sites.items():
        status_emoji = "🟢" if info.get("is_up", True) else "🔴"
        status_text += f"{status_emoji} **{name}**\n"
        status_text += f"   URL: {info['url']}\n"
        
        last_check = info.get("last_check")
        if last_check:
            last_check_dt = datetime.fromisoformat(last_check)
            status_text += f"   Последняя проверка: {last_check_dt.strftime('%d.%m.%Y %H:%M')}\n"
        
        last_status = info.get("last_status")
        if last_status is not None:
            status_text += f"   Последний код ответа: {last_status}\n"
        
        last_response_time = info.get("last_response_time")
        if last_response_time is not None:
            speed_emoji, speed_desc = get_speed_info(last_response_time)
            status_text += f"   ⏱️ Последнее время отклика: {speed_emoji} {last_response_time} мс ({speed_desc})\n"
        
        status_text += "\n"
    
    await message.answer(status_text, parse_mode="Markdown")

# Commands for proxy management
@dp.message(Command("proxy_add"))
async def cmd_add_proxy(message: Message):
    """Command for adding proxy"""
    try:
        # Parse command: /proxy_add name url country
        parts = message.text.split(maxsplit=3)
        if len(parts) < 4:
            await message.answer("❌ Неправильный формат команды!\n\nИспользуйте: `/proxy_add <название> <url> <страна>`\n\nПример: `/proxy_add us_proxy http://proxy.example.com:8080 us`", parse_mode="Markdown")
            return
        
        name = parts[1].lower()
        proxy_url = parts[2]
        country = parts[3].lower()
        
        # Check proxy URL format
        if not proxy_url.startswith(('http://', 'https://', 'socks5://')):
            proxy_url = 'http://' + proxy_url
        
        # Add proxy
        if await proxy_manager.add_proxy(name, proxy_url, country, message.from_user.id):
            await message.answer(f"✅ Прокси **{name}** успешно добавлен!\n\nURL: {proxy_url}\n🌍 Страна: {country.upper()}", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Прокси с названием **{name}** уже существует!", parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Error adding proxy: {e}")
        await message.answer("❌ Произошла ошибка при добавлении прокси")


@dp.message(Command("proxy_remove"))
async def cmd_remove_proxy(message: Message):
    """Command for removing proxy"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("❌ Неправильный формат команды!\n\nИспользуйте: `/proxy_remove <название>`\n\nПример: `/proxy_remove us_proxy`", parse_mode="Markdown")
            return
        
        name = parts[1].lower()
        
        if await proxy_manager.remove_proxy(name):
            await message.answer(f"✅ Прокси **{name}** удален!", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Прокси с названием **{name}** не найден!", parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Error removing proxy: {e}")
        await message.answer("❌ Произошла ошибка при удалении прокси")


@dp.message(Command("proxy_list"))
async def cmd_list_proxies(message: Message):
    """Command for showing list of proxies"""
    proxies = proxy_manager.get_proxies()
    
    if not proxies:
        await message.answer("📝 Список прокси пуст.\n\nДобавьте первый прокси командой `/proxy_add <название> <url> <страна>`", parse_mode="Markdown")
        return
    
    proxies_text = "📝 **Доступные прокси:**\n\n"
    for name, info in proxies.items():
        status_emoji = "🟢" if info.get("is_active", True) else "🔴"
        country_emoji = "🌍"
        
        proxies_text += f"{status_emoji} **{name}**\n"
        proxies_text += f"   URL: {info['proxy_url']}\n"
        proxies_text += f"   {country_emoji} Страна: {info['country'].upper()}\n"
        proxies_text += f"   ✅ Успешно: {info.get('success_count', 0)}\n"
        proxies_text += f"   ❌ Ошибок: {info.get('fail_count', 0)}\n"
        
        last_used = info.get("last_used")
        if last_used:
            last_used_dt = datetime.fromisoformat(last_used)
            proxies_text += f"   🕐 Последнее использование: {last_used_dt.strftime('%d.%m.%Y %H:%M')}\n"
        
        proxies_text += "\n"
    
    await message.answer(proxies_text, parse_mode="Markdown")


@dp.message(Command("proxy_test"))
async def cmd_test_proxy(message: Message):
    """Command for testing proxy"""
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("❌ Неправильный формат команды!\n\nИспользуйте: `/proxy_test <название>`\n\nПример: `/proxy_test us_proxy`", parse_mode="Markdown")
            return
        
        name = parts[1].lower()
        proxy_info = proxy_manager.proxies.get(name)
        
        if not proxy_info:
            await message.answer(f"❌ Прокси с названием **{name}** не найден!", parse_mode="Markdown")
            return
        
        # Send message about start of testing
        status_msg = await message.answer(f"🔍 Testing proxy **{name}**...")
        
        # Test proxy
        is_working = await proxy_manager.test_proxy(proxy_info["proxy_url"])
        
        if is_working:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text=f"✅ Прокси **{name}** работает!\n\nURL: {proxy_info['proxy_url']}\n🌍 Страна: {proxy_info['country'].upper()}",
                parse_mode="Markdown"
            )
        else:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=status_msg.message_id,
                text=f"❌ Прокси **{name}** не работает!\n\nURL: {proxy_info['proxy_url']}\n🌍 Страна: {proxy_info['country'].upper()}",
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Error testing proxy: {e}")
        await message.answer("❌ Произошла ошибка при тестировании прокси")


async def main():
    """Main function"""
    logger.info("Starting bot for site monitoring...")
    
    # Initialize monitors
    await site_monitor.initialize()
    await proxy_manager.initialize()
    
    # Start periodic checking in background
    asyncio.create_task(periodic_check(site_monitor, proxy_manager))
    
    # Start bot
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
