from tkinter import *
from tkinter import ttk
from tkinter import messagebox as mb
import requests
import threading
import os
import json
import time
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

# Файлы для кэша
CACHE_FILE = "crypto_cache.json"
COINS_LIST_CACHE = "coins_list_cache.json"

# Кэш для цен (в памяти) - 2 минуты
PRICE_CACHE = {}

# Словари для хранения данных разных источников
crypto_data = {
    "CoinGecko": {"symbols": {}, "names": {}},
    "CoinMarketCap": {"symbols": {}, "names": {}},
    "CoinCap": {"symbols": {}, "names": {}},
    "CoinPaprika": {"symbols": {}, "names": {}},
    "Binance": {"symbols": {}, "names": {}},
    "Kraken": {"symbols": {}, "names": {}}
}

# Доступные источники данных
DATA_SOURCES = ["CoinGecko", "CoinMarketCap", "CoinCap", "CoinPaprika", "Binance", "Kraken"]


def get_coingecko_coin_id(symbol):
    """Получает ID монеты по символу с кэшированием"""
    # Проверяем кэш
    if os.path.exists(COINS_LIST_CACHE):
        try:
            with open(COINS_LIST_CACHE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                # Кэш действителен 24 часа
                if time.time() - cache.get('timestamp', 0) < 86400:
                    for coin in cache['coins']:
                        if coin['symbol'].upper() == symbol.upper():
                            return coin['id']
        except:
            pass

    # Загружаем свежий список
    try:
        time.sleep(3)  # ЗАДЕРЖКА 3 СЕКУНДЫ
        url = "https://api.coingecko.com/api/v3/coins/list"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        all_coins = response.json()

        # Сохраняем в кэш
        with open(COINS_LIST_CACHE, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.time(),
                'coins': all_coins
            }, f, ensure_ascii=False, indent=2)

        # Ищем ID
        for coin in all_coins:
            if coin['symbol'].upper() == symbol.upper():
                return coin['id']

        return None

    except Exception as e:
        print(f"Ошибка получения списка монет: {e}")
        return None


# --- Функции загрузки списков криптовалют с кэшированием ---

def load_coingecko_list():
    """Загружает список криптовалют с CoinGecko с кэшированием и задержкой"""

    # Проверяем наличие кэша
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                if time.time() - cache.get('timestamp', 0) < 3600:
                    if 'coingecko' in cache:
                        crypto_data["CoinGecko"]["symbols"] = cache['coingecko']['symbols']
                        crypto_data["CoinGecko"]["names"] = cache['coingecko']['names']
                        return True
        except:
            pass

    try:
        time.sleep(3)  # ЗАДЕРЖКА 3 СЕКУНДЫ

        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": "false"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        symbols = {}
        names = {}
        for coin in data:
            symbol = coin['symbol'].upper()
            name = coin['name']
            symbols[symbol] = name
            names[name] = symbol

        crypto_data["CoinGecko"]["symbols"] = symbols
        crypto_data["CoinGecko"]["names"] = names

        # Сохраняем в кэш
        cache_data = {'timestamp': time.time()}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

        cache_data['coingecko'] = {'symbols': symbols, 'names': names}
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        # Пробуем использовать устаревший кэш
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    if 'coingecko' in cache:
                        crypto_data["CoinGecko"]["symbols"] = cache['coingecko']['symbols']
                        crypto_data["CoinGecko"]["names"] = cache['coingecko']['names']
                        mb.showwarning("Внимание", f"Используются кэшированные данные CoinGecko.\nОшибка: {e}")
                        return True
            except:
                pass

        mb.showerror("Ошибка загрузки", f"CoinGecko: {e}")
        return False


def load_coinmarketcap_list():
    """Загружает список криптовалют с CoinMarketCap"""
    try:
        API_KEY = os.getenv('CMC_API_KEY')
        if not API_KEY:
            mb.showerror("Ошибка", "API ключ CoinMarketCap не найден!")
            return False

        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        headers = {"X-CMC_PRO_API_KEY": API_KEY}
        params = {"limit": 100, "convert": "USD"}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        symbols = {}
        names = {}
        for coin in data['data']:
            symbol = coin['symbol'].upper()
            name = coin['name']
            symbols[symbol] = name
            names[name] = symbol

        crypto_data["CoinMarketCap"]["symbols"] = symbols
        crypto_data["CoinMarketCap"]["names"] = names
        return True

    except Exception as e:
        mb.showerror("Ошибка загрузки", f"CoinMarketCap: {e}")
        return False


