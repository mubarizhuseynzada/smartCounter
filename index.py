import serial
import time
import tkinter as tk
from tkinter import ttk

# ----------- Arduino serial ----------
arduino = serial.Serial('COM4', 9600, timeout=1)   # ← измени COM-порт!
time.sleep(2)

# ----------- Prices ---------------
COST_LIGHT = 6
COST_GAS = 8
COST_WATER = 3

# ----------- Thresholds (порог) -----------
LIGHT_THRESHOLD = 300
GAS_THRESHOLD = 350
WATER_THRESHOLD = 400

# ----------- Totals ---------------
total_light = 0
total_gas = 0
total_water = 0

# ================ GUI ================
root = tk.Tk()
root.title("Smart Counter Monitor")
root.geometry("480x300")
root.resizable(False, False)

style = ttk.Style()
style.configure("TLabel", font=("Segoe UI", 12))

# Заголовок
title = ttk.Label(root, text="SMART COUNTER STATUS", font=("Segoe UI", 16, "bold"))
title.pack(pady=10)

# Рамка значений
frame = ttk.Frame(root)
frame.pack(pady=10)

# ----- SENSOR VALUES -----
lbl_light = ttk.Label(frame, text="Light: 0")
lbl_light.grid(row=0, column=0, padx=20, pady=5)

lbl_gas = ttk.Label(frame, text="Gas: 0")
lbl_gas.grid(row=1, column=0, padx=20, pady=5)

lbl_water = ttk.Label(frame, text="Water: 0")
lbl_water.grid(row=2, column=0, padx=20, pady=5)

# ----- COST VALUES -----
lbl_cost_light = ttk.Label(frame, text="Light cost: 0.00 ₼")
lbl_cost_light.grid(row=0, column=1, padx=20, pady=5)

lbl_cost_gas = ttk.Label(frame, text="Gas cost: 0.00 ₼")
lbl_cost_gas.grid(row=1, column=1, padx=20, pady=5)

lbl_cost_water = ttk.Label(frame, text="Water cost: 0.00 ₼")
lbl_cost_water.grid(row=2, column=1, padx=20, pady=5)

# ----- TOTAL -----
lbl_total = ttk.Label(root, text="TOTAL: 0.00 ₼", font=("Segoe UI", 15, "bold"))
lbl_total.pack(pady=15)


# ================== LOGIC ==================
def analog_to_value(analog):
    return analog / 1023


def update_data():
    global total_light, total_gas, total_water

    try:
        line = arduino.readline().decode().strip()

        if line == "":
            root.after(200, update_data)
            return

        if line == "PAYMENT":
            total_light = total_gas = total_water = 0
            lbl_total.configure(text="TOTAL: 0.00 ₼")
            root.after(200, update_data)
            return

        # Разбираем данные
        parts = line.split(',')
        sensor = {}
        for p in parts:
            key, val = p.split(':')
            sensor[key] = int(val)

        light = sensor['light']
        gas = sensor['gas']
        water = sensor['water']

        # ---- Update sensor labels ----
        lbl_light.configure(text=f"Light: {light}")
        lbl_gas.configure(text=f"Gas: {gas}")
        lbl_water.configure(text=f"Water: {water}")

        # ----- COST CALCULATION -----
        if light > LIGHT_THRESHOLD:
            total_light += analog_to_value(light) * COST_LIGHT

        if gas > GAS_THRESHOLD:
            total_gas += analog_to_value(gas) * COST_GAS

        if water > WATER_THRESHOLD:
            total_water += analog_to_value(water) * COST_WATER

        # Update cost labels
        lbl_cost_light.configure(text=f"Light cost: {total_light:.2f} ₼")
        lbl_cost_gas.configure(text=f"Gas cost: {total_gas:.2f} ₼")
        lbl_cost_water.configure(text=f"Water cost: {total_water:.2f} ₼")

        # Total
        total = total_light + total_gas + total_water
        lbl_total.configure(text=f"TOTAL: {total:.2f} ₼")

    except Exception as e:
        print("Error:", e)

    root.after(200, update_data)   # обновлять каждые 200 мс

# Старт обновления
update_data()

# Запуск GUI
root.mainloop()
