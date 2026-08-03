from tkinter import *
from tkinter import ttk
from tkinter import messagebox as mb
import requests
import threading
import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

# Словари для хранения данных разных источников
crypto_data = {
    "CoinGecko": {
        "symbols": {},  # будет заполнено позже
        "names": {}
    },
    "CoinMarketCap": {
        "symbols": {},
        "names": {}
    }
}

# Доступные источники данных
DATA_SOURCES = ["CoinGecko", "CoinMarketCap"]


# --- Функции загрузки списков криптовалют ---

def load_coingecko_list():
    """Загружает список криптовалют с CoinGecko"""
    try:
        # CoinGecko API: получаем список всех криптовалют с ценами
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,  # ограничим до 100 для скорости
            "page": 1,
            "sparkline": "false"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Заполняем словарь
        symbols = {}
        names = {}
        for coin in data:
            symbol = coin['symbol'].upper()
            name = coin['name']
            symbols[symbol] = name
            # Для поиска по названию тоже добавляем
            names[name] = symbol

        crypto_data["CoinGecko"]["symbols"] = symbols
        crypto_data["CoinGecko"]["names"] = names
        return True

    except Exception as e:
        mb.showerror("Ошибка загрузки",
                     f"Не удалось загрузить список криптовалют с CoinGecko:\n{e}")
        return False


def load_coinmarketcap_list():
    """Загружает список криптовалют с CoinMarketCap"""
    try:
        # Берем ключ из переменных окружения
        API_KEY = os.getenv('CMC_API_KEY')

        # Проверяем, есть ли ключ
        if not API_KEY:
            mb.showerror("Ошибка",
                         "API ключ CoinMarketCap не найден!\n"
                         "Проверьте файл .env или переменную окружения CMC_API_KEY")
            return False

        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        headers = {
            "X-CMC_PRO_API_KEY": API_KEY
        }
        params = {
            "limit": 100,
            "convert": "USD"
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        # Заполняем словарь
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
        mb.showerror("Ошибка загрузки",
                     f"Не удалось загрузить список криптовалют с CoinMarketCap:\n{e}")
        return False


# --- Функция получения курса к USD ---

def get_price_to_usd(source, crypto_symbol):
    """Получает цену криптовалюты в USD из выбранного источника"""
    try:
        if source == "CoinGecko":
            # CoinGecko требует ID, а не символ
            # Ищем ID по символу
            coin_list_url = "https://api.coingecko.com/api/v3/coins/list"
            response = requests.get(coin_list_url)
            response.raise_for_status()
            all_coins = response.json()

            # Ищем ID для валюты
            coin_id = None
            for coin in all_coins:
                if coin['symbol'].upper() == crypto_symbol:
                    coin_id = coin['id']
                    break

            if not coin_id:
                return None, f"Валюта {crypto_symbol} не найдена"

            # Получаем цену в USD
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd"
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if coin_id not in data:
                return None, f"Цена для {crypto_symbol} не найдена"

            price_usd = data[coin_id]['usd']
            return price_usd, None

        elif source == "CoinMarketCap":
            # Берем ключ из переменных окружения
            API_KEY = os.getenv('CMC_API_KEY')

            if not API_KEY:
                return None, "API ключ CoinMarketCap не найден!"

            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
            headers = {"X-CMC_PRO_API_KEY": API_KEY}
            params = {
                "symbol": crypto_symbol,
                "convert": "USD"
            }
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if crypto_symbol not in data['data']:
                return None, f"Валюта {crypto_symbol} не найдена"

            price_usd = data['data'][crypto_symbol]['quote']['USD']['price']
            return price_usd, None

    except Exception as e:
        return None, f"Ошибка: {str(e)}"


# --- Функция обновления комбобоксов ---

def update_crypto_comboboxes():
    """Обновляет списки криптовалют в комбобоксах"""
    source = source_combobox.get()

    if source == "CoinGecko":
        # Загружаем список из CoinGecko
        if not load_coingecko_list():
            return
        symbols = list(crypto_data["CoinGecko"]["symbols"].keys())
    elif source == "CoinMarketCap":
        if not load_coinmarketcap_list():
            return
        symbols = list(crypto_data["CoinMarketCap"]["symbols"].keys())
    else:
        return

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

    # Получаем курсы в отдельном потоке, чтобы не замораживать интерфейс
    def get_rates():
        try:
            # Цена для первой криптовалюты
            price1, error1 = get_price_to_usd(source, crypto1_code)
            if error1:
                mb.showerror("Ошибка", error1)
                return

            # Цена для второй криптовалюты
            price2, error2 = get_price_to_usd(source, crypto2_code)
            if error2:
                mb.showerror("Ошибка", error2)
                return

            # Получаем названия
            crypto1_name = crypto_data[source]["symbols"].get(crypto1_code, crypto1_code)
            crypto2_name = crypto_data[source]["symbols"].get(crypto2_code, crypto2_code)

            # Показываем курсы к USD
            mb.showinfo("Курсы к USD",
                        f"1 {crypto1_name} ({crypto1_code}) = ${price1:.6f} USD\n"
                        f"1 {crypto2_name} ({crypto2_code}) = ${price2:.6f} USD")

        except Exception as e:
            mb.showerror("Ошибка", f"Произошла ошибка: {str(e)}")

    # Запускаем в отдельном потоке
    threading.Thread(target=get_rates, daemon=True).start()


# --- Создание GUI ---

window = Tk()
window.title("Курсы криптовалют к USD")
window.geometry("600x350")
window.resizable(False, False)

main_frame = Frame(window)
main_frame.pack(padx=20, pady=20, fill=BOTH, expand=True)

# --- Строка 0: Выбор источника ---
Label(main_frame, text="Источник данных:", font=("Arial", 10, "bold")).grid(row=0, column=0, pady=10, sticky="w")
source_combobox = ttk.Combobox(main_frame, values=DATA_SOURCES, state="readonly", width=20)
source_combobox.grid(row=0, column=1, pady=10, sticky="w")
source_combobox.set(DATA_SOURCES[0])  # Выбираем CoinGecko по умолчанию

# Кнопка загрузки списка валют
Button(main_frame, text="Загрузить список валют", command=update_crypto_comboboxes,
       bg="#4CAF50", fg="white").grid(row=0, column=2, padx=10, pady=10)

# --- Строка 1: Первая криптовалюта ---
Label(main_frame, text="Криптовалюта 1:").grid(row=1, column=0, pady=10, sticky="w")
crypto1_combobox = ttk.Combobox(main_frame, width=20)
crypto1_combobox.grid(row=1, column=1, pady=10, sticky="w")
crypto1_combobox.bind("<<ComboboxSelected>>", update_crypto1_label)
crypto1_combobox.bind("<KeyRelease>", update_crypto1_label)
c1_label = ttk.Label(main_frame, width=30)
c1_label.grid(row=1, column=2, pady=10, sticky="w")

# --- Строка 2: Вторая криптовалюта ---
Label(main_frame, text="Криптовалюта 2:").grid(row=2, column=0, pady=10, sticky="w")
crypto2_combobox = ttk.Combobox(main_frame, width=20)
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

# Автоматически загружаем список при старте
window.after(100, update_crypto_comboboxes)

window.mainloop()