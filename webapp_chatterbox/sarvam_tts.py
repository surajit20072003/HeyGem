#!/usr/bin/env python3
"""
Sarvam.ai TTS API Wrapper for HeyGem Chatterbox
Supports 11 Indian languages including Kannada
"""
import requests
import os
import time

class SarvamTTS:
    """Wrapper for Sarvam.ai Text-to-Speech API"""
    
    SUPPORTED_LANGUAGES = {
        'kannada': 'kn-IN',
        'hindi': 'hi-IN',
        'bengali': 'bn-IN',
        'tamil': 'ta-IN',
        'telugu': 'te-IN',
        'malayalam': 'ml-IN',
        'marathi': 'mr-IN',
        'gujarati': 'gu-IN',
        'punjabi': 'pa-IN',
        'odia': 'or-IN',
        'assamese': 'as-IN'
    }
    
    def __init__(self, api_key):
        """
        Initialize Sarvam TTS client
        
        Args:
            api_key: Sarvam.ai API key
        """
        self.api_key = api_key
        self.base_url = "https://api.sarvam.ai/text-to-speech"
        
        if not api_key:
            print("⚠️  Warning: Sarvam API key not provided")
    
    def generate(self, text, language='kannada', speaker='abhilash', task_id=None, output_dir=None):
        """
        Generate TTS audio using Sarvam.ai
        
        Args:
            text: Text to convert to speech (in target language)
            language: Language name (e.g., 'kannada')
            speaker: Voice speaker ID (default: 'meera')
                    Valid options: anushka, abhilash, manisha, vidya, arya, karun, 
                                  hitesh, aditya, ritu, priya, neha, rahul, pooja, etc.
            task_id: Optional task ID for filename
            output_dir: Directory to save audio (default: temp/)
        
        Returns:
            Path to generated audio file
        
        Raises:
            Exception: If API call fails
        """
        # Get language code
        lang_code = self.SUPPORTED_LANGUAGES.get(language.lower())
        if not lang_code:
            raise ValueError(f"Unsupported language: {language}. Supported: {list(self.SUPPORTED_LANGUAGES.keys())}")
        
        # Default output directory
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare request
        headers = {
            'API-Subscription-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'inputs': [text],
            'target_language_code': lang_code,
            'speaker': speaker,
            'pitch': 0,
            'pace': 1.0,
            'loudness': 1.5,
            'speech_sample_rate': 24000,
            'enable_preprocessing': True,
            'model': 'bulbul:v2'  # Updated to v2
        }
        
        print(f"   🌐 Calling Sarvam.ai API...")
        print(f"      Language: {language} ({lang_code})")
        print(f"      Text length: {len(text)} chars")
        
        try:
            start_time = time.time()
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            api_time = time.time() - start_time
            
            if response.status_code == 200:
                # Parse response
                result = response.json()
                
                # Get audio data (base64 encoded)
                if 'audios' in result and len(result['audios']) > 0:
                    import base64
                    audio_base64 = result['audios'][0]
                    audio_bytes = base64.b64decode(audio_base64)
                    
                    # Generate output filename
                    if task_id:
                        output_filename = f"sarvam_tts_{task_id}.wav"
                    else:
                        output_filename = f"sarvam_tts_{int(time.time())}.wav"
                    
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Save audio
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
                    
                    file_size = os.path.getsize(output_path)
                    print(f"   ✅ Sarvam.ai audio generated")
                    print(f"      File: {output_filename}")
                    print(f"      Size: {file_size:,} bytes")
                    print(f"      API time: {api_time:.2f}s")
                    
                    return output_path
                else:
                    raise Exception("No audio data in API response")
            else:
                error_msg = f"Sarvam API error: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text}"
                
                print(f"   ❌ {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            raise Exception("Sarvam.ai API timeout (30s)")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Sarvam.ai API request error: {str(e)}")
        except Exception as e:
            raise Exception(f"Sarvam.ai API error: {str(e)}")

# Test
if __name__ == "__main__":
    import sys
    
    print("="*70)
    print("🧪 Testing Sarvam.ai TTS")
    print("="*70)
    
    # Get API key from environment
    api_key = os.getenv('SARVAM_API_KEY')
    
    if not api_key:
        print("\n❌ Error: SARVAM_API_KEY environment variable not set")
        print("   Set it with: export SARVAM_API_KEY='your_key_here'")
        sys.exit(1)
    
    # Initialize TTS
    tts = SarvamTTS(api_key)
    
    # Test Kannada TTS
    print("\n📝 Testing Kannada TTS...")
    kannada_text = "ನಮಸ್ಕಾರ! ಇದು ಪರೀಕ್ಷೆ. ಸರ್ವಮ್ ಏಪಿಐ ಚೆನ್ನಾಗಿ ಕೆಲಸ ಮಾಡುತ್ತಿದೆ."
    
    try:
        audio_path = tts.generate(kannada_text, language='kannada', speaker='manisha')
        print(f"\n✅ Test successful!")
        print(f"   Audio saved to: {audio_path}")
        print(f"\n🎵 Play with: ffplay {audio_path}")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
