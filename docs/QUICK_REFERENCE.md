# 🎾 Platform Tennis Video Enhancement - Quick Reference

## 🚀 Three Ways to Get Better Videos

### 1. Guided Setup (Easiest)
```bash
python setup_youtube_api.py
```
**What it does**: Walks you through everything step-by-step

### 2. YouTube API Search
```bash
export YOUTUBE_API_KEY="your_api_key_here"
python fix_youtube_links.py
```
**What it does**: Automatically finds technique-specific videos

### 3. Manual Curation (Best Quality)
```bash
python fix_youtube_links.py --manual-help
```
**What it does**: Shows you which techniques need better videos and suggests search terms

## 🎯 Priority Techniques to Improve

1. **Screen footwork and timing** - Unique to platform tennis
2. **Serve technique and consistency** - Foundation skill  
3. **Overhead technique and control** - Point-winning shots
4. **Return depth and direction** - Defensive foundation

## 🔍 Best Search Terms

```
"platform tennis [technique] technique tutorial"
"paddle tennis [technique] instruction professional"
"platform tennis [technique] strategy"
```

## 📊 Current Status

✅ **65 techniques** have working videos  
🎯 **7 priority techniques** identified for manual curation  
🔄 **Automatic backups** protect your data  
📈 **Enhanced search** finds better matches  

## 🛠️ Quick Commands

```bash
# See what needs improvement
python fix_youtube_links.py --manual-help

# Run enhanced search (with API)
python fix_youtube_links.py

# Interactive setup
python setup_youtube_api.py

# Check current videos
grep -c "youtube.com" data/complete_platform_tennis_training_guide.json
```

## 📖 Full Documentation

- **Complete Guide**: `ENHANCED_VIDEO_SYSTEM_SUMMARY.md`
- **API Setup**: `YOUTUBE_API_SETUP_GUIDE.md`  
- **Original README**: `YOUTUBE_LINKS_FIXED_README.md`

---
**🎾 Start with: `python setup_youtube_api.py`** 