import re
from ai.plate_patterns import PLATE_PATTERNS

class PlateCorrector:
    def detect_country(self, text):
        for country, pattern in PLATE_PATTERNS.items():
            if re.match(pattern, text):
                return country
        return None

    def smart_correct(self, text):
        text = text.upper().replace(" ", "").strip()
        
        country = self.detect_country(text)
        if country: return text, country

       
        replacements = [
            ('O', '0'), ('Q', '0'), ('I', '1'), ('L', '1'),
            ('Z', '2'), ('S', '5'), ('B', '8'), ('G', '6'),
            ('0', 'O'), ('1', 'I'), ('8', 'B'), ('5', 'S')
        ]

        current_text = text
        for old, new in replacements:
            test_text = current_text.replace(old, new)
            new_country = self.detect_country(test_text)
            if new_country:
                return test_text, new_country

        return text, None