def load_coincap_list():
    """Загружает список криптовалют с CoinCap (без ключа)"""
    try:
        time.sleep(0.5)

        url = "https://api.coincap.io/v2/assets"
        params = {"limit": 100}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        symbols = {}
        names = {}
        for coin in data['data']:
            symbol = coin['symbol'].upper()
            name = coin['name']
            symbols[symbol] = name
            names[name] = symbol

        crypto_data["CoinCap"]["symbols"] = symbols
        crypto_data["CoinCap"]["names"] = names

        # Сохраняем в кэш
        cache_data = {'timestamp': time.time()}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

        cache_data['coincap'] = {'symbols': symbols, 'names': names}
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        mb.showerror("Ошибка загрузки", f"CoinCap: {e}")
        return False


def load_coinpaprika_list():
    """Загружает список криптовалют с CoinPaprika (без ключа)"""
    try:
        time.sleep(0.5)

        url = "https://api.coinpaprika.com/v1/tickers"
        params = {"limit": 100}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        symbols = {}
        names = {}
        for coin in data:
            symbol = coin['symbol'].upper()
            name = coin['name']
            symbols[symbol] = name
            names[name] = symbol

        crypto_data["CoinPaprika"]["symbols"] = symbols
        crypto_data["CoinPaprika"]["names"] = names

        # Сохраняем в кэш
        cache_data = {'timestamp': time.time()}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

        cache_data['coinpaprika'] = {'symbols': symbols, 'names': names}
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        mb.showerror("Ошибка загрузки", f"CoinPaprika: {e}")
        return False


def load_binance_list():
    """Загружает список криптовалют с Binance (без ключа)"""
    try:
        time.sleep(0.5)

        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        symbols = {}
        names = {}
        # Берем только пары с USDT (самые популярные)
        for symbol in data['symbols']:
            if symbol['status'] == 'TRADING' and symbol['quoteAsset'] == 'USDT':
                base = symbol['baseAsset']
                symbols[base] = base
                names[base] = base

        crypto_data["Binance"]["symbols"] = symbols
        crypto_data["Binance"]["names"] = names

        # Сохраняем в кэш
        cache_data = {'timestamp': time.time()}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

        cache_data['binance'] = {'symbols': symbols, 'names': names}
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        mb.showerror("Ошибка загрузки", f"Binance: {e}")
        return False


def load_kraken_list():
    """Загружает список криптовалют с Kraken (без ключа)"""
    try:
        time.sleep(0.5)

        url = "https://api.kraken.com/0/public/Assets"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        symbols = {}
        names = {}
        for asset_id, asset_data in data['result'].items():
            if asset_data.get('status') == 'enabled':
                symbol = asset_id.upper()
                # Пытаемся получить название, если есть
                name = asset_data.get('name', asset_id)
                symbols[symbol] = name
                names[name] = symbol

        crypto_data["Kraken"]["symbols"] = symbols
        crypto_data["Kraken"]["names"] = names

        # Сохраняем в кэш
        cache_data = {'timestamp': time.time()}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

        cache_data['kraken'] = {'symbols': symbols, 'names': names}
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        mb.showerror("Ошибка загрузки", f"Kraken: {e}")
        return False


# --- Функция получения курса к USD с кэшированием цен ---

