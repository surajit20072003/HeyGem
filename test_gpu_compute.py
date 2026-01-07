#!/usr/bin/env python3
"""
Simple GPU Compute Test
Tests if GPU 1 and GPU 2 can actually run CUDA computations
"""
import torch
import time

def test_gpu(gpu_id):
    """Test a specific GPU with matrix multiplication"""
    print(f"\n{'='*60}")
    print(f"Testing GPU {gpu_id}")
    print(f"{'='*60}")
    
    if not torch.cuda.is_available():
        print(f"❌ CUDA not available!")
        return False
    
    device_count = torch.cuda.device_count()
    print(f"Total CUDA devices: {device_count}")
    
    if gpu_id >= device_count:
        print(f"❌ GPU {gpu_id} not found (only {device_count} devices available)")
        return False
    
    try:
        # Set device
        device = torch.device(f'cuda:{gpu_id}')
        print(f"✅ Device: {torch.cuda.get_device_name(gpu_id)}")
        
        # Allocate memory
        print(f"\n🧪 Running compute test...")
        size = 5000
        
        # Create large tensors
        a = torch.randn(size, size, device=device)
        b = torch.randn(size, size, device=device)
        
        # Warm up
        _ = torch.matmul(a, b)
        torch.cuda.synchronize(device)
        
        # Timed test
        start = time.time()
        for i in range(10):
            c = torch.matmul(a, b)
            torch.cuda.synchronize(device)
            if i % 3 == 0:
                print(f"   Iteration {i+1}/10 complete")
        
        elapsed = time.time() - start
        
        # Check memory
        mem_allocated = torch.cuda.memory_allocated(device) / 1024**2
        mem_reserved = torch.cuda.memory_reserved(device) / 1024**2
        
        print(f"\n✅ GPU {gpu_id} Test PASSED!")
        print(f"   Time: {elapsed:.2f}s for 10 iterations")
        print(f"   Memory allocated: {mem_allocated:.1f} MB")
        print(f"   Memory reserved: {mem_reserved:.1f} MB")
        
        # Cleanup
        del a, b, c
        torch.cuda.empty_cache()
        
        return True
        
    except Exception as e:
        print(f"\n❌ GPU {gpu_id} Test FAILED!")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("GPU Compute Test - Testing GPU 1 and GPU 2")
    print("="*60)
    
    results = {}
    
    # Test GPU 1
    results[1] = test_gpu(1)
    
    # Test GPU 2
    results[2] = test_gpu(2)
    
    # Test GPU 0 for comparison
    results[0] = test_gpu(0)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for gpu_id, passed in results.items():
        status = "✅ WORKING" if passed else "❌ FAILED"
        print(f"GPU {gpu_id}: {status}")
    print("="*60)
