#!/usr/bin/env python3
"""
Quick test script for Dual TTS system
Tests TTS services and GPU containers
"""
import requests
import time


def test_tts_service(port: int, name: str):
    """Test TTS service availability"""
    try:
        print(f"\n🧪 Testing {name} (Port {port})...")
        
        # Try health check (might fail if no /health endpoint)
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            print(f"   Health check: {response.status_code}")
        except:
            print(f"   Health check: Not available (expected)")
        
        # Try basic endpoint check
        response = requests.get(f"http://localhost:{port}", timeout=5)
        print(f"   ✅ {name} is responding")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"   ❌ {name} is NOT responding (container may not be running)")
        return False
    except Exception as e:
        print(f"   ⚠️  {name} error: {e}")
        return False


def test_gpu_container(port: int, gpu_id: int):
    """Test GPU container availability"""
    try:
        print(f"\n🧪 Testing GPU {gpu_id} Container (Port {port})...")
        
        # Try query endpoint
        response = requests.get(
            f"http://localhost:{port}/easy/query?code=test",
            timeout=5
        )
        print(f"   ✅ GPU {gpu_id} container is responding")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"   ❌ GPU {gpu_id} container is NOT responding")
        return False
    except Exception as e:
        print(f"   ⚠️  GPU {gpu_id} error: {e}")
        return False


def test_webapp():
    """Test webapp availability"""
    try:
        print(f"\n🧪 Testing Webapp (Port 5003)...")
        
        response = requests.get("http://localhost:5003/api/info", timeout=5)
        
        if response.status_code == 200:
            info = response.json()
            print(f"   ✅ Webapp is running")
            print(f"   Service: {info.get('service')}")
            print(f"   Version: {info.get('version')}")
            return True
        else:
            print(f"   ⚠️  Webapp responded with: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Webapp is NOT running")
        print(f"   Start it with: python3 app.py")
        return False
    except Exception as e:
        print(f"   ⚠️  Webapp error: {e}")
        return False


def main():
    print("="*80)
    print("🚀 Dual TTS System - Quick Test")
    print("="*80)
    
    results = {
        "tts0": test_tts_service(18182, "TTS Service 0 (GPU 0) [heygem-tts-dual-0]"),
        "tts1": test_tts_service(18183, "TTS Service 1 (GPU 1) [heygem-tts-dual-1]"),
        "gpu0": test_gpu_container(8390, 0),
        "gpu1": test_gpu_container(8391, 1),
        "webapp": test_webapp()
    }
    
    print("\n" + "="*80)
    print("📊 Test Results Summary")
    print("="*80)
    
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {service.upper()}: {'PASS' if status else 'FAIL'}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ All tests PASSED! System is ready!")
    else:
        print("⚠️  Some tests FAILED. Check the output above.")
        print("\n💡 Troubleshooting:")
        print("   1. Start Docker containers: docker-compose -f docker-compose-dual-tts.yml up -d")
        print("   2. Check container status: docker ps")
        print("   3. Check logs: docker logs heygem-tts-0")
        print("   4. Start webapp: cd webapp_dual_tts && python3 app.py")
    print("="*80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
