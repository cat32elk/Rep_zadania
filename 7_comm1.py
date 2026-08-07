import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import time
import pandas as pd
import mplfinance as mpf


def get_historical_data(coin_id="bitcoin", vs_currency="usd", days=7):
    """
    Получает исторические данные криптовалюты с CoinGecko API

    Аргументы:
    - coin_id: ID криптовалюты (например, 'bitcoin', 'ethereum')
    - vs_currency: валюта для сравнения (по умолчанию 'usd')
    - days: количество дней истории (1, 7, 14, 30, 90, 365)

    Возвращает:
    - Список словарей с датой и ценой
    """
    try:
        print(f"Запрос данных для {coin_id} за {days} дней...")
        time.sleep(1)  # Задержка для соблюдения лимитов API

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": vs_currency,
            "days": days,
            "interval": "daily"  # Можно изменить на 'hourly' для более детальных данных
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Обработка данных: prices содержит [timestamp, price]
        prices = data['prices']

        # Преобразуем в удобный формат
        historical_data = []
        for timestamp, price in prices:
            # Преобразуем миллисекунды в datetime
            date = datetime.fromtimestamp(timestamp / 1000)
            historical_data.append({
                'date': date,
                'price': price
            })

        print(f"✓ Получено {len(historical_data)} записей")
        return historical_data

    except requests.exceptions.RequestException as e:
        print(f"✗ Ошибка при запросе данных: {e}")
        return None
    except Exception as e:
        print(f"✗ Непредвиденная ошибка: {e}")
        return None


def get_top_coins(limit=10):
    """
    Получает список топ криптовалют по рыночной капитализации

    Аргументы:
    - limit: количество монет для получения

    Возвращает:
    - Список словарей с информацией о монетах
    """
    try:
        print("Запрос списка топ криптовалют...")
        time.sleep(1)

        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        coins = []
        for coin in data:
            coins.append({
                'id': coin['id'],
                'symbol': coin['symbol'].upper(),
                'name': coin['name'],
                'price': coin['current_price'],
                'market_cap': coin['market_cap']
            })

        print(f"✓ Получено {len(coins)} криптовалют")
        return coins

    except Exception as e:
        print(f"✗ Ошибка при получении списка монет: {e}")
        return []


def plot_simple_chart(data, title="Историческая цена"):
    """
    Строит простой линейный график

    Аргументы:
    - data: список словарей с ключами 'date' и 'price'
    - title: заголовок графика
    """
    if not data:
        print("Нет данных для отображения")
        return

    # Извлекаем даты и цены
    dates = [item['date'] for item in data]
    prices = [item['price'] for item in data]

    # Создаем график
    plt.figure(figsize=(12, 6))
    plt.plot(dates, prices, linewidth=2, color='#2196F3')

    # Настройки графика
    plt.title(title, fontsize=16, fontweight='bold')
    plt.xlabel('Дата', fontsize=12)
    plt.ylabel('Цена (USD)', fontsize=12)
    plt.grid(True, alpha=0.3)

    # Форматирование оси X
    plt.xticks(rotation=45)

    # Добавляем сетку
    plt.grid(True, alpha=0.3)

    # Показываем график
    plt.tight_layout()
    plt.show()


def plot_multi_chart(coins_data, title="Сравнение цен криптовалют"):
    """
    Строит график сравнения нескольких криптовалют

    Аргументы:
    - coins_data: словарь {название_монеты: данные_цены}
    - title: заголовок графика
    """
    if not coins_data:
        print("Нет данных для отображения")
        return

    plt.figure(figsize=(14, 7))

    # Цвета для разных криптовалют
    colors = ['#2196F3', '#FF9800', '#4CAF50', '#F44336', '#9C27B0', '#00BCD4']

    for i, (name, data) in enumerate(coins_data.items()):
        if data:
            dates = [item['date'] for item in data]
            prices = [item['price'] for item in data]
            color = colors[i % len(colors)]
            plt.plot(dates, prices, label=name, linewidth=2, color=color)

    # Настройки графика
    plt.title(title, fontsize=16, fontweight='bold')
    plt.xlabel('Дата', fontsize=12)
    plt.ylabel('Цена (USD)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left')
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()


