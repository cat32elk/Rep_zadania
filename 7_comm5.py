from tkinter import *
from tkinter import ttk
from tkinter import messagebox as mb
from tkinter import filedialog
import requests
import threading
import os
import json
import time
from datetime import datetime, timedelta
import hashlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates

# --- НАСТРОЙКИ ---
# 5 популярных криптовалют (ID для CoinGecko)
POPULAR_COINS = [
    {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
    {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
    {"id": "solana", "symbol": "SOL", "name": "Solana"},
    {"id": "cardano", "symbol": "ADA", "name": "Cardano"},
    {"id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin"}
]

# Периоды для исторических данных
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
    "prices": 300,  # 5 минут
    "historical": 3600,  # 1 час
    "ohlc": 3600  # 1 час
}

# Кэш для цен (в памяти)
PRICE_CACHE = {}
HISTORICAL_CACHE = {}

# Словарь для хранения данных
crypto_data = {
    "symbols": {},
    "names": {}
}


# --- ФУНКЦИИ КЭШИРОВАНИЯ ---

def get_cache_filename(data_type, *args):
    """Создает уникальное имя файла для кэша"""
    key = f"{data_type}_{'_'.join(str(arg) for arg in args)}"
    hash_key = hashlib.md5(key.encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{data_type}_{hash_key}.json")


def load_from_cache(cache_file, max_age):
    """Загружает данные из кэша, если они не устарели"""
    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:  # Проверка на пустой файл
                print(f"⚠ Кэш-файл пуст: {cache_file}")
                return None

            cache_data = json.loads(content)
            timestamp = cache_data.get('timestamp', 0)
            age = time.time() - timestamp

            if age < max_age:
                return cache_data.get('data')
            else:
                # Кэш устарел, удаляем файл
                try:
                    os.remove(cache_file)
                except:
                    pass
                return None

    except json.JSONDecodeError as e:
        # Файл повреждён - удаляем его
        print(f"⚠ Ошибка JSON в кэше: {e}. Удаляем файл {cache_file}")
        try:
            os.remove(cache_file)
        except:
            pass
        return None

    except Exception as e:
        print(f"⚠ Ошибка чтения кэша: {e}")
        return None


def save_to_cache(cache_file, data):
    """Сохраняет данные в кэш"""
    try:
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        # Используем временный файл для атомарной записи
        temp_file = cache_file + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Принудительная запись на диск

        # Переименовываем (атомарно)
        os.replace(temp_file, cache_file)
        return True

    except Exception as e:
        print(f"⚠ Ошибка сохранения кэша: {e}")
        return False


def make_request_with_retry(url, params, max_retries=3, delay=5):
    """
    Выполняет запрос с повторными попытками при ошибке 429
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 429:
                wait_time = delay * (attempt + 1)
                print(f"⚠ Ошибка 429. Пауза {wait_time} сек... (попытка {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"⚠ Ошибка: {e}. Повтор через {delay} сек...")
                time.sleep(delay)
            else:
                print(f"✗ Ошибка после {max_retries} попыток: {e}")
                return None

    return None


# --- ЗАГРУЗКА СПИСКА 5 ПОПУЛЯРНЫХ КРИПТОВАЛЮТ ---

def load_popular_coins():
    """Загружает список 5 популярных криптовалют"""
    crypto_data["symbols"] = {}
    crypto_data["names"] = {}

    for coin in POPULAR_COINS:
        symbol = coin["symbol"]
        name = coin["name"]
        crypto_data["symbols"][symbol] = name
        crypto_data["names"][name] = symbol

    return True


# --- ФУНКЦИЯ ПОЛУЧЕНИЯ ТЕКУЩЕГО КУРСА ---

def get_price_to_usd(crypto_symbol):
    """Получает цену криптовалюты в USD из CoinGecko с кэшированием"""
    cache_key = f"coingecko_{crypto_symbol}"

    # Проверяем кэш в памяти
    if cache_key in PRICE_CACHE:
        cached_time, cached_price = PRICE_CACHE[cache_key]
        if time.time() - cached_time < 120:  # 2 минуты
            return cached_price, None

    try:
        # Находим ID монеты
        coin_id = None
        for coin in POPULAR_COINS:
            if coin["symbol"] == crypto_symbol:
                coin_id = coin["id"]
                break

        if not coin_id:
            return None, f"Валюта {crypto_symbol} не найдена"

        time.sleep(1.5)

        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}

        data = make_request_with_retry(url, params)
        if not data:
            return None, "Ошибка получения данных"

        if coin_id not in data:
            return None, f"Цена для {crypto_symbol} не найдена"

        price = data[coin_id]['usd']

        # Сохраняем в кэш
        PRICE_CACHE[cache_key] = (time.time(), price)

        return price, None

    except Exception as e:
        return None, f"Ошибка: {str(e)}"


# --- ФУНКЦИЯ ПОЛУЧЕНИЯ ИСТОРИЧЕСКИХ ДАННЫХ ---

def get_historical_data(crypto_symbol, days=30):
    """Получает исторические данные криптовалюты за указанный период"""
    cache_key = f"historical_{crypto_symbol}_{days}"

    # Проверяем кэш в памяти
    if cache_key in HISTORICAL_CACHE:
        cached_time, cached_data = HISTORICAL_CACHE[cache_key]
        if time.time() - cached_time < 3600:  # 1 час
            return cached_data, None

    try:
        # Находим ID монеты
        coin_id = None
        for coin in POPULAR_COINS:
            if coin["symbol"] == crypto_symbol:
                coin_id = coin["id"]
                break

        if not coin_id:
            return None, f"Валюта {crypto_symbol} не найдена"

        # Проверяем кэш на диске
        cache_file = get_cache_filename("historical", coin_id, days)
        cached_data = load_from_cache(cache_file, CACHE_TIMES["historical"])
        if cached_data is not None:
            HISTORICAL_CACHE[cache_key] = (time.time(), cached_data)
            return cached_data, None

        time.sleep(1.5)

        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily"
        }

        data = make_request_with_retry(url, params)
        if not data:
            return None, "Ошибка получения исторических данных"

        prices = data.get('prices', [])

        historical_data = []
        for timestamp, price in prices:
            date = datetime.fromtimestamp(timestamp / 1000)
            historical_data.append({
                'date': date,
                'price': price
            })

        # Сохраняем в кэш
        HISTORICAL_CACHE[cache_key] = (time.time(), historical_data)
        save_to_cache(cache_file, historical_data)

        return historical_data, None

    except Exception as e:
        return None, f"Ошибка: {str(e)}"


# --- ФУНКЦИЯ ПОСТРОЕНИЯ ГРАФИКОВ ---

def plot_chart(historical_data, crypto_symbol, crypto_name, days):
    """Строит график исторических данных в новом окне"""
    if not historical_data:
        mb.showerror("Ошибка", "Нет данных для построения графика")
        return

    # Создаем новое окно
    chart_window = Toplevel(window)
    chart_window.title(f"{crypto_name} ({crypto_symbol}) - График за {days} дней")
    chart_window.geometry("800x500")

    # Создаем фигуру
    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.add_subplot(111)

    # Подготавливаем данные
    dates = [item['date'] for item in historical_data]
    prices = [item['price'] for item in historical_data]

    # Строим график
    ax.plot(dates, prices, linewidth=2, color='#2196F3')

    # Настройки графика
    ax.set_title(f'{crypto_name} ({crypto_symbol}) - Цена за {days} дней', fontsize=14, fontweight='bold')
    ax.set_xlabel('Дата', fontsize=10)
    ax.set_ylabel('Цена (USD)', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    # Добавляем информацию о ценах
    min_price = min(prices)
    max_price = max(prices)
    current_price = prices[-1]
    start_price = prices[0]
    change = ((current_price - start_price) / start_price) * 100

    info_text = f'Текущая: ${current_price:,.2f}\nМин: ${min_price:,.2f}\nМакс: ${max_price:,.2f}\nИзменение: {change:+.2f}%'
    ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

    # Встраиваем график в Tkinter
    canvas = FigureCanvasTkAgg(fig, master=chart_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    # Кнопка сохранения
    def save_chart():
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG файлы", "*.png"), ("Все файлы", "*.*")],
            initialfile=f"{crypto_symbol}_{days}days_{datetime.now().strftime('%Y%m%d')}.png"
        )
        if file_path:
            fig.savefig(file_path, dpi=300, bbox_inches='tight')
            mb.showinfo("Успех", f"График сохранен как:\n{file_path}")

    Button(chart_window, text="Сохранить график", command=save_chart,
           bg="#4CAF50", fg="white", padx=20, pady=5).pack(pady=10)


def show_historical_chart():
    """Показывает исторический график для выбранной криптовалюты"""
    crypto_code = crypto1_combobox.get()
    period = period_combobox.get()

    if not crypto_code:
        mb.showwarning("Внимание", "Выберите криптовалюту")
        return

    if not period:
        mb.showwarning("Внимание", "Выберите период")
        return

    days = PERIODS[period]
    crypto_name = crypto_data["symbols"].get(crypto_code, crypto_code)

    loading_label.config(text=f"⏳ Загрузка исторических данных для {crypto_code}...")
    window.update()

    def get_and_plot():
        try:
            data, error = get_historical_data(crypto_code, days)
            if error:
                loading_label.config(text="❌ Ошибка")
                mb.showerror("Ошибка", error)
                return

            loading_label.config(text="✅ Готово")

            # Строим график в новом окне
            plot_chart(data, crypto_code, crypto_name, days)

        except Exception as e:
            loading_label.config(text="❌ Ошибка")
            mb.showerror("Ошибка", f"Произошла ошибка: {str(e)}")

    threading.Thread(target=get_and_plot, daemon=True).start()


def show_comparison_chart():
    """Показывает сравнительный график двух криптовалют"""
    crypto1_code = crypto1_combobox.get()
    crypto2_code = crypto2_combobox.get()
    period = period_combobox.get()

    if not all([crypto1_code, crypto2_code]):
        mb.showwarning("Внимание", "Выберите обе криптовалюты")
        return

    if not period:
        mb.showwarning("Внимание", "Выберите период")
        return

    days = PERIODS[period]
    crypto1_name = crypto_data["symbols"].get(crypto1_code, crypto1_code)
    crypto2_name = crypto_data["symbols"].get(crypto2_code, crypto2_code)

    loading_label.config(text=f"⏳ Загрузка данных для сравнения...")
    window.update()

    def get_and_plot():
        try:
            # Получаем данные для обеих валют
            data1, error1 = get_historical_data(crypto1_code, days)
            if error1:
                loading_label.config(text="❌ Ошибка")
                mb.showerror("Ошибка", f"Ошибка для {crypto1_code}: {error1}")
                return

            data2, error2 = get_historical_data(crypto2_code, days)
            if error2:
                loading_label.config(text="❌ Ошибка")
                mb.showerror("Ошибка", f"Ошибка для {crypto2_code}: {error2}")
                return

            loading_label.config(text="✅ Готово")

            # Создаем окно для сравнительного графика
            chart_window = Toplevel(window)
            chart_window.title(f"Сравнение {crypto1_code} и {crypto2_code} за {days} дней")
            chart_window.geometry("900x550")

            fig = Figure(figsize=(9, 5), dpi=100)
            ax = fig.add_subplot(111)

            # Нормализуем данные для сравнения
            dates1 = [item['date'] for item in data1]
            prices1 = [item['price'] for item in data1]
            dates2 = [item['date'] for item in data2]
            prices2 = [item['price'] for item in data2]

            # Нормализация (приводим к 100% для сравнения динамики)
            norm_prices1 = [p / prices1[0] * 100 for p in prices1]
            norm_prices2 = [p / prices2[0] * 100 for p in prices2]

            # Строим графики
            ax.plot(dates1, norm_prices1, linewidth=2, color='#2196F3', label=f'{crypto1_code} ({crypto1_name})')
            ax.plot(dates2, norm_prices2, linewidth=2, color='#FF9800', label=f'{crypto2_code} ({crypto2_name})')

            ax.set_title(f'Сравнение динамики {crypto1_code} и {crypto2_code} за {days} дней\n(нормализовано к 100%)',
                         fontsize=14, fontweight='bold')
            ax.set_xlabel('Дата', fontsize=10)
            ax.set_ylabel('Изменение (%)', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            # Добавляем информацию
            change1 = ((prices1[-1] - prices1[0]) / prices1[0]) * 100
            change2 = ((prices2[-1] - prices2[0]) / prices2[0]) * 100

            info_text = f'{crypto1_code}: {change1:+.2f}%\n{crypto2_code}: {change2:+.2f}%'
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=10,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

            canvas = FigureCanvasTkAgg(fig, master=chart_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=BOTH, expand=True)

            def save_chart():
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG файлы", "*.png"), ("Все файлы", "*.*")],
                    initialfile=f"compare_{crypto1_code}_{crypto2_code}_{days}days_{datetime.now().strftime('%Y%m%d')}.png"
                )
                if file_path:
                    fig.savefig(file_path, dpi=300, bbox_inches='tight')
                    mb.showinfo("Успех", f"График сохранен как:\n{file_path}")

            Button(chart_window, text="Сохранить график", command=save_chart,
                   bg="#4CAF50", fg="white", padx=20, pady=5).pack(pady=10)

        except Exception as e:
            loading_label.config(text="❌ Ошибка")
            mb.showerror("Ошибка", f"Произошла ошибка: {str(e)}")

    threading.Thread(target=get_and_plot, daemon=True).start()


# --- ФУНКЦИИ GUI ---

def update_crypto_comboboxes():
    """Обновляет списки криптовалют в комбобоксах"""
    load_popular_coins()

    symbols = list(crypto_data["symbols"].keys())

    crypto1_combobox['values'] = symbols
    crypto2_combobox['values'] = symbols

    crypto1_combobox.set('')
    crypto2_combobox.set('')
    period_combobox.set('30 дней')  # Устанавливаем период по умолчанию

    c1_label.config(text="")
    c2_label.config(text="")
    loading_label.config(text=f"✅ Загружено {len(symbols)} популярных криптовалют")

    coins_list = "\n".join([f"• {symbol}: {name}" for symbol, name in crypto_data["symbols"].items()])
    info_label.config(text=f"Доступные валюты:\n{coins_list}")


def update_crypto1_label(event):
    code = crypto1_combobox.get()
    if code in crypto_data["symbols"]:
        c1_label.config(text=crypto_data["symbols"][code])
    else:
        c1_label.config(text="")


def update_crypto2_label(event):
    code = crypto2_combobox.get()
    if code in crypto_data["symbols"]:
        c2_label.config(text=crypto_data["symbols"][code])
    else:
        c2_label.config(text="")


def get_prices_to_usd():
    """Основная функция получения текущих курсов"""
    crypto1_code = crypto1_combobox.get()
    crypto2_code = crypto2_combobox.get()

    if not all([crypto1_code, crypto2_code]):
        mb.showwarning("Внимание", "Выберите обе криптовалюты")
        return

    loading_label.config(text="⏳ Получение курсов...")
    window.update()

    def get_rates():
        try:
            price1, error1 = get_price_to_usd(crypto1_code)
            if error1:
                loading_label.config(text="❌ Ошибка")
                mb.showerror("Ошибка", error1)
                return

            price2, error2 = get_price_to_usd(crypto2_code)
            if error2:
                loading_label.config(text="❌ Ошибка")
                mb.showerror("Ошибка", error2)
                return

            crypto1_name = crypto_data["symbols"].get(crypto1_code, crypto1_code)
            crypto2_name = crypto_data["symbols"].get(crypto2_code, crypto2_code)

            loading_label.config(text="✅ Готово")

            mb.showinfo("Курсы к USD (CoinGecko)",
                        f"📊 1 {crypto1_name} ({crypto1_code}) = ${price1:.6f} USD\n"
                        f"📊 1 {crypto2_name} ({crypto2_code}) = ${price2:.6f} USD\n\n"
                        f"🕐 Обновлено: {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            loading_label.config(text="❌ Ошибка")
            mb.showerror("Ошибка", f"Произошла ошибка: {str(e)}")

    threading.Thread(target=get_rates, daemon=True).start()


def show_guide():
    """Показывает руководство оператора"""
    guide_text = """
📖 РУКОВОДСТВО ОПЕРАТОРА

1. ОБЩИЕ СВЕДЕНИЯ
Программа для получения курсов 5 популярных криптовалют к USD.
Источник данных: CoinGecko API.

2. ДОСТУПНЫЕ ВАЛЮТЫ
• BTC - Bitcoin
• ETH - Ethereum  
• SOL - Solana
• ADA - Cardano
• DOGE - Dogecoin

3. ОСНОВНЫЕ ФУНКЦИИ
▶ Текущие курсы - показывает цены выбранных валют
▶ 📈 История - строит график изменения цены
▶ 📊 Сравнение - сравнивает две валюты
▶ Загрузить список - обновляет список валют
▶ Очистить кэш - удаляет сохраненные данные

4. КАК ПОЛЬЗОВАТЬСЯ

А. Получить текущие курсы:
1. Выберите Криптовалюту 1
2. Выберите Криптовалюту 2
3. Нажмите "Текущие курсы"

Б. Посмотреть историю:
1. Выберите Криптовалюту 1
2. Выберите Период (7, 14, 30, 90 дней)
3. Нажмите "📈 История"

В. Сравнить две валюты:
1. Выберите Криптовалюту 1
2. Выберите Криптовалюту 2
3. Выберите Период
4. Нажмите "📊 Сравнение"

5. СОХРАНЕНИЕ ГРАФИКОВ
В окне с графиком нажмите "Сохранить график".
Файл сохраняется в формате PNG.

6. ВОЗМОЖНЫЕ ОШИБКИ
• Ошибка 429 - подождите 30-60 секунд
• Нет данных - проверьте интернет
• Валюта не найдена - нажмите "Загрузить список"

7. ГОРЯЧИЕ КЛАВИШИ
• Alt+F - меню "Файл"
• Alt+H - меню "Справка"
• Esc - закрыть окно

💡 Совет: Начинайте с периода 30 дней - он дает хорошее представление о тренде.

"""
    mb.showinfo("📖 Как работать", guide_text)


def show_info():
    mb.showinfo("О программе",
                "📊 КУРСЫ КРИПТОВАЛЮТ К USD\n\n"
                "🪙 5 популярных криптовалют:\n"
                "• Bitcoin (BTC)\n"
                "• Ethereum (ETH)\n"
                "• Solana (SOL)\n"
                "• Cardano (ADA)\n"
                "• Dogecoin (DOGE)\n\n"
                "📡 Источник данных:\n"
                "• CoinGecko\n\n"
                "📈 Возможности:\n"
                "• Текущие курсы\n"
                "• Исторические графики\n"
                "• Сравнение двух валют\n"
                "• Сохранение графиков\n\n"
                "⚡ Особенности:\n"
                "• Кэширование данных\n"
                "• Защита от ошибки 429\n"
                "• Автоматические повторные попытки\n\n"
                "💡 Бесплатно, без API-ключей!\n\n"
                )


def clear_cache_files():
    """Очищает кэш"""
    try:
        if os.path.exists(CACHE_DIR):
            count = 0
            for file in os.listdir(CACHE_DIR):
                file_path = os.path.join(CACHE_DIR, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    count += 1
            PRICE_CACHE.clear()
            HISTORICAL_CACHE.clear()
            mb.showinfo("Успех", f"Кэш очищен! Удалено {count} файлов")
        else:
            mb.showinfo("Информация", "Кэш пуст")
    except Exception as e:
        mb.showerror("Ошибка", f"Не удалось очистить кэш: {e}")


# --- СОЗДАНИЕ GUI ---

window = Tk()
window.title("Курсы 5-ти популярных криптовалют к USD (CoinGecko + История)")
window.geometry("650x450")
window.resizable(False, False)

main_frame = Frame(window)
main_frame.pack(padx=20, pady=20, fill=BOTH, expand=True)

# --- Заголовок ---
Label(main_frame, text="CoinGecko - Анализ 5 популярных криптовалют",
      font=("Arial", 12, "bold"), fg="#2196F3").grid(row=0, column=0, columnspan=4, pady=5)

# --- Строка 1: Индикатор загрузки ---
loading_label = Label(main_frame, text="", font=("Arial", 9), fg="blue")
loading_label.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")

# --- Строка 2: Первая криптовалюта ---
Label(main_frame, text="Криптовалюта 1:", font=("Arial", 10)).grid(row=2, column=0, pady=5, sticky="w")
crypto1_combobox = ttk.Combobox(main_frame, width=15, state="readonly")
crypto1_combobox.grid(row=2, column=1, pady=5, sticky="w")
crypto1_combobox.bind("<<ComboboxSelected>>", update_crypto1_label)
c1_label = ttk.Label(main_frame, width=20, font=("Arial", 9))
c1_label.grid(row=2, column=2, pady=5, sticky="w")

# --- Строка 3: Вторая криптовалюта ---
Label(main_frame, text="Криптовалюта 2:", font=("Arial", 10)).grid(row=3, column=0, pady=5, sticky="w")
crypto2_combobox = ttk.Combobox(main_frame, width=15, state="readonly")
crypto2_combobox.grid(row=3, column=1, pady=5, sticky="w")
crypto2_combobox.bind("<<ComboboxSelected>>", update_crypto2_label)
c2_label = ttk.Label(main_frame, width=20, font=("Arial", 9))
c2_label.grid(row=3, column=2, pady=5, sticky="w")

# --- Строка 4: Выбор периода ---
Label(main_frame, text="Период:", font=("Arial", 10)).grid(row=4, column=0, pady=5, sticky="w")
period_combobox = ttk.Combobox(main_frame, values=list(PERIODS.keys()), width=15, state="readonly")
period_combobox.grid(row=4, column=1, pady=5, sticky="w")
period_combobox.set("30 дней")

# --- Строка 5: Кнопки ---
button_frame = Frame(main_frame)
button_frame.grid(row=5, column=0, columnspan=4, pady=10)

Button(button_frame, text="Текущие курсы", command=get_prices_to_usd,
       bg="#2196F3", fg="white", font=("Arial", 9), padx=12, pady=6).pack(side=LEFT, padx=3)

Button(button_frame, text="📈 История", command=show_historical_chart,
       bg="#4CAF50", fg="white", font=("Arial", 9), padx=12, pady=6).pack(side=LEFT, padx=3)

Button(button_frame, text="📊 Сравнение", command=show_comparison_chart,
       bg="#FF9800", fg="white", font=("Arial", 9), padx=12, pady=6).pack(side=LEFT, padx=3)

Button(button_frame, text="Загрузить список", command=update_crypto_comboboxes,
       bg="#9C27B0", fg="white", font=("Arial", 9), padx=10, pady=6).pack(side=LEFT, padx=3)

Button(button_frame, text="Очистить кэш", command=clear_cache_files,
       bg="#F44336", fg="white", font=("Arial", 9), padx=10, pady=6).pack(side=LEFT, padx=3)

# --- Строка 6: Информация о доступных валютах ---
info_label = Label(main_frame, text="", font=("Arial", 9), fg="gray", justify=LEFT)
info_label.grid(row=6, column=0, columnspan=4, pady=10, sticky="w")

# --- Строка 7: Статус ---
status_label = Label(main_frame, text="💡 Выберите валюты и период, затем нажмите нужную кнопку",
                     font=("Arial", 8), fg="gray")
status_label.grid(row=7, column=0, columnspan=4, pady=5)

# --- Создание меню ---
menu_bar = Menu(window)
window.config(menu=menu_bar)

# Меню "Файл"
file_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Файл", menu=file_menu)
file_menu.add_command(label="Загрузить список", command=update_crypto_comboboxes)
file_menu.add_command(label="Текущие курсы", command=get_prices_to_usd)
file_menu.add_command(label="Исторический график", command=show_historical_chart)
file_menu.add_command(label="Сравнение", command=show_comparison_chart)
file_menu.add_separator()
file_menu.add_command(label="Очистить кэш", command=clear_cache_files)
file_menu.add_separator()
file_menu.add_command(label="Выход", command=window.quit)

# Меню "Справка"
help_menu = Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="Справка", menu=help_menu)
help_menu.add_command(label="Как работать", command=show_guide)
help_menu.add_command(label="О программе", command=show_info)

# --- Инициализация ---
window.after(100, update_crypto_comboboxes)

window.mainloop()