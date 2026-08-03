from tkinter import *
from tkinter import ttk
from tkinter import messagebox as mb
import requests
import threading
import time

# Словари для хранения данных разных источников
crypto_data = {
    "CoinGecko": {
        "symbols": {},  # будет заполнено позже
        "names": {}
    }
}

# Доступные источники данных (пока один, потом добавлю)
DATA_SOURCES = ["CoinGecko"]


# --- Функции загрузки списков криптовалют ---

def load_coingecko_list():
    """Загружает список криптовалют с CoinGecko"""
    try:
        time.sleep(2)  # ← Добавляем задержку 2 секунды перед запросом
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




# --- Функция получения курса ---

def get_exchange_rate(source, base_symbol, target_symbol):
    """Получает курс обмена из выбранного источника"""
    try:
        if source == "CoinGecko":
            # CoinGecko требует ID, а не символ
            # Ищем ID по символу
            coin_list_url = "https://api.coingecko.com/api/v3/coins/list"
            response = requests.get(coin_list_url)
            response.raise_for_status()
            all_coins = response.json()

            # Ищем ID для базовой и целевой валюты
            base_id = None
            target_id = None
            for coin in all_coins:
                if coin['symbol'].upper() == base_symbol:
                    base_id = coin['id']
                if coin['symbol'].upper() == target_symbol:
                    target_id = coin['id']
                if base_id and target_id:
                    break

            if not base_id or not target_id:
                return None, "Одна из валют не найдена"

            # Получаем курс
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": f"{base_id},{target_id}",
                "vs_currencies": "usd"
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if base_id not in data or target_id not in data:
                return None, "Курс не найден"

            base_price = data[base_id]['usd']
            target_price = data[target_id]['usd']
            rate = target_price / base_price
            return rate, None


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
    else:
        return

    # Обновляем все комбобоксы
    base_combobox['values'] = symbols
    base2_combobox['values'] = symbols
    target_combobox['values'] = symbols

    # Очищаем выбор
    base_combobox.set('')
    base2_combobox.set('')
    target_combobox.set('')

    # Очищаем метки
    b_label.config(text="")
    b2_label.config(text="")
    t_label.config(text="")


# --- Функции обновления меток с названиями ---

def update_base_label(event):
    code = base_combobox.get()
    source = source_combobox.get()
    if source in crypto_data and code in crypto_data[source]["symbols"]:
        b_label.config(text=crypto_data[source]["symbols"][code])
    else:
        b_label.config(text="")


def update_base2_label(event):
    code = base2_combobox.get()
    source = source_combobox.get()
    if source in crypto_data and code in crypto_data[source]["symbols"]:
        b2_label.config(text=crypto_data[source]["symbols"][code])
    else:
        b2_label.config(text="")


def update_target_label(event):
    code = target_combobox.get()
    source = source_combobox.get()
    if source in crypto_data and code in crypto_data[source]["symbols"]:
        t_label.config(text=crypto_data[source]["symbols"][code])
    else:
        t_label.config(text="")


# --- Функция получения курса  ---

def exchange():
    """Основная функция получения курса обмена"""
    source = source_combobox.get()
    base_code = base_combobox.get()
    base2_code = base2_combobox.get()
    target_code = target_combobox.get()

    if not all([source, base_code, base2_code, target_code]):
        mb.showwarning("Внимание", "Выберите источник и все три валюты")
        return

    # Получаем курсы в отдельном потоке, чтобы не замораживать интерфейс
    def get_rates():
        try:
            # Курс для первой базовой валюты
            rate1, error1 = get_exchange_rate(source, base_code, target_code)
            if error1:
                mb.showerror("Ошибка", error1)
                return

            # Курс для второй базовой валюты
            rate2, error2 = get_exchange_rate(source, base2_code, target_code)
            if error2:
                mb.showerror("Ошибка", error2)
                return

            # Получаем названия
            base_name = crypto_data[source]["symbols"].get(base_code, base_code)
            base2_name = crypto_data[source]["symbols"].get(base2_code, base2_code)
            target_name = crypto_data[source]["symbols"].get(target_code, target_code)

            mb.showinfo("Курс обмена",
                        f"1 {base_name} = {rate1:.6f} {target_name}\n"
                        f"1 {base2_name} = {rate2:.6f} {target_name}")

        except Exception as e:
            mb.showerror("Ошибка", f"Произошла ошибка: {str(e)}")

    # Запускаем в отдельном потоке
    threading.Thread(target=get_rates, daemon=True).start()


# --- Создание GUI ---

window = Tk()
window.title("Курс криптовалют")
window.geometry("600x400")
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

# --- Строка 1: Базовая валюта 1 ---
Label(main_frame, text="Базовая валюта 1:").grid(row=1, column=0, pady=10, sticky="w")
base_combobox = ttk.Combobox(main_frame, width=20)
base_combobox.grid(row=1, column=1, pady=10, sticky="w")
base_combobox.bind("<<ComboboxSelected>>", update_base_label)
base_combobox.bind("<KeyRelease>", update_base_label)
b_label = ttk.Label(main_frame, width=30)
b_label.grid(row=1, column=2, pady=10, sticky="w")

# --- Строка 2: Базовая валюта 2 ---
Label(main_frame, text="Базовая валюта 2:").grid(row=2, column=0, pady=10, sticky="w")
base2_combobox = ttk.Combobox(main_frame, width=20)
base2_combobox.grid(row=2, column=1, pady=10, sticky="w")
base2_combobox.bind("<<ComboboxSelected>>", update_base2_label)
base2_combobox.bind("<KeyRelease>", update_base2_label)
b2_label = ttk.Label(main_frame, width=30)
b2_label.grid(row=2, column=2, pady=10, sticky="w")

# --- Строка 3: Целевая валюта ---
Label(main_frame, text="Целевая валюта:").grid(row=3, column=0, pady=10, sticky="w")
target_combobox = ttk.Combobox(main_frame, width=20)
target_combobox.grid(row=3, column=1, pady=10, sticky="w")
target_combobox.bind("<<ComboboxSelected>>", update_target_label)
target_combobox.bind("<KeyRelease>", update_target_label)
t_label = ttk.Label(main_frame, width=30)
t_label.grid(row=3, column=2, pady=10, sticky="w")

# --- Строка 4: Кнопка ---
Button(main_frame, text="Получить курс обмена", command=exchange,
       bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=20, pady=10).grid(row=4, column=1, pady=20)

# Автоматически загружаем список при старте
window.after(100, update_crypto_comboboxes)

window.mainloop()