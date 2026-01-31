#!/usr/bin/env python3
"""
Sarvam.ai TTS API Wrapper for HeyGem Chatterbox
Supports 11 Indian languages includig Kannada
Updated with Chunking Support (Max 250 chars)
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
            
    def _split_text(self, text, max_chars=250):
        """Split text into chunks respecting sentence boundaries"""
        if len(text) <= max_chars:
            return [text]
            
        chunks = []
        # Split by common Indian language delimiters
        # Danda (single and double), Question mark, Exclamation, Full stop
        import re
        sentences = re.split(r'(?<=[।॥?!.])\s+', text)
        
        current_chunk = ""
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # If single sentence is too long, force split it
            if len(sentence) > max_chars:
                # If current chunk has data, append it first
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # Split long sentence by spaces (words)
                words = sentence.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= max_chars:
                        temp_chunk += word + " "
                    else:
                        chunks.append(temp_chunk.strip())
                        temp_chunk = word + " "
                if temp_chunk:
                    chunks.append(temp_chunk.strip())
                    
            elif len(current_chunk) + len(sentence) + 1 <= max_chars:
                current_chunk += sentence + " "
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def _merge_audio_files(self, file_paths, output_path):
        """Merge multiple audio files using ffmpeg"""
        if not file_paths:
            return False
            
        list_file = f"{output_path}_list.txt"
        
        try:
            # Create ffmpeg concat list
            with open(list_file, 'w') as f:
                for path in file_paths:
                    f.write(f"file '{path}'\n")
            
            # Use ffmpeg to concat
            import subprocess
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', list_file, '-c', 'copy', output_path
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            return True
            
        except Exception as e:
            print(f"   ❌ Error merging audio: {e}")
            return False
        finally:
            if os.path.exists(list_file):
                try:
                    os.remove(list_file)
                except:
                    pass

    def generate(self, text, language='kannada', speaker='abhilash', task_id=None, output_dir=None):
        """
        Generate TTS audio using Sarvam.ai with chunking strategy
        """
        # Get language code
        lang_code = self.SUPPORTED_LANGUAGES.get(language.lower())
        if not lang_code:
            raise ValueError(f"Unsupported language: {language}. Supported: {list(self.SUPPORTED_LANGUAGES.keys())}")
        
        # Default output directory
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Split text into chunks
        chunks = self._split_text(text, max_chars=250)
        print(f"   🌐 Sarvam.ai: Split text into {len(chunks)} chunks (Max 250 chars)")
        print(f"      Original length: {len(text)} chars")
        
        # Step 2: Generate audio for each chunk
        temp_files = []
        base_filename = task_id if task_id else f"sarvam_{int(time.time())}"
        
        try:
            for i, chunk in enumerate(chunks):
                if not chunk.strip(): continue
                
                print(f"      Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
                
                headers = {
                    'API-Subscription-Key': self.api_key,
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'inputs': [chunk],
                    'target_language_code': lang_code,
                    'speaker': speaker,
                    'pitch': 0,
                    'pace': 1.0,
                    'loudness': 1.5,
                    'speech_sample_rate': 24000,
                    'enable_preprocessing': True,
                    'model': 'bulbul:v2'
                }
                
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'audios' in result and len(result['audios']) > 0:
                        import base64
                        audio_base64 = result['audios'][0]
                        audio_bytes = base64.b64decode(audio_base64)
                        
                        chunk_path = os.path.join(output_dir, f"{base_filename}_part_{i}.wav")
                        with open(chunk_path, 'wb') as f:
                            f.write(audio_bytes)
                        temp_files.append(chunk_path)
                    else:
                        print(f"      ⚠️ No audio for chunk {i+1}")
                else:
                    print(f"      ⚠️ API Error chunk {i+1}: {response.status_code} - {response.text}")
                    # Continue to try other chunks
            
            if not temp_files:
                raise Exception("Failed to generate any audio chunks")
            
            # Step 3: Merge chunks
            output_filename = f"{base_filename}.wav"
            output_path = os.path.join(output_dir, output_filename)
            
            final_path = None
            
            if len(temp_files) == 1:
                # Just move the single file
                if os.path.exists(output_path): os.remove(output_path)
                os.rename(temp_files[0], output_path)
                final_path = output_path
                print(f"   ✅ Single chunk saved to {output_path}")
            else:
                # Merge multiple files
                if self._merge_audio_files(temp_files, output_path):
                    final_path = output_path
                    print(f"   ✅ Merged {len(temp_files)} chunks to {output_path}")
                    # Cleanup temp files
                    for tmp in temp_files:
                        if os.path.exists(tmp): os.remove(tmp)
                else:
                    print(f"   ⚠️ Merge failed, using first chunk")
                    final_path = temp_files[0]
            
            if final_path:
                file_size = os.path.getsize(final_path)
                print(f"   ✅ Sarvam.ai audio complete: {os.path.basename(final_path)} ({file_size:,} bytes)")
                return final_path
            else:
                raise Exception("Audio generation failed")
            
        except Exception as e:
            print(f"   ❌ Sarvam TTS Error: {e}")
            import traceback
            traceback.print_exc()
            raise

# Test
if __name__ == "__main__":
    import sys
    
    print("="*70)
    print("🧪 Testing Sarvam.ai TTS with Chunking")
    print("="*70)
    
    # Get API key from environment
    api_key = os.getenv('SARVAM_API_KEY')
    
    if not api_key:
        print("\n❌ Error: SARVAM_API_KEY environment variable not set")
        sys.exit(1)
    
    tts = SarvamTTS(api_key)
    
    # Long text for testing
    long_text = "Namaskar. This is a very long text to test chunking capabilities. " * 10
    print(f"\n📝 Testing with {len(long_text)} chars...")
    
    try:
        audio_path = tts.generate(long_text, language='hindi', speaker='meera')
        print(f"\n✅ Test successful!")
        print(f"   Audio saved to: {audio_path}")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
