#!/usr/bin/env python3
"""
Запуск телеграм-бота для мониторинга сайтов
"""

import asyncio
from src.main import main

if __name__ == "__main__":
    asyncio.run(main()) 