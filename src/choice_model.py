# choice_model.py

from src.ui_emotion_mapper import map_emotion_to_ui_color

AXIS_RGB = {
    "red":   (1, 0, 0),
    "green": (0, 1, 0),
    "blue":  (0, 0, 1),
}

MIN_BRIGHTNESS = 0  # 暗さを底上げするための下限値（0〜255）

def lift_brightness(value: int) -> int:
    return max(value, MIN_BRIGHTNESS)

class Choice:
    def __init__(self, label, action_key, emotion_axis, emotion_value=255, requirement_keys=None):
        self.label = label
        self.action_key = action_key
        self.emotion_axis = emotion_axis  # "red", "green", "blue"
        self.emotion_value = emotion_value  # 0–255（強さ）
        self.requirement_keys = requirement_keys or []

    def get_emotion_color(self):
        """emotion_axis と emotion_value を使って RGB 色を返す（明度底上げ）"""
        scale = self.emotion_value / 255
        base = AXIS_RGB[self.emotion_axis]
        return tuple(lift_brightness(int(c * scale * 255)) for c in base)

    def get_player_scaled_color(self, player_emotion_color):
        """プレイヤーの emotion_color に合わせて、この選択肢の軸方向成分だけ抽出（明度底上げ）"""
        r, g, b = player_emotion_color
        if self.emotion_axis == "red":
            return (lift_brightness(r), 0, 0)
        elif self.emotion_axis == "green":
            return (0, lift_brightness(g), 0)
        elif self.emotion_axis == "blue":
            return (0, 0, lift_brightness(b))

    def get_emotion_x_player_scaled_color(self, player_emotion_color):
        """
        emotion_valueの強さとプレイヤーの感情の色を掛け合わせ、明度も底上げ。
        出力は RGB 値。
        """
        r, g, b = player_emotion_color
        scale = self.emotion_value / 255
        if self.emotion_axis == "red":
            return (lift_brightness(int(r * scale)), 0, 0)
        elif self.emotion_axis == "green":
            return (0, lift_brightness(int(g * scale)), 0)
        elif self.emotion_axis == "blue":
            return (0, 0, lift_brightness(int(b * scale)))

    def get_ui_color(self):
        """emotion軸からUI表示用のカラーを取得（②で利用）"""
        return map_emotion_to_ui_color(self.rgb_value)

    def is_available(self, checker):
        """requirements_checker.py で条件を満たしているかを判定"""
        return checker.check_all(self.requirement_keys)
