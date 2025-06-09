import paho.mqtt.client as mqtt
import time
import random
import json
import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "smart_city/waste"
DB_FILE = "waste_data.db"

class WasteBinSensor:
    def __init__(self, bin_id, location):
        self.bin_id = bin_id
        self.location = location
        self.fill_level = random.uniform(0, 20)
        self.temperature = random.uniform(18, 25)
        self.humidity = random.uniform(30, 60)
        self.relay_status = "OFF"

    def read_sensors(self):
        self.fill_level = min(100, self.fill_level + random.uniform(0.5, 3.0))
        self.temperature = max(15, min(40, self.temperature + random.uniform(-1, 1)))
        self.humidity = max(20, min(80, self.humidity + random.uniform(-2, 2)))
        self.relay_status = "ON" if self.fill_level > 90 else "OFF"

        return {
            "bin_id": self.bin_id,
            "location": self.location,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fill_level": round(self.fill_level, 1),
            "temperature": round(self.temperature, 1),
            "humidity": round(self.humidity, 1),
            "relay_status": self.relay_status,
            "status": self.get_bin_status()
        }

    def get_bin_status(self):
        if self.temperature > 35:
            return "ALERT: High Temperature"
        elif self.fill_level > 90:
            return "URGENT: Nearly Full"
        elif self.fill_level > 75:
            return "WARNING: Getting Full"
        return "Normal"

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS waste_data (
                    bin_id TEXT,
                    location TEXT,
                    timestamp TEXT,
                    fill_level REAL,
                    temperature REAL,
                    humidity REAL,
                    relay_status TEXT,
                    status TEXT)''')
    conn.commit()
    conn.close()

def save_to_database(sensor_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO waste_data VALUES (?,?,?,?,?,?,?,?)", (
        sensor_data["bin_id"],
        sensor_data["location"],
        sensor_data["timestamp"],
        sensor_data["fill_level"],
        sensor_data["temperature"],
        sensor_data["humidity"],
        sensor_data["relay_status"],
        sensor_data["status"]
    ))
    conn.commit()
    conn.close()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker successfully")
    else:
        print(f"Connection failed with code {rc}")

def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT Broker. Reconnecting...")
    client.reconnect()

def simulate_smart_bin_network():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"Could not connect to MQTT broker: {e}")
        return

    bins = [
        WasteBinSensor("EBIN001", "City Center"),
        WasteBinSensor("EBIN002", "Main Street"),
        WasteBinSensor("EBIN003", "Park Area")
    ]

    print("Smart Waste Monitoring System Started")

    try:
        while True:
            for waste_bin in bins:
                sensor_data = waste_bin.read_sensors()
                topic = f"{MQTT_TOPIC_PREFIX}/{waste_bin.bin_id}"
                client.publish(topic, json.dumps(sensor_data))
                save_to_database(sensor_data)

                print(f"\nBin ID: {sensor_data['bin_id']} - Location: {sensor_data['location']}")
                print(f"Fill Level: {sensor_data['fill_level']}%")
                print(f"Temperature: {sensor_data['temperature']}°C")
                print(f"Humidity: {sensor_data['humidity']}%")
                print(f"Relay Status: {sensor_data['relay_status']}")
                print(f"Status: {sensor_data['status']}")

            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopping monitoring system...")
        client.loop_stop()
        client.disconnect()

def start_gui():
    root = tk.Tk()
    root.title("Smart Waste Monitoring System")
    root.geometry("600x400")

    tree = ttk.Treeview(root, columns=("bin_id", "location", "fill_level", "temperature", "humidity", "relay_status", "status"), show='headings')
    for col in tree["columns"]:
        tree.heading(col, text=col.replace("_", " ").title())
    tree.pack(fill=tk.BOTH, expand=True)

    def update_gui():
        tree.delete(*tree.get_children())
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM waste_data ORDER BY timestamp DESC LIMIT 10")
        rows = c.fetchall()
        for row in rows:
            tree.insert("", tk.END, values=row)
        conn.close()
        root.after(5000, update_gui)

    update_gui()
    root.mainloop()

import threading

if __name__ == "__main__":
    setup_database()

    simulation_thread = threading.Thread(target=simulate_smart_bin_network, daemon=True)
    simulation_thread.start()

    start_gui()

