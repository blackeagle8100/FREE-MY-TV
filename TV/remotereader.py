#!/usr/bin/env python3

import sys
import subprocess
from evdev import InputDevice, categorize, ecodes
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QFont, QColor, QPalette

# Path to the input device (replace with the correct device path)
device_path = "/dev/input/event5"  # Update with the correct event number for your device

# Open the device
dev = InputDevice(device_path)

print(f"Listening to {dev.name} ({device_path})")

def decrease_volume():
    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"], check=True)
    print("Volume decreased by 5%")

def increase_volume():
    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"], check=True)
    print("Volume increased by 5%")

def toggle_mute():
    subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"], check=True)
    print("Toggled mute/unmute")


def open_firefox():
    subprocess.Popen(["firefox"])  # No need for `check=True` since it's not blocking
    print("Opened Firefox")

import subprocess

def show_desktop():
    # Kill specific applications
    apps = ["firefox", "google-chrome-stable", "popcorntime"]
    for app in apps:
        subprocess.run(["pkill", app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Show desktop using wmctrl
    try:
        subprocess.run(["wmctrl", "-k", "on"], check=True)
        print("Showing desktop")
    except subprocess.CalledProcessError:
        print("Failed to execute wmctrl command")


def toggle_mic_mute():
    subprocess.run(["amixer", "set", "Capture", "toggle"], check=True)
    print("Toggled microphone mute/unmute")











# Main loop for key events
try:
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keystate == key_event.key_down:
                keycode = key_event.event.code
                if keycode == 113:
                    print("Toggling mute/unmute volume...")
                    toggle_mute()
                elif keycode == 150:
                    print("Opening Firefox...")
                    open_firefox()
                elif keycode == 158:
                    print("No action for keycode 158")
                elif keycode == 115:
                    print("Increasing volume by 5%...")
                    increase_volume()
                elif keycode == 114:
                    print("Decreasing volume by 5%...")
                    decrease_volume()
                elif keycode == 172:
                    print("Showing desktop...")
                    show_desktop()
                elif keycode == 582:
                    print("Toggling microphone mute/unmute...")
                    toggle_mic_mute()
                else:
                    print(f"Unknown button pressed with keycode: {keycode}")
except KeyboardInterrupt:
    print("Exiting...")


