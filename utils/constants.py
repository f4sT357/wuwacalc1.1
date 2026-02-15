# --- Stat Name Constants (Japanese) ---
STAT_CRIT_RATE = "クリティカル率"
STAT_CRIT_DMG = "クリティカルダメージ"
STAT_ATK_PERCENT = "攻撃力%"
STAT_ATK_FLAT = "攻撃力"
STAT_HP_PERCENT = "HP%"
STAT_HP_FLAT = "HP"
STAT_DEF_PERCENT = "防御力%"
STAT_DEF_FLAT = "防御力"
STAT_ER = "共鳴効率"
STAT_BASIC_DMG_BONUS = "通常攻撃ダメージアップ"
STAT_HEAVY_DMG_BONUS = "重撃ダメージアップ"
STAT_SKILL_DMG_BONUS = "共鳴スキルダメージアップ"
STAT_LIBERATION_DMG_BONUS = "共鳴解放ダメージアップ"
STAT_FUSION_DMG_BONUS = "焦熱ダメージアップ"
STAT_GLACIO_DMG_BONUS = "凝縮ダメージアップ"
STAT_ELECTRO_DMG_BONUS = "電導ダメージアップ"
STAT_AERO_DMG_BONUS = "気動ダメージアップ"
STAT_SPECTRO_DMG_BONUS = "回折ダメージアップ"
STAT_HAVOC_DMG_BONUS = "消滅ダメージアップ"
STAT_HEALING_BONUS = "HP回復効果アップ"

DAMAGE_BONUS_STATS = [
    STAT_BASIC_DMG_BONUS,
    STAT_HEAVY_DMG_BONUS,
    STAT_SKILL_DMG_BONUS,
    STAT_LIBERATION_DMG_BONUS,
    STAT_FUSION_DMG_BONUS,
    STAT_GLACIO_DMG_BONUS,
    STAT_ELECTRO_DMG_BONUS,
    STAT_AERO_DMG_BONUS,
    STAT_SPECTRO_DMG_BONUS,
    STAT_HAVOC_DMG_BONUS,
]

# --- CV Weight Keys ---
CV_KEY_CRIT_RATE = "crit_rate"
CV_KEY_CRIT_DMG = "crit_dmg"
CV_KEY_ATK_PERCENT = "atk_percent"
CV_KEY_ATK_FLAT_DIVISOR = "atk_flat_divisor"
CV_KEY_ATK_FLAT_MULTIPLIER = "atk_flat_multiplier"
CV_KEY_ER = "er"
CV_KEY_DMG_BONUS = "dmg_bonus"

# (Redundant game data removed - now loaded from game_data.json)

THEME_COLORS = {
    "dark": {
        "background": "#2e2e2e",
        "input_bg": "#202020",
        "text": "#ffffff",
        "shadow": "#000000",
        "border": "#5a5a5a",
        "button_bg": "#5a5a5a",
        "button_text": "#ffffff",
        "button_hover": "#6a6a6a",
        "tab_bg": "#3e3e3e",
        "tab_text": "#ffffff",
        "tab_selected": "#4a90e2",
        "group_border": "#5a5a5a",
    },
    "light": {
        "background": "#f0f0f0",
        "input_bg": "#ffffff",
        "text": "#000000",
        "shadow": "#ffffff",
        "border": "#c0c0c0",
        "button_bg": "#e0e0e0",
        "button_text": "#000000",
        "button_hover": "#d0d0d0",
        "tab_bg": "#e0e0e0",
        "tab_text": "#000000",
        "tab_selected": "#a0c0e0",
        "group_border": "#c0c0c0",
    },
}

# --- File and Directory Constants ---
LOG_FILENAME = "wuwacalc.log"
CONFIG_FILENAME = "config.json"
HISTORY_FILENAME = "history.json"
EQUIPPED_ECHOES_FILENAME = "equipped_echoes.json"
CROP_PRESETS_FILENAME = "crop_presets.json"

DIR_CHARACTER_SETTINGS = "character_settings_jsons"
DIR_DATA = "data"
DIR_IMAGES = "images"
DIR_LICENSES = "licenses"
DIR_LOGS = "logs"
DIR_TESSERACT = "tesseract"

# --- Resource Path Keys (for get_resource_path) ---
RES_GAME_DATA = "game_data.json"
RES_CALC_CONFIG = "calculation_config.json"

# Default cost configuration
DEFAULT_COST_CONFIG = "43311"

# OCR engine constants
OCR_ENGINE_PILLOW = "pillow"

# JSON key constants for data structures
KEY_SUBSTATS = "substats"
KEY_STAT = "stat"
KEY_VALUE = "value"
KEY_CHARACTER = "character"
KEY_CHARACTER_JP = "character_jp"
KEY_CONFIG = "config"
KEY_AUTO_APPLY = "auto_apply"
KEY_SCORE_MODE = "score_mode"
KEY_ECHOES = "echoes"
KEY_MAIN_STAT = "main_stat"
KEY_CHARACTER_WEIGHTS = "character_weights"
KEY_CHARACTER_MAINSTATS = "character_mainstats"
# --- History Constants ---
ACTION_SINGLE = "Single Evaluation"
ACTION_BATCH = "Batch Evaluation"
ACTION_OCR = "OCR"

# --- UI Constants ---
# Default window dimensions
DEFAULT_WINDOW_WIDTH = 1000
DEFAULT_WINDOW_HEIGHT = 950

# Dialog dimensions
DIALOG_CHAR_SETTING_WIDTH = 600
DIALOG_CHAR_SETTING_HEIGHT = 600
DIALOG_CROP_WIDTH = 900
DIALOG_CROP_HEIGHT = 700

# Image preview dimensions
IMAGE_PREVIEW_MAX_WIDTH = 600
IMAGE_PREVIEW_MAX_HEIGHT = 260

# Timer intervals (milliseconds)
TIMER_SAVE_CONFIG_INTERVAL = 500
TIMER_CROP_PREVIEW_INTERVAL = 100
TIMER_RESIZE_PREVIEW_INTERVAL = 100
