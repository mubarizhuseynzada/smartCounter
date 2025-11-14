import serial
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====== Serial connection ======
arduino = serial.Serial('COM16', 9600, timeout=1)  # ← измени на свой порт!
time.sleep(2)

# ====== Thresholds ======
LIGHT_THRESHOLD = 300   # теперь счёт идёт, если light < LIGHT_THRESHOLD
GAS_THRESHOLD = 350
WATER_THRESHOLD = 400

# ====== Accumulators =====
total_light = 0
total_gas = 0
total_water = 0
last_payment_time = None

# Для хранения последних показаний
current_values = {"light":0, "gas":0, "water":0}
current_cardID = "NONE"

# =========================================================
#                          GUI
# =========================================================
root = tk.Tk()
root.title("Smart Counter Monitor")
root.geometry("480x320")
root.resizable(False, False)

style = ttk.Style()
style.configure("TLabel", font=("Segoe UI", 12))

title = ttk.Label(root, text="SMART COUNTER STATUS", font=("Segoe UI", 16, "bold"))
title.pack(pady=10)

frame = ttk.Frame(root)
frame.pack(pady=10)

# Sensor values
lbl_light = ttk.Label(frame, text="Light: 0")
lbl_light.grid(row=0, column=0, padx=20, pady=5)

lbl_gas = ttk.Label(frame, text="Gas: 0")
lbl_gas.grid(row=1, column=0, padx=20, pady=5)

lbl_water = ttk.Label(frame, text="Water: 0")
lbl_water.grid(row=2, column=0, padx=20, pady=5)

# Costs
lbl_cost_light = ttk.Label(frame, text="Light cost: 0.00 ₼")
lbl_cost_light.grid(row=0, column=1, padx=20, pady=5)

lbl_cost_gas = ttk.Label(frame, text="Gas cost: 0.00 ₼")
lbl_cost_gas.grid(row=1, column=1, padx=20, pady=5)

lbl_cost_water = ttk.Label(frame, text="Water cost: 0.00 ₼")
lbl_cost_water.grid(row=2, column=1, padx=20, pady=5)

# TOTAL
lbl_total = ttk.Label(root, text="TOTAL: 0.00 ₼", font=("Segoe UI", 15, "bold"))
lbl_total.pack(pady=10)

# RFID status
lbl_rfid = ttk.Label(root, text="RFID: Not detected", font=("Segoe UI", 12))
lbl_rfid.pack(pady=5)

# =========================================================
#                     Logic functions
# =========================================================
def analog_to_value(analog):
    return analog / 1023  # нормализация 0-1

def read_from_arduino():
    global total_light, total_gas, total_water, last_payment_time, current_values, current_cardID
    while True:
        try:
            line = arduino.readline().decode().strip()
            if line == "":
                continue

            parts = line.split(";")
            if len(parts) < 4:
                continue

            light = int(parts[0])
            gas = int(parts[1])
            water = int(parts[2])
            cardID = parts[3]

            current_values["light"] = light
            current_values["gas"] = gas
            current_values["water"] = water
            current_cardID = cardID

            # --- LIGHT ---
            if light < LIGHT_THRESHOLD:  # инвертированная логика
                unit = analog_to_value(light)
                if total_light <= 200:
                    total_light += unit * 0.084
                elif total_light <= 300:
                    total_light += unit * 0.10
                else:
                    total_light += unit * 0.15

            # --- GAS ---
            if gas > GAS_THRESHOLD:
                unit = analog_to_value(gas)
                if total_gas <= 1200:
                    total_gas += unit * 0.125
                elif total_gas <= 2200:
                    total_gas += unit * 0.20
                else:
                    total_gas += unit * 0.30

            # --- WATER ---
            if water > WATER_THRESHOLD:
                unit = analog_to_value(water)
                total_water += unit * 1.0

            # --- Payment by RFID ---
            if cardID != "NONE":
                total_light = 0
                total_gas = 0
                total_water = 0
                last_payment_time = datetime.now()

        except Exception as e:
            print("Arduino read error:", e)

# ================= Update GUI =================
def update_gui():
    global total_light, total_gas, total_water, current_values, current_cardID
    try:
        lbl_light.configure(text=f"Light: {current_values['light']}")
        lbl_gas.configure(text=f"Gas: {current_values['gas']}")
        lbl_water.configure(text=f"Water: {current_values['water']}")

        if current_cardID != "NONE":
            lbl_rfid.configure(text=f"RFID: {current_cardID}")
        else:
            lbl_rfid.configure(text="RFID: Not detected")

        lbl_cost_light.configure(text=f"Light cost: {total_light:.2f} ₼")
        lbl_cost_gas.configure(text=f"Gas cost: {total_gas:.2f} ₼")
        lbl_cost_water.configure(text=f"Water cost: {total_water:.2f} ₼")
        lbl_total.configure(text=f"TOTAL: {total_light + total_gas + total_water:.2f} ₼")
    except Exception as e:
        print("GUI update error:", e)
    root.after(200, update_gui)

# =========================================================
#                     Telegram bot
# =========================================================
BOT_TOKEN = "7978466946:AAF4gBpJRY0ZKFHVEE0l0lDUAU_JpVq30h8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я SmartCounter бот.\n"
        "Команды:\n"
        "/water - счёт за воду\n"
        "/gas - счёт за газ\n"
        "/light - счёт за свет\n"
        "/total - полный счёт\n"
        "/last_payment - информация о последней оплате"
    )

async def water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Вода:\n"
        f"Использовано: {current_values['water']:.2f} куб.м\n"
        f"Счёт с последней оплаты: {total_water:.2f} ₼"
    )

async def gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Газ:\n"
        f"Использовано: {current_values['gas']:.2f} куб.м\n"
        f"Счёт с последней оплаты: {total_gas:.2f} ₼"
    )

async def light(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Свет:\n"
        f"Использовано: {current_values['light']:.2f} условных кВт\n"
        f"Счёт с последней оплаты: {total_light:.2f} ₼"
    )

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_sum = total_light + total_gas + total_water
    await update.message.reply_text(
        f"Общий счёт с последней оплаты:\n"
        f"Свет: {total_light:.2f} ₼\n"
        f"Газ: {total_gas:.2f} ₼\n"
        f"Вода: {total_water:.2f} ₼\n"
        f"Итого: {total_sum:.2f} ₼"
    )

async def last_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if last_payment_time:
        await update.message.reply_text(
            f"Последняя оплата: {last_payment_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Счёт с последней оплаты:\n"
            f"Свет: {total_light:.2f} ₼, Газ: {total_gas:.2f} ₼, Вода: {total_water:.2f} ₼"
        )
    else:
        await update.message.reply_text("Оплата ещё не производилась.")

def run_telegram_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("water", water))
    app.add_handler(CommandHandler("gas", gas))
    app.add_handler(CommandHandler("light", light))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("last_payment", last_payment))
    print("Telegram bot running...")
    app.run_polling()

# =========================================================
#                     Main
# =========================================================
# Запускаем Arduino поток
threading.Thread(target=read_from_arduino, daemon=True).start()
# Запускаем Telegram поток
threading.Thread(target=run_telegram_bot, daemon=True).start()
# Запускаем GUI
update_gui()
root.mainloop()
