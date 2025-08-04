# Gesture Controller 

## Overview

This project is a real-time gesture recognition system that offers an intuitive, camera-based method for interacting with a computer. It leverages the MediaPipe library to interpret hand landmarks and translate them into a rich set of commands for system control.

The application is built around a state-driven architecture, which isolates gestures for different tasks, creating a seamless and error-free user experience. It effectively turns a standard webcam into a powerful tool for hands-free computer operation.

---

## Core Features

- **Multi-Mode Architecture:** The system operates in four distinct modes (Menu, System Control, Mouse, and Typing) to provide a clear and organized control scheme without conflicting gestures.

- **Full Mouse Emulation:** Delivers comprehensive cursor control, including high-precision movement, standard left/right clicks, double-clicks, and a robust drag-and-drop function activated by a sustained pinch.

- **Dynamic System Control:** Allows for fine-grained, continuous adjustment of system volume and screen brightness using intuitive gestures, designed to prevent abrupt jumps in value.

- **Hands-Free Typing:** Features an on-screen virtual keyboard with a "dwell-to-type" mechanism, enabling text input by simply hovering the cursor over keys.

- **Interactive Overlay UI:** A clean, semi-transparent interface provides all necessary information without obstructing the view. It includes context-aware guides that display the relevant gestures for the currently active mode.

---

## Setup and Installation

### Prerequisites
- Python 3.8+
- A standard webcam
- Windows OS (recommended for full access to audio and brightness controls).

### Installation Steps

1.  **Clone the repository:**
    ```bash
    git clone git remote add origin https://github.com/Nimasol42/Gesture-Controller
    cd Gesture-Controller
    ```

2.  **Set up a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## Usage

Launch the application by running the main script from your terminal:
```bash
python main.py
```
The program will start in the main menu. Use the "pinch" gesture to select an operational mode. For guidance on specific gestures within each mode, refer to the on-screen help panel.

---

## Gesture Reference

### Control Mode
- **Volume:** Use the "horns" gesture (index and pinky fingers up) and move your hand vertically.
- **Brightness:** With five fingers extended, alter the horizontal distance between your thumb and pinky.

### Mouse Mode
- **Cursor Movement:** Guide with your index finger.
- **Left Click:** Pinch thumb and index finger.
- **Double Click:** Perform two quick left-click pinches.
- **Right Click:** Pinch thumb and middle finger.
- **Drag & Drop:** Sustain the left-click pinch gesture until the cursor changes color, then drag and release.

### Typing Mode
- **Key Input:** Hover the cursor over any key for a moment to type it.

---

## Dependencies
- `opencv-python`
- `mediapipe`
- `numpy`
- `screen_brightness_control`
- `pyautogui`
- `pycaw`

---

## License
This project is licensed under the MIT License.
