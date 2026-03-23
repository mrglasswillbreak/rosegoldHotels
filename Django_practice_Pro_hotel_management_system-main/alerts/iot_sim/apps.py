import random
import time
import requests
from twilio.rest import Client
import os


API_URL = "http://127.0.0.1:8000/api/iot-data/"

ROOMS = ["101", "102", "103", "104"]

TIME_WINDOW = 60
MOTION_THRESHOLD = 8
INACTIVITY_LIMIT = 120

room_state = {}

# Initialize rooms
for room in ROOMS:
    room_state[room] = {
        "motion_log": [],
        "last_motion": time.time(),
        "occupied": random.choice([True, False])
    }

def generate_sensor_data():
    temp = round(random.uniform(22, 40), 2)
    gas = random.choice([0, 0, 0, 1])  # rare gas event
    motion = random.choice([0, 1])
    return temp, gas, motion

def analyze(room, temp, gas, motion):
    state = room_state[room]
    current_time = time.time()

    # Log motion
    if motion == 1:
        state["motion_log"].append(current_time)
        state["last_motion"] = current_time

    # Keep only recent motion events
    state["motion_log"] = [
        t for t in state["motion_log"]
        if current_time - t <= TIME_WINDOW
    ]

    motion_count = len(state["motion_log"])
    inactive_time = current_time - state["last_motion"]

    # Smart logic
    if gas == 1:
        return "CRITICAL: Gas detected"

    if not state["occupied"] and motion == 1:
        return "CRITICAL: Motion in empty room"

    if motion_count > MOTION_THRESHOLD:
        return "WARNING: Excessive motion"

    if state["occupied"] and inactive_time > INACTIVITY_LIMIT:
        return "ALERT: No movement"

    if temp > 35 and motion == 1:
        return "WARNING: High temp + activity"

    return "NORMAL"

def simulate():
    while True:
        for room in ROOMS:
            temp, gas, motion = generate_sensor_data()
            status = analyze(room, temp, gas, motion)

            data = {
                "room": room,
                "temperature": temp,
                "gas": gas,
                "motion": motion,
                "status": status
            }

            print(data)

            try:
                requests.post(API_URL, json=data)
            except:
                print("Server not reachable")

        time.sleep(3)

simulate()

