import re

# ai/plate_patterns.py

PLATE_PATTERNS = {

    "KZ_NEW_3L": r"^\d{3}[A-Z]{3}\d{2}$",

    "KZ_NEW_2L": r"^\d{3}[A-Z]{2}\d{2}$",

    "KZ_OLD": r"^[A-Z]\d{3}[A-Z]{2}$",

    "KZ_DIP": r"^[A-Z]\d{6}$",

    "CN": r"^[A-Z]\d{5}$",

    "RU": r"^[A-Z]\d{3}[A-Z]{2}\d{2,3}$"
}



