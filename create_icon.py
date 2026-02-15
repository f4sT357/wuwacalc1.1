from PIL import Image, ImageDraw


def create_wave_icon(filename="app_icon.ico"):
    size = (256, 256)
    # Background color (Dark Blue-ish)
    bg_color = (20, 30, 50)
    # Wave colors
    wave_color_1 = (0, 120, 215)  # Medium Blue
    wave_color_2 = (100, 200, 255)  # Light Blue

    img = Image.new("RGBA", size, bg_color)
    draw = ImageDraw.Draw(img)

    # Draw simple waves
    # Wave 1 (Back)
    points1 = [(0, 150), (60, 130), (120, 160), (180, 140), (256, 170), (256, 256), (0, 256)]
    draw.polygon(points1, fill=wave_color_1)

    # Wave 2 (Front)
    points2 = [(0, 190), (50, 210), (110, 180), (170, 220), (230, 190), (256, 210), (256, 256), (0, 256)]
    draw.polygon(points2, fill=wave_color_2)

    # Optional: Add a stylized "W" or similar if needed, but simple is better for icon.

    # Save as ICO
    # Including multiple sizes for better scaling in Windows
    img.save(filename, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icon created: {filename}")


if __name__ == "__main__":
    create_wave_icon()
