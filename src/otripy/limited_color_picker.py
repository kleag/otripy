from PySide6.QtWidgets import QApplication, QColorDialog
from PySide6.QtGui import QColor
import colorsys
import math

class LimitedColorPicker:
    COLORS = {
        "red": (255, 0, 0), "blue": (0, 0, 255), "green": (0, 255, 0), "orange": (255, 165, 0),
        "purple": (128, 0, 128), "darkred": (139, 0, 0), "lightred": (255, 102, 102),
        "darkblue": (0, 0, 139), "lightblue": (173, 216, 230), "darkgreen": (0, 100, 0), "lightgreen": (144, 238, 144),
        "cadetblue": (95, 158, 160), "white": (255, 255, 255), "pink": (255, 192, 203),
        "gray": (128, 128, 128), "black": (0, 0, 0)
    }

    @staticmethod
    def get_color():
        """Opens QColorDialog and returns the closest predefined color name."""
        color = QColorDialog.getColor()
        if color.isValid():
            chosen_color = (color.red(), color.green(), color.blue())
            result = LimitedColorPicker.find_closest_color(chosen_color)
            print(f"Color: {result}")
            return result
        return None  # If the user cancels

    @staticmethod
    def rgb_to_lab(rgb):
        """Converts RGB (0-255) to Lab color space for better visual matching."""
        def pivot_xyz(n):
            return math.pow(n, 1/3) if n > 0.008856 else (7.787 * n) + (16 / 116)

        r, g, b = [x / 255.0 for x in rgb]  # Normalize RGB
        r, g, b = [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in (r, g, b)]

        # Convert to XYZ color space
        X = (r * 0.4124564 + g * 0.3575761 + b * 0.1804375) / 0.95047
        Y = (r * 0.2126729 + g * 0.7151522 + b * 0.0721750)
        Z = (r * 0.0193339 + g * 0.1191920 + b * 0.9503041) / 1.08883

        # Convert to Lab color space
        X, Y, Z = pivot_xyz(X), pivot_xyz(Y), pivot_xyz(Z)
        L = (116 * Y) - 16
        a = 500 * (X - Y)
        b = 200 * (Y - Z)

        return (L, a, b)

    @staticmethod
    def color_difference(lab1, lab2):
        """Computes CIE76 color difference (simplified CIEDE2000) between two Lab colors."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))

    @staticmethod
    def find_closest_color(rgb):
        """Finds the visually closest predefined color using Lab color space."""
        lab1 = LimitedColorPicker.rgb_to_lab(rgb)
        return min(LimitedColorPicker.COLORS, key=lambda name: LimitedColorPicker.color_difference(
            lab1, LimitedColorPicker.rgb_to_lab(LimitedColorPicker.COLORS[name])
        ))

# Example usage
if __name__ == "__main__":
    app = QApplication([])
    selected_color = LimitedColorPicker.get_color()
    if selected_color:
        print(f"Selected color: {selected_color}")
    else:
        print("Color selection canceled.")
