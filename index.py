import serial
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ====== Serial connection with Arduino ======
arduino = serial.Serial('COM16', 9600, timeout=1)  # ← change to your port
time.sleep(2)

# ====== Thresholds ======
LIGHT_THRESHOLD = 300   # Light counting starts when value < threshold
GAS_THRESHOLD = 350
WATER_THRESHOLD = 400

# ====== Accumulators ======
total_light = 0
total_gas = 0
total_water = 0
last_payment_time = None

# Store last sensor readings
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

# Sensor values labels
lbl_light = ttk.Label(frame, text="Light: 0")
lbl_light.grid(row=0, column=0, padx=20, pady=5)

lbl_gas = ttk.Label(frame, text="Gas: 0")
lbl_gas.grid(row=1, column=0, padx=20, pady=5)

lbl_water = ttk.Label(frame, text="Water: 0")
lbl_water.grid(row=2, column=0, padx=20, pady=5)

# Costs labels
lbl_cost_light = ttk.Label(frame, text="Light cost: 0.00 ₼")
lbl_cost_light.grid(row=0, column=1, padx=20, pady=5)

lbl_cost_gas = ttk.Label(frame, text="Gas cost: 0.00 ₼")
lbl_cost_gas.grid(row=1, column=1, padx=20, pady=5)

lbl_cost_water = ttk.Label(frame, text="Water cost: 0.00 ₼")
lbl_cost_water.grid(row=2, column=1, padx=20, pady=5)

# TOTAL cost
lbl_total = ttk.Label(root, text="TOTAL: 0.00 ₼", font=("Segoe UI", 15, "bold"))
lbl_total.pack(pady=10)

# RFID status
lbl_rfid = ttk.Label(root, text="RFID: Not detected", font=("Segoe UI", 12))
lbl_rfid.pack(pady=5)

# =========================================================
#                     Logic functions
# =========================================================
def analog_to_value(analog):
    return analog / 1023  # normalize 0-1

def read_from_arduino():
    """ Continuously read data from Arduino and update counters """
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

            # --- LIGHT calculation ---
            if light < LIGHT_THRESHOLD:  # inverted logic
                unit = analog_to_value(light)
                if total_light <= 200:
                    total_light += unit * 0.084
                elif total_light <= 300:
                    total_light += unit * 0.10
                else:
                    total_light += unit * 0.15

            # --- GAS calculation ---
            if gas > GAS_THRESHOLD:
                unit = analog_to_value(gas)
                if total_gas <= 1200:
                    total_gas += unit * 0.125
                elif total_gas <= 2200:
                    total_gas += unit * 0.20
                else:
                    total_gas += unit * 0.30

            # --- WATER calculation ---
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
    """ Update the Tkinter GUI with current values """
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
    """ Respond to /start command """
    await update.message.reply_text(
        "Hello! I am SmartCounter bot.\n"
        "Commands:\n"
        "/water - show water bill\n"
        "/gas - show gas bill\n"
        "/light - show light bill\n"
        "/total - show total bill\n"
        "/last_payment - show last payment info"
    )

async def water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Respond to /water command """
    await update.message.reply_text(
        f"Water:\n"
        f"Used: {current_values['water']:.2f} m³\n"
        f"Bill since last payment: {total_water:.2f} ₼"
    )

async def gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Respond to /gas command """
    await update.message.reply_text(
        f"Gas:\n"
        f"Used: {current_values['gas']:.2f} m³\n"
        f"Bill since last payment: {total_gas:.2f} ₼"
    )

async def light(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Respond to /light command """
    await update.message.reply_text(
        f"Light:\n"
        f"Used: {current_values['light']:.2f} kWh\n"
        f"Bill since last payment: {total_light:.2f} ₼"
    )

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Respond to /total command """
    total_sum = total_light + total_gas + total_water
    await update.message.reply_text(
        f"Total bill since last payment:\n"
        f"Light: {total_light:.2f} ₼\n"
        f"Gas: {total_gas:.2f} ₼\n"
        f"Water: {total_water:.2f} ₼\n"
        f"Total: {total_sum:.2f} ₼"
    )

async def last_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Respond to /last_payment command """
    if last_payment_time:
        await update.message.reply_text(
            f"Last payment: {last_payment_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Bill since last payment:\n"
            f"Light: {total_light:.2f} ₼, Gas: {total_gas:.2f} ₼, Water: {total_water:.2f} ₼"
        )
    else:
        await update.message.reply_text("No payments have been made yet.")

def run_telegram_bot():
    """ Run Telegram bot in separate thread """
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
# Start Arduino reading thread
threading.Thread(target=read_from_arduino, daemon=True).start()
# Start Telegram bot thread
threading.Thread(target=run_telegram_bot, daemon=True).start()
# Start GUI update loop
update_gui()
root.mainloop()
