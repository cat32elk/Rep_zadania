import requests
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import time
import pandas as pd
import os
import hashlib

# Попытка импортировать mplfinance для свечных графиков
try:
    import mplfinance as mpf

    HAS_MPLFINANCE = True
except ImportError:
    HAS_MPLFINANCE = False
    print("Для свечных графиков установите: pip install mplfinance")

# --- НАСТРОЙКИ ---
# Список популярных криптовалют (ID для CoinGecko)
POPULAR_COINS = [
    {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
    {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
    {"id": "solana", "symbol": "SOL", "name": "Solana"},
    {"id": "cardano", "symbol": "ADA", "name": "Cardano"},
    {"id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin"}
]

# Периоды для анализа (в днях)
PERIODS = {
    "7 дней": 7,
    "14 дней": 14,
    "30 дней": 30,
    "90 дней": 90
}

# --- КЭШИРОВАНИЕ ---
CACHE_DIR = "crypto_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Время жизни кэша (в секундах)
CACHE_TIMES = {
    "historical": 3600,  # 1 час
    "ohlc": 3600,  # 1 час
    "prices": 600,  # 10 минут
    "comparison": 3600  # 1 час
}


def get_cache_filename(data_type, *args):
    """Создает уникальное имя файла для кэша"""
    key = f"{data_type}_{'_'.join(str(arg) for arg in args)}"
    hash_key = hashlib.md5(key.encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{data_type}_{hash_key}.json")


def load_from_cache(cache_file, max_age):
    """Загружает данные из кэша, если они не устарели"""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                timestamp = cache_data.get('timestamp', 0)
                age = time.time() - timestamp
                if age < max_age:
                    print(f"  ✓ Использован кэш (возраст: {int(age / 60)} мин.)")
                    return cache_data.get('data')
                else:
                    print(f"  ⚠ Кэш устарел (возраст: {int(age / 60)} мин.)")
        except Exception as e:
            print(f"  ✗ Ошибка чтения кэша: {e}")
    return None


def save_to_cache(cache_file, data):
    """Сохраняет данные в кэш"""
    try:
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print("  ✓ Данные сохранены в кэш")
        return True
    except Exception as e:
        print(f"  ✗ Ошибка сохранения кэша: {e}")
        return False


def make_request_with_cache(url, params, cache_type, cache_args, max_age, silent=False):
    """
    Выполняет запрос с кэшированием
    """
    cache_key = get_cache_filename(cache_type, *cache_args)

    # Пробуем загрузить из кэша
    cached_data = load_from_cache(cache_key, max_age)
    if cached_data is not None:
        return cached_data

    # Если данных нет или они устарели, делаем запрос
    try:
        if not silent:
            print(f"  📡 Запрос к API...")

        # Задержка для соблюдения лимитов API
        time.sleep(2)

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Сохраняем в кэш
        save_to_cache(cache_key, data)

        return data

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Ошибка запроса: {e}")

        # Пробуем использовать устаревший кэш
        if os.path.exists(cache_key):
            try:
                with open(cache_key, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    print("  ⚠ Используются устаревшие кэшированные данные")
                    return cache_data.get('data')
            except:
                pass

        return None
    except Exception as e:
        print(f"  ✗ Непредвиденная ошибка: {e}")
        return None


# --- ОСНОВНЫЕ ФУНКЦИИ ---

def get_current_prices(coins=POPULAR_COINS):
    """
    Получает текущие цены для всех популярных криптовалют (с кэшированием)
    """
    results = {}

    for coin in coins:
        coin_id = coin['id']
        symbol = coin['symbol']
        name = coin['name']

        print(f"\n💰 {name} ({symbol})")

        # Создаем ключ для кэша
        cache_key = get_cache_filename("price", coin_id, "usd")

        # Проверяем кэш
        cached_price = load_from_cache(cache_key, CACHE_TIMES["prices"])
        if cached_price is not None:
            results[coin_id] = {
                'symbol': symbol,
                'name': name,
                'price': cached_price,
                'from_cache': True
            }
            print(f"  Цена: ${cached_price:,.2f} (из кэша)")
            continue

        # Делаем запрос
        try:
            time.sleep(1.5)  # Задержка между запросами

            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd"
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if coin_id in data and 'usd' in data[coin_id]:
                price = data[coin_id]['usd']
                results[coin_id] = {
                    'symbol': symbol,
                    'name': name,
                    'price': price,
                    'from_cache': False
                }

                # Сохраняем в кэш
                save_to_cache(cache_key, price)
                print(f"  Цена: ${price:,.2f}")
            else:
                print(f"  ✗ Цена не найдена")
                results[coin_id] = {
                    'symbol': symbol,
                    'name': name,
                    'price': None,
                    'from_cache': False
                }

        except Exception as e:
            print(f"  ✗ Ошибка: {e}")
            results[coin_id] = {
                'symbol': symbol,
                'name': name,
                'price': None,
                'from_cache': False
            }

    return results


def get_historical_data(coin_id, days=30, vs_currency="usd"):
    """
    Получает исторические данные для одной криптовалюты
    """
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": vs_currency,
            "days": days,
            "interval": "daily"
        }

        cache_args = (coin_id, vs_currency, days)
        max_age = CACHE_TIMES["historical"]

        data = make_request_with_cache(url, params, "historical", cache_args, max_age, silent=True)

        if not data:
            return None

        prices = data.get('prices', [])

        historical_data = []
        for timestamp, price in prices:
            date = datetime.fromtimestamp(timestamp / 1000)
            historical_data.append({
                'date': date,
                'price': price
            })

        return historical_data

    except Exception as e:
        print(f"  ✗ Ошибка получения данных для {coin_id}: {e}")
        return None


def get_ohlc_data(coin_id, days=30, vs_currency="usd"):
    """
    Получает OHLC данные для свечного графика
    """
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params = {
            "vs_currency": vs_currency,
            "days": days
        }

        cache_args = (coin_id, vs_currency, days)
        max_age = CACHE_TIMES["ohlc"]

        data = make_request_with_cache(url, params, "ohlc", cache_args, max_age, silent=True)

        if not data:
            return None

        ohlc_data = []
        for item in data:
            date = datetime.fromtimestamp(item[0] / 1000)
            ohlc_data.append({
                'date': date,
                'open': item[1],
                'high': item[2],
                'low': item[3],
                'close': item[4]
            })

        return ohlc_data

    except Exception as e:
        print(f"  ✗ Ошибка получения OHLC для {coin_id}: {e}")
        return None


def load_all_historical_data(coins=POPULAR_COINS, days=30):
    """
    Загружает исторические данные для всех популярных криптовалют
    """
    print(f"\n📊 Загрузка исторических данных за {days} дней...")
    print("-" * 60)

    all_data = {}

    for coin in coins:
        coin_id = coin['id']
        symbol = coin['symbol']
        name = coin['name']

        print(f"\n🪙 {name} ({symbol})")

        data = get_historical_data(coin_id, days)
        if data:
            all_data[coin_id] = data
            prices = [item['price'] for item in data]
            print(f"  ✓ Загружено {len(data)} записей")
            print(f"    Начальная цена: ${prices[0]:,.2f}")
            print(f"    Текущая цена: ${prices[-1]:,.2f}")
            change = ((prices[-1] - prices[0]) / prices[0]) * 100
            print(f"    Изменение: {change:+.2f}%")
            print(f"    Минимум: ${min(prices):,.2f}")
            print(f"    Максимум: ${max(prices):,.2f}")
        else:
            print(f"  ✗ Нет данных")

    return all_data


def print_summary_table(prices_data):
    """
    Выводит сводную таблицу с текущими ценами
    """
    print("\n" + "=" * 70)
    print("📊 СВОДНАЯ ТАБЛИЦА ЦЕН")
    print("=" * 70)
    print(f"{'№':<4} {'Криптовалюта':<15} {'Символ':<8} {'Цена (USD)':<15} {'Источник'}")
    print("-" * 70)

    for i, (coin_id, data) in enumerate(prices_data.items(), 1):
        symbol = data['symbol']
        name = data['name']
        price = data['price']
        source = "Кэш" if data.get('from_cache', False) else "API"

        if price:
            print(f"{i:<4} {name:<15} {symbol:<8} ${price:>12,.2f}  {source}")
        else:
            print(f"{i:<4} {name:<15} {symbol:<8} {'Нет данных':<15}  {source}")

    print("=" * 70)
    print(f"* Источник данных: CoinGecko")
    print(f"* Время обновления: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)


def plot_comparison_chart(all_data, days=30):
    """
    Строит график сравнения всех криптовалют
    """
    if not all_data:
        print("Нет данных для построения графика")
        return

    plt.figure(figsize=(14, 8))

    # Цвета для разных криптовалют
    colors = {
        'bitcoin': '#F7931A',
        'ethereum': '#627EEA',
        'solana': '#9945FF',
        'cardano': '#0033AD',
        'dogecoin': '#C2A633'
    }

    for coin_id, data in all_data.items():
        if data:
            # Находим название монеты
            name = next((c['name'] for c in POPULAR_COINS if c['id'] == coin_id), coin_id)
            dates = [item['date'] for item in data]
            prices = [item['price'] for item in data]
            color = colors.get(coin_id, '#2196F3')
            plt.plot(dates, prices, label=name, linewidth=2, color=color)

    plt.title(f'Сравнение цен криптовалют за {days} дней', fontsize=16, fontweight='bold')
    plt.xlabel('Дата', fontsize=12)
    plt.ylabel('Цена (USD)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left')
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()


def plot_individual_charts(all_data, days=30):
    """
    Строит отдельные графики для каждой криптовалюты
    """
    if not all_data:
        print("Нет данных для построения графиков")
        return

    # Цвета для разных криптовалют
    colors = {
        'bitcoin': '#F7931A',
        'ethereum': '#627EEA',
        'solana': '#9945FF',
        'cardano': '#0033AD',
        'dogecoin': '#C2A633'
    }

    for coin_id, data in all_data.items():
        if data:
            name = next((c['name'] for c in POPULAR_COINS if c['id'] == coin_id), coin_id)
            symbol = next((c['symbol'] for c in POPULAR_COINS if c['id'] == coin_id), coin_id)

            dates = [item['date'] for item in data]
            prices = [item['price'] for item in data]

            plt.figure(figsize=(12, 6))
            color = colors.get(coin_id, '#2196F3')
            plt.plot(dates, prices, linewidth=2, color=color)

            plt.title(f'{name} ({symbol}) - Цена за {days} дней', fontsize=16, fontweight='bold')
            plt.xlabel('Дата', fontsize=12)
            plt.ylabel('Цена (USD)', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)

            # Добавляем информацию о ценах
            min_price = min(prices)
            max_price = max(prices)
            current_price = prices[-1]

            plt.text(0.02, 0.98, f'Текущая: ${current_price:,.2f}',
                     transform=plt.gca().transAxes, fontsize=10,
                     verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            plt.text(0.02, 0.92, f'Мин: ${min_price:,.2f}',
                     transform=plt.gca().transAxes, fontsize=10,
                     verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            plt.text(0.02, 0.86, f'Макс: ${max_price:,.2f}',
                     transform=plt.gca().transAxes, fontsize=10,
                     verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

            plt.tight_layout()
            plt.show()


def plot_candlestick_chart(coin_id="bitcoin", days=14):
    """
    Строит свечной график для указанной криптовалюты
    """
    if not HAS_MPLFINANCE:
        print("❌ Библиотека mplfinance не установлена")
        print("Установите: pip install mplfinance")
        return

    print(f"\n📊 Получение OHLC данных для {coin_id}...")
    ohlc_data = get_ohlc_data(coin_id, days)

    if not ohlc_data:
        print("Нет данных для построения свечного графика")
        return

    try:
        name = next((c['name'] for c in POPULAR_COINS if c['id'] == coin_id), coin_id)
        symbol = next((c['symbol'] for c in POPULAR_COINS if c['id'] == coin_id), coin_id)

        df = pd.DataFrame(ohlc_data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        mpf.plot(df, type='candle', style='charles',
                 title=f'{name} ({symbol}) - Свечной график за {days} дней',
                 volume=False, figsize=(14, 7))

    except Exception as e:
        print(f"✗ Ошибка при построении свечного графика: {e}")


def clear_cache():
    """Очищает кэш"""
    if os.path.exists(CACHE_DIR):
        count = 0
        for file in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    count += 1
            except:
                pass
        print(f"✓ Очищено {count} файлов кэша")
    else:
        print("Папка кэша не найдена")


def show_cache_info():
    """Показывает информацию о кэше"""
    if not os.path.exists(CACHE_DIR):
        print("Папка кэша не найдена")
        return

    files = os.listdir(CACHE_DIR)
    if not files:
        print("Кэш пуст")
        return

    print("\n📁 Информация о кэше:")
    print("-" * 60)
    total_size = 0

    for file in files:
        file_path = os.path.join(CACHE_DIR, file)
        size = os.path.getsize(file_path)
        total_size += size
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        age = int((datetime.now() - mod_time).total_seconds() / 60)

        # Определяем тип данных
        data_type = file.split('_')[0] if '_' in file else 'unknown'

        print(f"  {data_type:<12} {file:<35} {size / 1024:>6.1f} KB  ({age} мин.)")

    print("-" * 60)
    print(f"Всего файлов: {len(files)}, Общий размер: {total_size / 1024:.1f} KB")


# --- ОСНОВНАЯ ПРОГРАММА ---

def main():
    print("=" * 70)
    print("🪙 АНАЛИЗ ПОПУЛЯРНЫХ КРИПТОВАЛЮТ (С КЭШИРОВАНИЕМ)")
    print("=" * 70)

    # Показываем список анализируемых монет
    print("\n📋 Анализируемые криптовалюты:")
    for i, coin in enumerate(POPULAR_COINS, 1):
        print(f"  {i}. {coin['name']} ({coin['symbol']}) - ID: {coin['id']}")

    print(f"\n💾 Кэш: включен (папка: {CACHE_DIR})")
    print(f"⏰ Время жизни кэша: 1 час для исторических данных, 10 минут для цен")

    # 1. Получаем текущие цены
    print("\n" + "=" * 70)
    print("1️⃣ ТЕКУЩИЕ ЦЕНЫ")
    print("=" * 70)

    prices_data = get_current_prices()
    print_summary_table(prices_data)

    # 2. Загружаем исторические данные
    print("\n" + "=" * 70)
    print("2️⃣ ИСТОРИЧЕСКИЕ ДАННЫЕ (30 дней)")
    print("=" * 70)

    days = 30
    historical_data = load_all_historical_data(POPULAR_COINS, days)

    # 3. Строим графики
    if historical_data:
        print("\n" + "=" * 70)
        print("3️⃣ ПОСТРОЕНИЕ ГРАФИКОВ")
        print("=" * 70)

        # Сравнительный график
        print("\n▶ Строим сравнительный график...")
        plot_comparison_chart(historical_data, days)

        # Индивидуальные графики
        print("\n▶ Строим индивидуальные графики...")
        plot_individual_charts(historical_data, days)

        # Свечной график для Bitcoin
        print("\n▶ Строим свечной график для Bitcoin...")
        plot_candlestick_chart("bitcoin", 14)

    # 4. Информация о кэше
    print("\n" + "=" * 70)
    print("4️⃣ ИНФОРМАЦИЯ О КЭШЕ")
    print("=" * 70)
    show_cache_info()

    print("\n" + "=" * 70)
    print("✅ АНАЛИЗ ЗАВЕРШЕН")
    print("=" * 70)

    print("\n💡 Советы:")
    print("  - Для обновления цен используйте: get_current_prices()")
    print("  - Для очистки кэша: clear_cache()")
    print("  - Для просмотра кэша: show_cache_info()")


if __name__ == "__main__":
    main()