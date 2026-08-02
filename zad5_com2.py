from tkinter import *
from tkinter import ttk
from tkinter import messagebox as mb
import requests


def update_base_label(event):
    code = base_combobox.get()
    if code in currencies:
        b_label.config(text=currencies[code])
    else:
        b_label.config(text="")


def update_base2_label(event):
    code = base2_combobox.get()
    if code in currencies:
        b2_label.config(text=currencies[code])
    else:
        b2_label.config(text="")


def update_target_label(event):
    code = target_combobox.get()
    if code in currencies:
        t_label.config(text=currencies[code])
    else:
        t_label.config(text="")


def exchange():
    target_code = target_combobox.get()
    base_code = base_combobox.get()
    base2_code = base2_combobox.get()

    if not (target_code and base_code and base2_code):
        mb.showwarning("Внимание", "Выберите все три валюты")
        return

    try:
        # Запрос для первой валюты
        response = requests.get(f'https://open.er-api.com/v6/latest/{base_code}')
        response.raise_for_status()
        data = response.json()

        if 'rates' not in data or target_code not in data['rates']:
            mb.showerror("Ошибка", f"Валюта {target_code} не найдена")
            return

        rate1 = data['rates'][target_code]
        base_name = currencies[base_code]
        target_name = currencies[target_code]

        # Запрос для второй валюты
        response2 = requests.get(f'https://open.er-api.com/v6/latest/{base2_code}')
        response2.raise_for_status()
        data2 = response2.json()

        if 'rates' not in data2 or target_code not in data2['rates']:
            mb.showerror("Ошибка", f"Валюта {target_code} не найдена")
            return

        rate2 = data2['rates'][target_code]
        base2_name = currencies[base2_code]

        mb.showinfo("Курс обмена",
                    f"1 {base_name} = {rate1:.4f} {target_name}\n"
                    f"1 {base2_name} = {rate2:.4f} {target_name}")

    except requests.exceptions.RequestException as e:
        mb.showerror("Ошибка сети", f"Не удалось получить данные: {e}")
    except Exception as e:
        mb.showerror("Ошибка", f"Произошла ошибка: {e}")


currencies = {
    "USD": "Американский доллар",
    "EUR": "Евро",
    "JPY": "Японская йена",
    "GBP": "Британский фунт стерлингов",
    "AUD": "Австралийский доллар",
    "CAD": "Канадский доллар",
    "CHF": "Швейцарский франк",
    "CNY": "Китайский юань",
    "RUB": "Российский рубль",
    "KZT": "Казахстанский тенге",
    "UZS": "Узбекский сум"
}

window = Tk()
window.title("Курс обмена валюты")
window.geometry("360x400")

Label(text="Базовая валюта 1:").pack(padx=10, pady=5)
base_combobox = ttk.Combobox(values=list(currencies.keys()))
base_combobox.pack(padx=10, pady=5)
base_combobox.bind("<<ComboboxSelected>>", update_base_label)
base_combobox.bind("<KeyRelease>", update_base_label)
b_label = ttk.Label()
b_label.pack(padx=10, pady=5)

Label(text="Базовая валюта 2:").pack(padx=10, pady=5)
base2_combobox = ttk.Combobox(values=list(currencies.keys()))
base2_combobox.pack(padx=10, pady=5)
base2_combobox.bind("<<ComboboxSelected>>", update_base2_label)
base2_combobox.bind("<KeyRelease>", update_base2_label)
b2_label = ttk.Label()
b2_label.pack(padx=10, pady=5)

Label(text="Целевая валюта:").pack(padx=10, pady=5)
target_combobox = ttk.Combobox(values=list(currencies.keys()))
target_combobox.pack(padx=10, pady=5)
target_combobox.bind("<<ComboboxSelected>>", update_target_label)
target_combobox.bind("<KeyRelease>", update_target_label)
t_label = ttk.Label()
t_label.pack(padx=10, pady=5)

Button(text="Получить курс обмена", command=exchange).pack(padx=10, pady=10)
window.mainloop()