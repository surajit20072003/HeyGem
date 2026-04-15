# Models Folder - Config & Vocab Files Analysis

## 📂 Location: `/nvme0n1-disk/nvme01/HeyGem/models/IndicTrans2/`

---

## 📊 All JSON, TGT, SRC, ZIP Files (21 files)

### **File Type Summary:**
- **JSON files:** 3 (config files)
- **ZIP files:** 2 (vocabulary archives)
- **SRC files:** 8 (source vocabulary)
- **TGT files:** 8 (target vocabulary)
- **Total:** 21 files
- **Total Size:** ~30 MB

---

## 📁 Detailed File List with Sizes

### **1. Configuration Files (JSON)**

| File | Size | Purpose | Push? |
|------|------|---------|-------|
| `inference/triton_server/dhruva/ulca_model.json` | 112 KB | Triton model config | ⚠️ OPTIONAL |
| `en-indic-exp/en-indic-preprint/ct2_fp16_model/config.json` | 158 B | FP16 model config | ✅ YES |
| `en-indic-exp/en-indic-preprint/ct2_int8_model/config.json` | 158 B | INT8 model config | ✅ YES |

**Subtotal:** ~112 KB

---

### **2. Vocabulary Archives (ZIP)**

| File | Size | Purpose | Push? |
|------|------|---------|-------|
| `en-indic-exp/en-indic-spm.zip` | 2.8 MB | SentencePiece model | ✅ YES |
| `en-indic-exp/en-indic-fairseq-dict.zip` | 983 KB | Fairseq dictionary | ✅ YES |

**Subtotal:** ~3.8 MB

---

### **3. Vocabulary Files (SRC/TGT)**

#### **3a. Main Vocab Directory**
```
en-indic-exp/vocab/
├── model.SRC     742 KB    # Source tokenizer model
├── model.TGT     3.2 MB    # Target tokenizer model
├── vocab.SRC     468 KB    # Source vocabulary
└── vocab.TGT     2.8 MB    # Target vocabulary
```
**Subtotal:** ~7.2 MB

#### **3b. FP16 Model Vocab**
```
en-indic-exp/en-indic-preprint/ct2_fp16_model/vocab/
├── model.SRC     742 KB
├── model.TGT     3.2 MB
├── vocab.SRC     468 KB
└── vocab.TGT     2.8 MB
```
**Subtotal:** ~7.2 MB

#### **3c. INT8 Model Vocab**
```
en-indic-exp/en-indic-preprint/ct2_int8_model/vocab/
├── model.SRC     742 KB
├── model.TGT     3.2 MB
├── vocab.SRC     468 KB
└── vocab.TGT     2.8 MB
```
**Subtotal:** ~7.2 MB

#### **3d. Fairseq Model Vocab**
```
en-indic-exp/en-indic-preprint/fairseq_model/vocab/
├── model.SRC     742 KB
├── model.TGT     3.2 MB
├── vocab.SRC     468 KB
└── vocab.TGT     2.8 MB
```
**Subtotal:** ~7.2 MB

---

## 📈 Size Breakdown

| Category | Files | Total Size | Push to Git? |
|----------|-------|------------|--------------|
| JSON configs | 3 | ~112 KB | ✅ YES |
| ZIP archives | 2 | ~3.8 MB | ✅ YES |
| Vocab files (SRC/TGT) | 16 | ~29 MB | ✅ YES |
| **TOTAL** | **21** | **~33 MB** | **✅ YES** |

---

## ✅ Recommendation: **PUSH करें!**

### **क्यों Push करना चाहिए:**

1. **Essential Files हैं:**
   - ये vocabulary और configuration files हैं
   - Translation के लिए absolutely जरूरी हैं
   - इनके बिना model काम नहीं करेगा

2. **Reasonable Size:**
   - Total ~33 MB (manageable for Git)
   - Model weights (GB size) नहीं हैं
   - Standard vocabulary files हैं