def plot_candlestick(data, title="Свечной график"):
    """
    Строит свечной график (требуется установка библиотеки mplfinance)

    Аргументы:
    - data: список словарей с ключами 'date', 'open', 'high', 'low', 'close'
    - title: заголовок графика
    """
    try:

        if not data:
            print("Нет данных для отображения")
            return

        # Преобразуем в DataFrame для mplfinance
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # Строим свечной график
        mpf.plot(df, type='candle', style='charles', title=title,
                 volume=False, figsize=(14, 7))

    except ImportError:
        print("Для свечного графика требуются библиотеки pandas и mplfinance")
        print("Установите их: pip install pandas mplfinance")


def get_ohlc_data(coin_id="bitcoin", vs_currency="usd", days=30):
    """
    Получает OHLC данные (Open, High, Low, Close) для свечного графика

    Аргументы:
    - coin_id: ID криптовалюты
    - vs_currency: валюта для сравнения
    - days: количество дней

    Возвращает:
    - Список словарей с OHLC данными
    """
    try:
        print(f"Запрос OHLC данных для {coin_id}...")
        time.sleep(1)

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params = {
            "vs_currency": vs_currency,
            "days": days
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        ohlc_data = []
        for item in data:
            # Формат: [timestamp, open, high, low, close]
            date = datetime.fromtimestamp(item[0] / 1000)
            ohlc_data.append({
                'date': date,
                'open': item[1],
                'high': item[2],
                'low': item[3],
                'close': item[4]
            })

        print(f"✓ Получено {len(ohlc_data)} OHLC записей")
        return ohlc_data

    except Exception as e:
        print(f"✗ Ошибка при получении OHLC данных: {e}")
        return None


# --- Основная часть для экспериментов ---

if __name__ == "__main__":
    print("=" * 50)
    print("ЭКСПЕРИМЕНТЫ С ИСТОРИЧЕСКИМИ ДАННЫМИ КРИПТОВАЛЮТ")
    print("=" * 50)

    # 1. Получаем список топ криптовалют
    top_coins = get_top_coins(5)
    if top_coins:
        print("\nТоп криптовалют:")
        for i, coin in enumerate(top_coins, 1):
            print(f"  {i}. {coin['name']} ({coin['symbol']}): ${coin['price']:,.2f}")

    # 2. Получаем исторические данные для Bitcoin
    print("\n" + "-" * 50)
    btc_data = get_historical_data("bitcoin", "usd", 30)

    if btc_data:
        # Выводим первые 5 и последние 5 записей
        print("\nПример данных:")
        print(f"  Первые 5 записей:")
        for item in btc_data[:5]:
            print(f"    {item['date'].strftime('%Y-%m-%d')}: ${item['price']:,.2f}")

        print(f"  Последние 5 записей:")
        for item in btc_data[-5:]:
            print(f"    {item['date'].strftime('%Y-%m-%d')}: ${item['price']:,.2f}")

        # 3. Строим простой линейный график
        print("\nСтроим линейный график Bitcoin...")
        plot_simple_chart(btc_data, "Bitcoin (BTC) - Цена за 30 дней")

    # 4. Получаем данные для нескольких криптовалют для сравнения
    print("\n" + "-" * 50)
    print("Получение данных для сравнения нескольких криптовалют...")

    multi_coins = {}
    for coin in top_coins[:3]:  # Берем первые 3 монеты
        coin_id = coin['id']
        data = get_historical_data(coin_id, "usd", 30)
        if data:
            multi_coins[coin['symbol']] = data

    if len(multi_coins) > 1:
        print("\nСтроим график сравнения...")
        plot_multi_chart(multi_coins, "Сравнение цен криптовалют за 30 дней")

    # 5. Получаем OHLC данные для свечного графика
    print("\n" + "-" * 50)
    ohlc_data = get_ohlc_data("bitcoin", "usd", 14)

    if ohlc_data:
        print(f"\nПример OHLC данных (первые 5):")
        for item in ohlc_data[:5]:
            print(f"  {item['date'].strftime('%Y-%m-%d')}: O=${item['open']:.2f}, "
                  f"H=${item['high']:.2f}, L=${item['low']:.2f}, C=${item['close']:.2f}")

        # Пытаемся построить свечной график (требуется mplfinance)
        try:
            print("\nПопытка построить свечной график...")
            plot_candlestick(ohlc_data, "Bitcoin (BTC) - Свечной график")
        except:
            print("  Не удалось построить свечной график (возможно, не установлены pandas/mplfinance)")
            print("  Установите: pip install pandas mplfinance")

    print("\n" + "=" * 50)
    print("ЭКСПЕРИМЕНТЫ ЗАВЕРШЕНЫ")
    print("=" * 50)