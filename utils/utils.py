import sys
import os
import logging
from typing import Callable
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None
# OpenCV related logic removed


def get_app_path() -> str:
    """
    Get the directory path where the executable is located.
    Used for user-writable files like config.json and logs.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # utils.py is in the 'utils' subdirectory, so we need to go up one level to reach the root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(relative_path: str = "") -> str:
    """
    Get the absolute path to a resource.
    Works for dev and for PyInstaller (MEIPASS).
    Used for read-only bundled assets like game data.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # utils.py is in the 'utils' subdirectory, so we need to go up one level to reach the root
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


def crop_image_by_percent(
    img: "Image.Image", left_p: float, top_p: float, width_p: float, height_p: float
) -> "Image.Image":
    """Crops an area from the image based on left, top, width, and height percentages.

    Args:
        img: Pillow Image object.
        left_p: The percentage from the left to start the crop (0-100).
        top_p: The percentage from the top to start the crop (0-100).
        width_p: The width of the crop as a percentage of total image width (0-100).
        height_p: The height of the crop as a percentage of total image height (0-100).

    Returns:
        The cropped Image object.

    Raises:
        ValueError: If the percentage settings result in an invalid crop box.
    """
    w, h = img.size

    left = int(w * (left_p / 100))
    top = int(h * (top_p / 100))
    right = left + int(w * (width_p / 100))
    bottom = top + int(h * (height_p / 100))

    # Clip the coordinates to be within the image boundaries
    left = max(0, left)
    top = max(0, top)
    right = min(w, right)
    bottom = min(h, bottom)

    if left >= right or top >= bottom:
        raise ValueError("Invalid percentage settings resulted in a zero or negative size crop box.")

    return img.crop((left, top, right, bottom))


def get_substat_display(stat_name, value):
    """
    Display string for substats.
    If '%' is in stat_name, display with '%', otherwise as is.
    """
    if "%" in stat_name:
        return f"{stat_name} : {value} %"
    else:
        return f"{stat_name} : {value}"


def setup_tesseract():
    """Set up and confirm the path for Tesseract OCR."""
    logger = logging.getLogger(__name__)
    if pytesseract is None:
        logger.warning("pytesseract is not installed. OCR functions will be unavailable.")
        return

    if sys.platform != "win32":
        logger.info("Tesseract setup is configured for Windows. On other OS, it's assumed to be in PATH.")
        return

    # Prioritize checking the path for Tesseract bundled with PyInstaller
    bundled_tesseract = None
    bundled_tessdata = None

    if getattr(sys, "frozen", False):
        # If running with PyInstaller
        base_path = sys._MEIPASS
        bundled_tesseract = os.path.join(base_path, "tesseract", "tesseract.exe")
        bundled_tessdata = os.path.join(base_path, "tesseract", "tessdata")
        logger.info(f"PyInstaller environment detected: base_path={base_path}")
        logger.info(f"Bundled Tesseract path: {bundled_tesseract}")
        logger.info(f"Bundled tessdata path: {bundled_tessdata}")

    # Search for Tesseract with priority
    possible_paths = [
        bundled_tesseract,  # Bundled Tesseract (highest priority)
        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
    ]

    # Exclude None
    possible_paths = [p for p in possible_paths if p]

    tesseract_found = False
    for path in possible_paths:
        logger.info(f"Checking for Tesseract at: {path}")
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"[OK] Tesseract path set to: {path}")

            # Set TESSDATA_PREFIX environment variable
            if bundled_tesseract and path == bundled_tesseract:
                if bundled_tessdata and os.path.exists(bundled_tessdata):
                    os.environ["TESSDATA_PREFIX"] = bundled_tessdata + os.sep
                    logger.info(f"[OK] TESSDATA_PREFIX set to: {os.environ['TESSDATA_PREFIX']}")
                    # Log contents of tessdata for debugging
                    try:
                        tessdata_files = os.listdir(bundled_tessdata)
                        logger.info(f"[OK] Found {len(tessdata_files)} files in tessdata.")
                        important_files = ["eng.traineddata", "jpn.traineddata", "jpn_vert.traineddata"]
                        for f in important_files:
                            if f in tessdata_files:
                                logger.info(f"  [OK] Found {f}")
                    except Exception as e:
                        logger.warning(f"Could not list tessdata contents: {e}")
                else:
                    logger.warning(f"Bundled tessdata not found at: {bundled_tessdata}")
            else:
                # For system-installed Tesseract
                tessdata_dir = os.path.join(os.path.dirname(path), "tessdata")
                if os.path.exists(tessdata_dir):
                    os.environ["TESSDATA_PREFIX"] = tessdata_dir + os.sep
                    logger.info(f"[OK] TESSDATA_PREFIX set for system Tesseract: {os.environ['TESSDATA_PREFIX']}")

            tesseract_found = True
            break

    if not tesseract_found:
        logger.warning("[ERROR] Tesseract executable not found.")
        logger.warning("  Searched paths:")
        for p in possible_paths:
            logger.warning(f"    - {p}")

    # Check Tesseract version
    try:
        version = pytesseract.get_tesseract_version()
        logger.info(f"[OK] Tesseract version: {version}")
    except Exception as e:
        logger.warning(f"[ERROR] Could not get Tesseract version: {e}")
        logger.warning(f"   pytesseract.tesseract_cmd = {pytesseract.pytesseract.tesseract_cmd}")
        if "TESSDATA_PREFIX" in os.environ:
            logger.warning(f"   TESSDATA_PREFIX = {os.environ['TESSDATA_PREFIX']}")


def is_pillow_installed() -> bool:
    """Checks if Pillow (PIL) is installed."""
    try:
        from PIL import Image

        return True
    except ImportError:
        return False


def is_pytesseract_installed() -> bool:
    """Checks if pytesseract is installed."""
    try:
        import pytesseract

        return True
    except ImportError:
        return False


def is_tesseract_configured() -> bool:
    """Checks if Tesseract is correctly configured by trying to get its version."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def check_and_alert_environment(gui_log: "Callable[[str], None]") -> None:
    """Environment check."""
    logger = logging.getLogger(__name__)
    try:
        pil_installed = is_pillow_installed()
        pytesseract_installed = is_pytesseract_installed()
        tesseract_configured = is_tesseract_configured()

        missing_libs = []
        if not pil_installed:
            missing_libs.append("Pillow")
        if not pytesseract_installed:
            missing_libs.append("pytesseract")

        if missing_libs:
            gui_log(f"Warning: The following libraries are missing: {', '.join(missing_libs)}")
            gui_log("To use the OCR feature, please install these libraries.")
        elif not tesseract_configured:
            gui_log("Warning: Tesseract is not configured correctly.")
            gui_log("To use OCR, please install Tesseract and set the path.")
        else:
            gui_log("Environment check: OCR feature is available.")



    except Exception as e:
        logger.warning(f"Environment check error: {e}", exc_info=True)