def get_price_to_usd(source, crypto_symbol):
    """Получает цену криптовалюты в USD из выбранного источника с кэшированием"""
    # Проверяем кэш цен (действителен 2 минуты)
    cache_key = f"{source}_{crypto_symbol}"
    if cache_key in PRICE_CACHE:
        cached_time, cached_price = PRICE_CACHE[cache_key]
        if time.time() - cached_time < 120:  # 2 минуты
            return cached_price, None

    try:
        if source == "CoinGecko":
            time.sleep(3)  # ЗАДЕРЖКА 3 СЕКУНДЫ

            # Получаем ID монеты из кэша
            coin_id = get_coingecko_coin_id(crypto_symbol)

            if not coin_id:
                return None, f"Валюта {crypto_symbol} не найдена"

            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {"ids": coin_id, "vs_currencies": "usd"}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if coin_id not in data:
                return None, f"Цена для {crypto_symbol} не найдена"

            price = data[coin_id]['usd']

            # Сохраняем в кэш цен
            PRICE_CACHE[cache_key] = (time.time(), price)

            return price, None

        elif source == "CoinMarketCap":
            API_KEY = os.getenv('CMC_API_KEY')
            if not API_KEY:
                return None, "API ключ CoinMarketCap не найден!"

            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
            headers = {"X-CMC_PRO_API_KEY": API_KEY}
            params = {"symbol": crypto_symbol, "convert": "USD"}
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if crypto_symbol not in data['data']:
                return None, f"Валюта {crypto_symbol} не найдена"

            price = data['data'][crypto_symbol]['quote']['USD']['price']
            PRICE_CACHE[cache_key] = (time.time(), price)
            return price, None

        elif source == "CoinCap":
            time.sleep(0.3)

            url = f"https://api.coincap.io/v2/assets/{crypto_symbol.lower()}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if 'data' not in data:
                return None, f"Валюта {crypto_symbol} не найдена"

            price = float(data['data']['priceUsd'])
            PRICE_CACHE[cache_key] = (time.time(), price)
            return price, None

        elif source == "CoinPaprika":
            time.sleep(0.3)

            # Сначала ищем ID по символу
            url = "https://api.coinpaprika.com/v1/tickers"
            response = requests.get(url)
            response.raise_for_status()
            all_tickers = response.json()

            coin_id = None
            for coin in all_tickers:
                if coin['symbol'].upper() == crypto_symbol:
                    coin_id = coin['id']
                    break

            if not coin_id:
                return None, f"Валюта {crypto_symbol} не найдена"

            url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if 'quotes' not in data or 'USD' not in data['quotes']:
                return None, f"Цена для {crypto_symbol} не найдена"

            price = data['quotes']['USD']['price']
            PRICE_CACHE[cache_key] = (time.time(), price)
            return price, None

        elif source == "Binance":
            time.sleep(0.3)

            url = f"https://api.binance.com/api/v3/ticker/price"
            params = {"symbol": f"{crypto_symbol}USDT"}
            response = requests.get(url, params=params)

            if response.status_code == 404:
                return None, f"Пара {crypto_symbol}/USDT не найдена"

            response.raise_for_status()
            data = response.json()

            price = float(data['price'])
            PRICE_CACHE[cache_key] = (time.time(), price)
            return price, None

        elif source == "Kraken":
            time.sleep(0.3)

            # Формируем пару XBT для BTC, иначе просто добавляем USD
            if crypto_symbol == "BTC":
                pair = "XXBTZUSD"
            elif crypto_symbol == "ETH":
                pair = "XETHZUSD"
            else:
                pair = f"{crypto_symbol}USD"

            url = f"https://api.kraken.com/0/public/Ticker"
            params = {"pair": pair}
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'error' in data and data['error']:
                return None, f"Ошибка Kraken: {data['error'][0]}"

            if pair not in data['result']:
                return None, f"Пара {pair} не найдена"

            ticker = data['result'][pair]
            price = float(ticker['c'][0])
            PRICE_CACHE[cache_key] = (time.time(), price)
            return price, None

    except requests.exceptions.RequestException as e:
        # Если запрос не удался, пробуем вернуть кэшированную цену
        if cache_key in PRICE_CACHE:
            _, cached_price = PRICE_CACHE[cache_key]
            mb.showwarning("Внимание",
                           f"Используется кэшированная цена для {crypto_symbol}.\n"
                           f"Ошибка: {str(e)}")
            return cached_price, None
        return None, f"Ошибка запроса: {str(e)}"
    except Exception as e:
        return None, f"Ошибка: {str(e)}"


# --- Функция обновления комбобоксов ---

