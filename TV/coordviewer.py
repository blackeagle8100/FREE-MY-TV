#!/usr/bin/env python3

from pynput import mouse

def on_click(x, y, button, pressed):
    if pressed:
        print(f"Clicked at: ({x}, {y})")

def main():
    with mouse.Listener(on_click=on_click) as listener:
        listener.join()

if __name__ == "__main__":
    main()
