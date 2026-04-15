# Models Folder - Python Files List

## 📂 Location: `/nvme0n1-disk/nvme01/HeyGem/models/`

---

## 🐍 All Python Files Found (12 files)

### **IndicTrans2 Inference Module**

#### 1. Core Inference Files
```
models/IndicTrans2/inference/
├── __init__.py                          # Package initialization
├── engine.py                            # Main inference engine
├── custom_interactive.py                # Interactive translation interface
└── download.py                          # Model download utilities
```

#### 2. Configuration Files
```
models/IndicTrans2/inference/model_configs/
├── __init__.py                          # Model config initialization
└── custom_transformer.py                # Custom transformer configurations
```

#### 3. Normalization & Utilities
```
models/IndicTrans2/inference/
├── flores_codes_map_indic.py            # Language code mappings
├── indic_num_map.py                     # Indic numeral mappings
├── normalize_punctuation.py             # Punctuation normalization
└── normalize_regex_inference.py         # Regex-based normalization
```

#### 4. Triton Server (Optional)
```
models/IndicTrans2/inference/triton_server/
├── client.py                            # Triton client
└── triton_repo/nmt/1/model.py          # Triton model wrapper
```

---

## 📊 File Details

| # | File Path | Purpose | Git Push? |
|---|-----------|---------|-----------|
| 1 | `IndicTrans2/inference/__init__.py` | Package init | ✅ YES |
| 2 | `IndicTrans2/inference/engine.py` | Main inference engine | ✅ YES |
| 3 | `IndicTrans2/inference/custom_interactive.py` | Interactive CLI | ✅ YES |
| 4 | `IndicTrans2/inference/download.py` | Model downloader | ✅ YES |
| 5 | `IndicTrans2/inference/flores_codes_map_indic.py` | Language codes | ✅ YES |
| 6 | `IndicTrans2/inference/indic_num_map.py` | Number mappings | ✅ YES |
| 7 | `IndicTrans2/inference/normalize_punctuation.py` | Punctuation | ✅ YES |
| 8 | `IndicTrans2/inference/normalize_regex_inference.py` | Regex utils | ✅ YES |
| 9 | `IndicTrans2/inference/model_configs/__init__.py` | Config init | ✅ YES |
| 10 | `IndicTrans2/inference/model_configs/custom_transformer.py` | Transformer config | ✅ YES |
| 11 | `IndicTrans2/inference/triton_server/client.py` | Triton client | ⚠️ OPTIONAL |
| 12 | `IndicTrans2/inference/triton_server/triton_repo/nmt/1/model.py` | Triton model | ⚠️ OPTIONAL |

---

## ⚠️ Important Notes

### **Should Push to Git:**
✅ **YES** - All these Python files are **code files**, not model weights
- They are part of the IndicTrans2 inference library
- Required for translation functionality
- Small file sizes (typically < 100 KB each)
- Essential for the application to work

### **Should NOT Push:**
❌ **NO** - Model weight files (separate from these .py files):
- `*.pth` files
- `*.ckpt` files
- `*.safetensors` files
- `*.bin` files
- Large model directories

---

## 📦 Recommended Git Add Commands

### Option 1: Add All Python Files
```bash
cd /nvme0n1-disk/nvme01/HeyGem
git add models/IndicTrans2/inference/*.py
git add models/IndicTrans2/inference/model_configs/*.py
```

### Option 2: Add Entire IndicTrans2 Inference Code (Recommended)
```bash
cd /nvme0n1-disk/nvme01/HeyGem
git add models/IndicTrans2/inference/
```

**Note:** Make sure your `.gitignore` excludes model weights:
```gitignore
# In .gitignore
models/**/*.pth
models/**/*.ckpt
models/**/*.safetensors
models/**/*.bin
```

---

## 🔍 File Size Check

To verify file sizes before pushing:
```bash
cd /nvme0n1-disk/nvme01/HeyGem/models/IndicTrans2/inference
find . -name "*.py" -exec ls -lh {} \;
```

---

## ✅ Recommendation

**PUSH THESE FILES** - They are essential code files for:
1. IndicTrans2 translation functionality
2. Language normalization
3. Model configuration
4. Inference engine

**Total estimated size:** < 500 KB (all Python files combined)

---

## 🚀 Updated Git Push Checklist

Add to your existing push commands:
```bash
# Add IndicTrans2 inference code
git add models/IndicTrans2/inference/

# Or individually
git add models/IndicTrans2/inference/__init__.py
git add models/IndicTrans2/inference/engine.py
git add models/IndicTrans2/inference/custom_interactive.py
git add models/IndicTrans2/inference/download.py
git add models/IndicTrans2/inference/flores_codes_map_indic.py
git add models/IndicTrans2/inference/indic_num_map.py
git add models/IndicTrans2/inference/normalize_punctuation.py
git add models/IndicTrans2/inference/normalize_regex_inference.py
git add models/IndicTrans2/inference/model_configs/__init__.py
git add models/IndicTrans2/inference/model_configs/custom_transformer.py
```

---

**Created:** 2026-01-29  
**Purpose:** Git push decision for models folder Python files