def update_crypto_comboboxes():
    """Обновляет списки криптовалют в комбобоксах"""
    source = source_combobox.get()

    # Сопоставление источника с функцией загрузки
    loaders = {
        "CoinGecko": load_coingecko_list,
        "CoinMarketCap": load_coinmarketcap_list,
        "CoinCap": load_coincap_list,
        "CoinPaprika": load_coinpaprika_list,
        "Binance": load_binance_list,
        "Kraken": load_kraken_list
    }

    if source not in loaders:
        return

    if not loaders[source]():
        return

    symbols = list(crypto_data[source]["symbols"].keys())

    # Обновляем все комбобоксы
    crypto1_combobox['values'] = symbols
    crypto2_combobox['values'] = symbols

    # Очищаем выбор
    crypto1_combobox.set('')
    crypto2_combobox.set('')

    # Очищаем метки
    c1_label.config(text="")
    c2_label.config(text="")


# --- Функции обновления меток с названиями ---

def update_crypto1_label(event):
    code = crypto1_combobox.get()
    source = source_combobox.get()
    if source in crypto_data and code in crypto_data[source]["symbols"]:
        c1_label.config(text=crypto_data[source]["symbols"][code])
    else:
        c1_label.config(text="")


def update_crypto2_label(event):
    code = crypto2_combobox.get()
    source = source_combobox.get()
    if source in crypto_data and code in crypto_data[source]["symbols"]:
        c2_label.config(text=crypto_data[source]["symbols"][code])
    else:
        c2_label.config(text="")


# --- Функция получения курса к USD ---

def get_prices_to_usd():
    """Основная функция получения курсов криптовалют к USD"""
    source = source_combobox.get()
    crypto1_code = crypto1_combobox.get()
    crypto2_code = crypto2_combobox.get()

    if not all([source, crypto1_code, crypto2_code]):
        mb.showwarning("Внимание", "Выберите источник и обе криптовалюты")
        return

    def get_rates():
        try:
            price1, error1 = get_price_to_usd(source, crypto1_code)
            if error1:
                mb.showerror("Ошибка", error1)
                return

            price2, error2 = get_price_to_usd(source, crypto2_code)
            if error2:
                mb.showerror("Ошибка", error2)
                return

            crypto1_name = crypto_data[source]["symbols"].get(crypto1_code, crypto1_code)
            crypto2_name = crypto_data[source]["symbols"].get(crypto2_code, crypto2_code)

            mb.showinfo("Курсы к USD",
                        f"1 {crypto1_name} ({crypto1_code}) = ${price1:.6f} USD\n"
                        f"1 {crypto2_name} ({crypto2_code}) = ${price2:.6f} USD")

        except Exception as e:
            mb.showerror("Ошибка", f"Произошла ошибка: {str(e)}")

    threading.Thread(target=get_rates, daemon=True).start()


def show_info():
    mb.showinfo("О программе", "Источники: \n"
                               "CoinCap (не требует ключа, простой API, без ключа);\n"
                               "CoinPaprika (не требует ключа, надежный, без авторизации);\n"
                               "Binance (не требует ключа, только пары с USDT);\n"
                               "Kraken (не требует ключа, требует специальных названий пар (XXBTZUSD))\n"
                               "Особенности API: \n"
                               "CoinCap: \n"
                               " Список: https://api.coincap.io/v2/assets \n"
                               " Цена: https://api.coincap.io/v2/assets/bitcoin\n"
                               "CoinPaprika:\n"
                               " Список: https://api.coinpaprika.com/v1/tickers \n"
                               " Цена: https://api.coinpaprika.com/v1/tickers/btc-bitcoin\n"
                               "Binance:\n"
                               " Список: https://api.binance.com/api/v3/exchangeInfo\n"
                               " Цена: https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT\n"
                               "Kraken:\n"
                               " Список: https://api.kraken.com/0/public/Assets\n"
                               " Цена: https://api.kraken.com/0/public/Ticker?pair=XXBTZUSD\n"
                )


def change_source_from_menu(source_name):
    """Меняет источник из меню"""
    source_combobox.set(source_name)
    update_crypto_comboboxes()
    update_source_menu()


