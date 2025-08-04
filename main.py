import cv2
import mediapipe as mp
import numpy as np
import screen_brightness_control as sbc
import math
import time
import platform
import pyautogui

# For safety, this is disabled by default. Enable if you trust the script.
# pyautogui.FAILSAFE = False

if platform.system() == "Windows":
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
else:
    AudioUtilities, IAudioEndpointVolume, CLSCTX_ALL = None, None, None

class GestureController:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 1280)
        self.cap.set(4, 720)
        self.screen_width, self.screen_height = pyautogui.size()

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, max_num_hands=1)
        self.mp_draw = mp.solutions.drawing_utils

        self.volume = self.init_volume()
        if self.volume:
            self.vol_range = self.volume.GetVolumeRange()
            self.min_vol, self.max_vol = self.vol_range[0], self.vol_range[1]
        
        self.current_mode = "menu"
        self.typed_text = ""
        self.click_cooldown = 0.5
        self.last_action_time = 0
        self.dwell_time = 0.8
        self.dwell_start_time = 0
        self.dwelling_key_pos = None

        self.smooth_x, self.smooth_y = 0, 0
        self.alpha = 0.5

        # Advanced control state variables
        self.vol_gesture_active = False
        self.vol_gesture_start_y = 0
        self.initial_vol = 0
        self.is_dragging = False
        self.drag_start_time = 0
        self.last_left_click_time = 0
        self.DOUBLE_CLICK_INTERVAL = 0.4
        
        # UI state variables
        self.click_flash_info = None
        self.colors = {
            "primary": (20, 20, 20), "highlight": (60, 60, 60), "text": (255, 255, 255),
            "accent": (0, 150, 255), "flash": (255, 255, 255)
        }
        self.font = cv2.FONT_HERSHEY_DUPLEX

        self.define_ui_elements()

    def init_volume(self):
        if platform.system() == "Windows":
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                return interface.QueryInterface(IAudioEndpointVolume)
            except Exception as e:
                print(f"Could not initialize audio control: {e}")
                return None
        return None

    def define_ui_elements(self):
        self.buttons = {
            "menu": [{"rect": (100, 150, 450, 100), "text": "Typing Mode", "action": "typing"},
                     {"rect": (100, 300, 450, 100), "text": "Control Mode", "action": "control"},
                     {"rect": (100, 450, 450, 100), "text": "Mouse Mode", "action": "mouse"}],
            "typing": [{"rect": (1100, 20, 150, 70), "text": "Back", "action": "menu"}],
            "control": [{"rect": (1100, 20, 150, 70), "text": "Back", "action": "menu"}],
            "mouse": [{"rect": (1100, 20, 150, 70), "text": "Back", "action": "menu"}]}
        self.keyboard_keys = [["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "<-"],
                              ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "Clr"],
                              ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Space"]]

    # Core Logic Handlers
    def process_gestures(self, hand_landmarks, img_shape):
        h, w, _ = img_shape
        landmarks = hand_landmarks.landmark
        raw_ix, raw_iy = landmarks[8].x * w, landmarks[8].y * h
        self.smooth_x = self.alpha * raw_ix + (1 - self.alpha) * self.smooth_x
        self.smooth_y = self.alpha * raw_iy + (1 - self.alpha) * self.smooth_y
        cursor_pos = (int(self.smooth_x), int(self.smooth_y))
        tip_ids = [4, 8, 12, 16, 20]
        fingers_up = [1 if landmarks[tip_ids[0]].x < landmarks[tip_ids[0] - 1].x else 0]
        for i in range(1, 5): fingers_up.append(1 if landmarks[tip_ids[i]].y < landmarks[tip_ids[i] - 2].y else 0)
        def get_dist(p1, p2): return math.hypot((landmarks[p1].x-landmarks[p2].x)*w, (landmarks[p1].y-landmarks[p2].y)*h)
        return {"cursor": cursor_pos, "fingers_up": fingers_up, "num_fingers_up": sum(fingers_up),
                "is_left_pinching": get_dist(4, 8) < 40, "is_right_pinching": get_dist(4, 12) < 40,
                "brightness_dist": abs(landmarks[20].x - landmarks[4].x), "wrist_pos": (landmarks[0].x*w, landmarks[0].y*h)}

    def handle_ui_button_clicks(self, gesture_info):
        cursor_x, cursor_y = gesture_info["cursor"]
        if gesture_info["is_left_pinching"] and (time.time() - self.last_action_time) > self.click_cooldown:
            for btn in self.buttons.get(self.current_mode, []):
                x, y, w, h = btn["rect"]
                if x < cursor_x < x + w and y < cursor_y < y + h:
                    self.current_mode = btn["action"]
                    self.last_action_time = time.time()
                    self.click_flash_info = {"rect": btn["rect"], "time": time.time()}
                    self.is_dragging = False; pyautogui.mouseUp()
                    return True
        return False

    def handle_control_mode(self, gesture_info):
        fingers, num_fingers = gesture_info["fingers_up"], gesture_info["num_fingers_up"]
        is_vol_gesture = num_fingers == 2 and fingers[1] and fingers[4]
        if is_vol_gesture:
            if not self.vol_gesture_active:
                self.vol_gesture_active, self.vol_gesture_start_y = True, gesture_info["wrist_pos"][1]
                if self.volume: self.initial_vol = self.volume.GetMasterVolumeLevel()
            else:
                delta_y = self.vol_gesture_start_y - gesture_info["wrist_pos"][1]
                vol_change = np.interp(delta_y, [-200, 200], [self.min_vol - self.initial_vol, self.max_vol - self.initial_vol])
                new_vol = np.clip(self.initial_vol + vol_change, self.min_vol, self.max_vol)
                if self.volume: self.volume.SetMasterVolumeLevel(new_vol, None)
        else:
            self.vol_gesture_active = False
        if num_fingers == 5:
            brightness_level = int(np.interp(gesture_info["brightness_dist"], [0.15, 0.5], [0, 100]))
            sbc.set_brightness(np.clip(brightness_level, 0, 100))

    def handle_mouse_mode(self, gesture_info):
        h, w, _ = self.img.shape
        cursor_x, cursor_y = gesture_info["cursor"]
        safe_x, safe_y = np.clip(cursor_x, 200, w - 200), np.clip(cursor_y, 150, h - 250)
        mapped_x, mapped_y = np.interp(safe_x, [200, w - 200], [0, self.screen_width]), np.interp(safe_y, [150, h - 250], [0, self.screen_height])
        pyautogui.moveTo(mapped_x, mapped_y)
        can_act = (time.time() - self.last_action_time) > 0.2
        if gesture_info["is_left_pinching"]:
            if not self.is_dragging and self.drag_start_time == 0: self.drag_start_time = time.time()
            if time.time() - self.drag_start_time > 0.3 and not self.is_dragging: self.is_dragging = True; pyautogui.mouseDown()
        else:
            if self.is_dragging: pyautogui.mouseUp(); self.is_dragging = False
            self.drag_start_time = 0
        if not self.is_dragging and can_act:
            if gesture_info["is_left_pinching"] and self.drag_start_time == 0:
                if time.time() - self.last_left_click_time < self.DOUBLE_CLICK_INTERVAL: pyautogui.doubleClick(); self.last_left_click_time = 0
                else: pyautogui.click()
                self.last_action_time = self.last_left_click_time = time.time()
            elif gesture_info["is_right_pinching"]: pyautogui.rightClick(); self.last_action_time = time.time()
    
    #UI Drawing Functions
    def draw_rounded_rect(self, img, rect, radius, color):
        x, y, w, h = rect; r = radius
        cv2.ellipse(img, (x + r, y + r), (r, r), 180, 0, 90, color, -1)
        cv2.ellipse(img, (x + w - r, y + r), (r, r), 270, 0, 90, color, -1)
        cv2.ellipse(img, (x + w - r, y + h - r), (r, r), 0, 0, 90, color, -1)
        cv2.ellipse(img, (x + r, y + h - r), (r, r), 90, 0, 90, color, -1)
        cv2.rectangle(img, (x + r, y), (x + w - r, y + h), color, -1)
        cv2.rectangle(img, (x, y + r), (x + w, y + h - r), color, -1)

    def draw_ui_elements(self, overlay, gesture_info):
        cursor_x, cursor_y = gesture_info["cursor"] if gesture_info else (-1, -1)
        for btn in self.buttons.get(self.current_mode, []):
            color = self.colors["highlight"] if (btn["rect"][0] < cursor_x < btn["rect"][0] + btn["rect"][2] and btn["rect"][1] < cursor_y < btn["rect"][1] + btn["rect"][3]) else self.colors["primary"]
            self.draw_rounded_rect(overlay, btn["rect"], 20, color)
            text_size = cv2.getTextSize(btn["text"], self.font, 1.5, 2)[0]
            text_x, text_y = btn["rect"][0] + (btn["rect"][2] - text_size[0]) // 2, btn["rect"][1] + (btn["rect"][3] + text_size[1]) // 2
            cv2.putText(overlay, btn["text"], (text_x, text_y), self.font, 1.5, self.colors["text"], 2)
        if self.current_mode == "typing": self.draw_keyboard(overlay, gesture_info)
        if self.click_flash_info and time.time() - self.click_flash_info["time"] < 0.2:
            self.draw_rounded_rect(overlay, self.click_flash_info["rect"], 20, self.colors["flash"])
        else:
            self.click_flash_info = None

    def draw_keyboard(self, overlay, gesture_info):
        h, w, _ = self.img.shape
        cursor_x, cursor_y = gesture_info["cursor"] if gesture_info else (-1, -1)
        keyboard_y_start, key_found = h - 280, False
        self.draw_rounded_rect(overlay, (20, 80, w - 40, 100), 20, self.colors["primary"])
        cv2.putText(overlay, self.typed_text, (40, 145), self.font, 2, self.colors["text"], 3)
        for i, row in enumerate(self.keyboard_keys):
            for j, key in enumerate(row):
                key_w = 120 if key == "Space" else 70
                rect = (j * 80 + 20, i * 80 + keyboard_y_start, key_w, 70)
                x, y, w_key, h_key = rect
                is_hover = (x < cursor_x < x + w_key and y < cursor_y < y + h_key)
                color = self.colors["highlight"] if is_hover else self.colors["primary"]
                self.draw_rounded_rect(overlay, rect, 15, color)
                if is_hover:
                    key_found = True
                    if self.dwelling_key_pos != (i, j): self.dwelling_key_pos, self.dwell_start_time = (i, j), time.time()
                    if time.time() - self.dwell_start_time > self.dwell_time:
                        if key == "<-": self.typed_text = self.typed_text[:-1]
                        elif key == "Clr": self.typed_text = ""
                        elif key == "Space": self.typed_text += " "
                        else: self.typed_text += key
                        self.dwell_start_time = time.time()
                    progress = (time.time() - self.dwell_start_time) / self.dwell_time
                    cv2.rectangle(overlay, (x, y+h_key-5), (int(x + w_key * progress), y+h_key), self.colors["accent"], -1)
                font_scale = 1.5 if len(key)==1 else 1.0
                text_size = cv2.getTextSize(key, self.font, font_scale, 2)[0]
                text_x, text_y = x + (w_key - text_size[0]) // 2, y + (h_key + text_size[1]) // 2
                cv2.putText(overlay, key, (text_x, text_y), self.font, font_scale, self.colors["text"], 2)
        if not key_found: self.dwelling_key_pos = None

    def draw_feedback_panel(self, overlay, gesture_info):
        self.draw_rounded_rect(overlay, (10, 10, 350, 120), 20, self.colors["primary"])
        cv2.putText(overlay, f"Mode: {self.current_mode.upper()}", (25, 45), self.font, 1, self.colors["text"], 2)
        if self.current_mode == "control":
            try:
                brightness = int(sbc.get_brightness()[0])
                cv2.putText(overlay, f"Brightness: {brightness}%", (25, 80), self.font, 1, self.colors["text"], 2)
            except: pass
            if self.volume:
                vol_percent = int(np.interp(self.volume.GetMasterVolumeLevel(), [self.min_vol, self.max_vol], [0, 100]))
                cv2.putText(overlay, f"Volume: {vol_percent}%", (25, 115), self.font, 1, self.colors["text"], 2)
        cursor_color = self.colors["accent"]
        if self.current_mode == "mouse":
            if self.is_dragging: cursor_color = (0, 255, 0)
            elif gesture_info["is_left_pinching"] or gesture_info["is_right_pinching"]: cursor_color = (0, 0, 255)
        cv2.circle(self.img, gesture_info["cursor"], 12, cursor_color, cv2.FILLED)
        cv2.circle(self.img, gesture_info["cursor"], 12, (255,255,255), 2)

    def draw_gesture_guides(self, overlay):
        h, w, _ = self.img.shape
        guides = {
            "control": ["Rahnamaye Zhest (Control):",
                        "- Seda: Zhest Shakh + Harekat Bala/Payin",
                        "- Rushanayi: 5 Angosht + Baz/Baste Kardan"],
            "typing": ["Rahnamaye Zhest (Typing):",
                       "- Entekhab: Negah Dashtan Neshangar",
                       "- Jabejayi: Ba Angosht Eshareh"],
            "mouse": ["Rahnamaye Zhest (Mouse):",
                      "- Klik Chap: Shast + Eshareh",
                      "- Klik Rast: Shast + Miyani",
                      "- Keshidan: Negah Dashtan Klik Chap"]
        }
        guide_text = guides.get(self.current_mode)
        if guide_text:
            if self.current_mode == 'typing':
                x, y_start, max_w = w - 410, 200, 400
            else:
                x, y_start, max_w = w - 410, h - 150, 400
            
            panel_h = len(guide_text) * 35 + 15
            self.draw_rounded_rect(overlay, (x - 10, y_start - 25, max_w, panel_h), 15, self.colors["primary"])
            for i, line in enumerate(guide_text):
                cv2.putText(overlay, line, (x, y_start + i * 35), self.font, 0.7, self.colors["text"], 2)

    def run(self):
        while True:
            success, self.img = self.cap.read()
            if not success: continue
            self.img = cv2.flip(self.img, 1)

            img_rgb = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)
            
            overlay = self.img.copy()
            gesture_info = None

            if results.multi_hand_landmarks:
                hand_landmarks = results.multi_hand_landmarks[0]
                gesture_info = self.process_gestures(hand_landmarks, self.img.shape)
                
                ui_clicked = self.handle_ui_button_clicks(gesture_info)

                if not ui_clicked:
                    if self.current_mode == "control": self.handle_control_mode(gesture_info)
                    elif self.current_mode == "mouse": self.handle_mouse_mode(gesture_info)
                
                self.mp_draw.draw_landmarks(self.img, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
            
            self.draw_ui_elements(overlay, gesture_info)
            self.draw_gesture_guides(overlay)
            
            alpha = 0.65
            cv2.addWeighted(overlay, alpha, self.img, 1 - alpha, 0, self.img)

            if gesture_info: 
                self.draw_feedback_panel(self.img, gesture_info)
            
            cv2.imshow("Gesture Controller Pro v12 (Final)", self.img)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    controller = GestureController()
    controller.run()