3. **No Regeneration:**
   - ये files manually download की गई थीं
   - Regenerate नहीं हो सकतीं easily
   - Repository के साथ होनी चाहिए

4. **Required for Deployment:**
   - नई machine पर deploy करते समय ये चाहिए होंगी
   - IndicTrans2 setup के part हैं

---

## ⚠️ Alternative: Git LFS (Large File Storage)

अगर आप Git repository को light रखना चाहते हैं:

### **Option 1: Use Git LFS**
```bash
# Install Git LFS
git lfs install

# Track large files
git lfs track "models/**/*.zip"
git lfs track "models/**/*.TGT"
git lfs track "models/**/*.SRC"

# Add .gitattributes
git add .gitattributes

# Then add files normally
git add models/IndicTrans2/en-indic-exp/
```

### **Option 2: Regular Git Push (Recommended)**
```bash
# Simple approach - just push everything
git add models/IndicTrans2/en-indic-exp/
git add models/IndicTrans2/inference/triton_server/dhruva/ulca_model.json
```

---

## 🚀 Git Commands

### **Add All Config & Vocab Files:**
```bash
cd /nvme0n1-disk/nvme01/HeyGem

# Add JSON configs
git add models/IndicTrans2/en-indic-exp/en-indic-preprint/ct2_fp16_model/config.json
git add models/IndicTrans2/en-indic-exp/en-indic-preprint/ct2_int8_model/config.json
git add models/IndicTrans2/inference/triton_server/dhruva/ulca_model.json

# Add ZIP archives
git add models/IndicTrans2/en-indic-exp/en-indic-spm.zip
git add models/IndicTrans2/en-indic-exp/en-indic-fairseq-dict.zip

# Add all vocab directories
git add models/IndicTrans2/en-indic-exp/vocab/
git add models/IndicTrans2/en-indic-exp/en-indic-preprint/ct2_fp16_model/vocab/
git add models/IndicTrans2/en-indic-exp/en-indic-preprint/ct2_int8_model/vocab/
git add models/IndicTrans2/en-indic-exp/en-indic-preprint/fairseq_model/vocab/
```

### **Or Add Entire Directory (Easier):**
```bash
cd /nvme0n1-disk/nvme01/HeyGem
git add models/IndicTrans2/en-indic-exp/
git add models/IndicTrans2/inference/triton_server/dhruva/
```

---

## ❌ Still DON'T Push:

These are the actual model weights (NOT in this list):
```
models/**/*.pth          # PyTorch weights (GBs)
models/**/*.ckpt         # Checkpoints (GBs)
models/**/*.safetensors  # SafeTensor weights (GBs)
models/**/*.bin          # Binary model files (GBs)
```

---

## 📋 Updated .gitignore

Make sure your `.gitignore` has:
```gitignore
# Allow vocab and config files
!models/**/*.json
!models/**/*.zip
!models/**/*.SRC
!models/**/*.TGT
!models/**/*.src
!models/**/*.tgt

# But exclude large model weights
models/**/*.pth
models/**/*.ckpt
models/**/*.safetensors
models/**/*.bin
```

---

## 🎯 Final Recommendation

### **✅ PUSH करें (Recommended):**
- सभी 21 files push करें
- Total ~33 MB है (acceptable)
- Essential files हैं
- Deployment के लिए जरूरी हैं

### **📊 Impact:**
- Repository size: +33 MB
- Clone time: +5-10 seconds
- Essential for functionality: YES

---

## 🔍 Verify Before Push

```bash
# Check what will be added
cd /nvme0n1-disk/nvme01/HeyGem
git add models/IndicTrans2/en-indic-exp/
git status

# See total size
du -sh models/IndicTrans2/en-indic-exp/
```

---

**Created:** 2026-01-29  
**Decision:** ✅ PUSH ALL CONFIG & VOCAB FILES  
**Total Size:** ~33 MB  
**Files:** 21 (JSON, ZIP, SRC, TGT)