def on_source_combobox_change(event):
    """Обработчик изменения в Combobox"""
    update_source_menu()
    update_crypto_comboboxes()


def update_source_menu():
    """Обновляет меню источников, ставя галочку на текущий выбранный"""
    current_source = source_combobox.get()
    for i, source in enumerate(DATA_SOURCES):
        if source == current_source:
            source_menu.entryconfig(i, label=f"✓ {source}")
        else:
            source_menu.entryconfig(i, label=f"  {source}")


# --- Создание GUI ---

window = Tk()
window.title("Курсы криптовалют к USD")
window.geometry("650x350")
window.resizable(False, False)

main_frame = Frame(window)
main_frame.pack(padx=20, pady=20, fill=BOTH, expand=True)

# --- Строка 0: Выбор источника ---
Label(main_frame, text="Источник данных:", font=("Arial", 10, "bold")).grid(row=0, column=0, pady=10, sticky="w")

# Комбобокс для выбора источника
source_combobox = ttk.Combobox(main_frame, values=DATA_SOURCES, state="readonly", width=25)
source_combobox.grid(row=0, column=1, pady=10, sticky="w")
source_combobox.set(DATA_SOURCES[0])
source_combobox.bind("<<ComboboxSelected>>", on_source_combobox_change)

Button(main_frame, text="Загрузить список валют", command=update_crypto_comboboxes,
       bg="#4CAF50", fg="white").grid(row=0, column=2, padx=10, pady=10)

# --- Строка 1: Первая криптовалюта ---
Label(main_frame, text="Криптовалюта 1:").grid(row=1, column=0, pady=10, sticky="w")
crypto1_combobox = ttk.Combobox(main_frame, width=25)
crypto1_combobox.grid(row=1, column=1, pady=10, sticky="w")
crypto1_combobox.bind("<<ComboboxSelected>>", update_crypto1_label)
crypto1_combobox.bind("<KeyRelease>", update_crypto1_label)
c1_label = ttk.Label(main_frame, width=30)
c1_label.grid(row=1, column=2, pady=10, sticky="w")

# --- Строка 2: Вторая криптовалюта ---
Label(main_frame, text="Криптовалюта 2:").grid(row=2, column=0, pady=10, sticky="w")
crypto2_combobox = ttk.Combobox(main_frame, width=25)
crypto2_combobox.grid(row=2, column=1, pady=10, sticky="w")
crypto2_combobox.bind("<<ComboboxSelected>>", update_crypto2_label)
crypto2_combobox.bind("<KeyRelease>", update_crypto2_label)
c2_label = ttk.Label(main_frame, width=30)
c2_label.grid(row=2, column=2, pady=10, sticky="w")

# --- Строка 3: Информация ---
info_label = Label(main_frame, text="Курсы отображаются в USD (доллар США)",
                   font=("Arial", 9, "italic"), fg="gray")
info_label.grid(row=3, column=0, columnspan=3, pady=10)

# --- Строка 4: Кнопка ---
Button(main_frame, text="Получить курсы к USD", command=get_prices_to_usd,
       bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=20, pady=10).grid(row=4, column=1, pady=20)

# --- Создание меню ---
menu_bar = Menu(window)
window.config(menu=menu_bar)

# Меню "Источник"
source_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Источник", menu=source_menu)

# Добавляем все источники в меню
for source in DATA_SOURCES:
    source_menu.add_command(label=f"  {source}", command=lambda s=source: change_source_from_menu(s))

# Меню "Файл"
file_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Файл", menu=file_menu)
file_menu.add_command(label="Загрузить список валют", command=update_crypto_comboboxes)
file_menu.add_command(label="Получить курсы к USD", command=get_prices_to_usd)

file_menu.add_separator()
file_menu.add_command(label="Выход", command=window.quit)

# Меню "Справка"
help_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Справка", menu=help_menu)
help_menu.add_command(label="О программе", command=show_info)

# --- Инициализация ---
# Устанавливаем начальный источник и обновляем меню
update_source_menu()

# Автоматически загружаем список при старте
window.after(100, update_crypto_comboboxes)

window.mainloop()