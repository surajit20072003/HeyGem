#!/usr/bin/env python3
"""
IndicTrans2 Translation Wrapper for HeyGem Chatterbox
Supports English → Kannada (and other Indian languages)
"""
import sys
import os

# Get HeyGem root directory
HEYGEM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDICTRANS_PATH = os.path.join(HEYGEM_ROOT, 'models', 'IndicTrans2')

# Add to path
sys.path.append(INDICTRANS_PATH)

from inference.engine import Model

class IndicTranslator:
    """Wrapper for IndicTrans2 translation"""
    
    LANGUAGE_CODES = {
        'kannada': 'kan_Knda',
        'hindi': 'hin_Deva',
        'bengali': 'ben_Beng',
        'tamil': 'tam_Taml',
        'telugu': 'tel_Telu',
        'malayalam': 'mal_Mlym',
        'marathi': 'mar_Deva',
        'gujarati': 'guj_Gujr',
        'punjabi': 'pan_Guru',
        'odia': 'ory_Orya',
        'assamese': 'asm_Beng'
    }
    
    def __init__(self):
        # Use relative path from HeyGem root
        model_dir = os.path.join(
            HEYGEM_ROOT,
            'models',
            'IndicTrans2',
            'en-indic-exp',
            'en-indic-preprint',
            'ct2_fp16_model'
        )
        self.model_dir = model_dir
        self.model = None
        print(f"📚 IndicTranslator initialized with model dir: {model_dir}")
        
    def load_model(self):
        """Load IndicTrans2 model (lazy loading)"""
        if self.model is None:
            print(f"🔄 Loading IndicTrans2 model from {self.model_dir}...")
            try:
                self.model = Model(self.model_dir, model_type="ctranslate2")
                print("✅ IndicTrans2 model loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load IndicTrans2: {e}")
                raise
    
    def translate(self, text, src_lang="eng_Latn", tgt_lang="kan_Knda"):
        """
        Translate text from source to target language
        
        Args:
            text: Text to translate (string or list)
            src_lang: Source language code (default: eng_Latn)
            tgt_lang: Target language code (default: kan_Knda)
        
        Returns:
            Translated text (string or list)
        """
        self.load_model()
        
        # Handle single string or list
        sentences = [text] if isinstance(text, str) else text
        
        # Translate
        translations = self.model.batch_translate(sentences, src_lang, tgt_lang)
        
        # Return single string or list
        return translations[0] if len(translations) == 1 else translations
    
    def english_to_kannada(self, text):
        """Convenience method: English → Kannada"""
        return self.translate(text, "eng_Latn", "kan_Knda")
    
    def english_to_language(self, text, language):
        """
        Translate English to any supported Indian language
        
        Args:
            text: English text
            language: Language name (e.g., 'kannada', 'hindi')
        """
        lang_code = self.LANGUAGE_CODES.get(language.lower())
        if not lang_code:
            raise ValueError(f"Unsupported language: {language}")
        
        return self.translate(text, "eng_Latn", lang_code)

# Test
if __name__ == "__main__":
    print("="*70)
    print("🧪 Testing IndicTranslator")
    print("="*70)
    
    translator = IndicTranslator()
    
    # Test translation
    english_text = "Hello, how are you? I hope you are doing well."
    print(f"\n📝 English: {english_text}")
    
    kannada_text = translator.english_to_kannada(english_text)
    print(f"🇮🇳 Kannada: {kannada_text}")
    
    print("\n✅ Translation test successful!")
