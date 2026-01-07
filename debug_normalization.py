
from webapp_chunked.text_normalization import latex_to_speech

text = """Would you like me to solve a problem using this formula, for example: 2x2+5x−3=0​"""

print(f"Original: {text}")
print("-" * 40)
normalized = latex_to_speech(text)
print(f"Normalized: {normalized}")
print("-" * 40)
