# Amazon Photos Video Storage Management — Quickstart Guide

This tool connects to your Amazon Photos account, finds all uploaded videos, calculates their sizes, and sorts them from largest to smallest so you can quickly identify what is taking up storage space and remove unwanted large files.

---

## 1. Quick Cookie Extraction (60 seconds)

Amazon does not provide standard API keys for personal photos, so the tool uses your active session cookies from the web browser.

### In Google Chrome / Microsoft Edge / Brave:
1. Open your browser and navigate to [Amazon Photos](https://www.amazon.com/photos) (or your regional Amazon Photos page).
2. Ensure you are signed in and can see your photos.
3. Press **F12** (or Right-Click anywhere on the page and select **Inspect**) to open Developer Tools.
4. Click on the **Application** tab at the top (if you don't see it, click the `>>` chevron icon).
5. In the left sidebar, expand **Storage** > **Cookies**, and click on `https://www.amazon.com`.
6. Look for and copy the values for these **3 cookies**:
   - `session-id` (e.g., `123-4567890-1234567`)
   - `ubid-main` (or `ubid-acb<country>` if outside the US)
   - `at-main` (or `at-acb<country>` if outside the US)

### In Firefox:
1. Press **F12** > Click the **Storage** tab > **Cookies** > `https://www.amazon.com`.
2. Copy `session-id`, `ubid-main`, and `at-main`.

### In Safari:
1. Enable Developer menu (**Safari Settings** > **Advanced** > check *"Show features for web developers"*).
2. Press **Option + Command + I** > **Storage** > **Cookies**.
3. Copy `session-id`, `ubid-main`, and `at-main`.

---

## 2. Configuration

Choose either **Method A** (`.env`) or **Method B** (`cookies.json`):

### Method A: Using `.env` (Recommended)
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Open `.env` and fill in your values:
```ini
AMAZON_SESSION_ID=123-4567890-1234567
AMAZON_UBID_MAIN=123-4567890-1234567
AMAZON_AT_MAIN=Atza|...
AMAZON_TLD=com
```

### Method B: Using `cookies.json`
Create a file named `cookies.json` in this folder:
```json
{
  "session-id": "123-4567890-1234567",
  "ubid-main": "123-4567890-1234567",
  "at-main": "Atza|...",
  "tld": "com"
}
```

---

## 3. Running the Tool

Activate the virtual environment:
```powershell
.venv\Scripts\Activate.ps1
```

### Scan & List Largest Videos:
```powershell
python find_large_videos.py
```
This will:
- Connect to Amazon Photos.
- Retrieve all your videos.
- Print a summary of total video storage consumed.
- Display a table of the top 25 largest videos (rank, size, date, resolution, filename, node ID).
- Export the complete inventory to `amazon_videos_by_size.csv`.

### Show More or Filter:
```powershell
# Show top 50 videos
python find_large_videos.py --limit 50

# Only list videos larger than 200 MB
python find_large_videos.py --min-size-mb 200

# Save to a custom CSV file
python find_large_videos.py --csv my_large_videos.csv
```

---

## 4. Cleaning Up / Freeing Space

### Safe Deletion (Moving to Trash):
Videos moved to Trash can be restored from the Amazon Photos web app if you change your mind.

1. **Move specific video by Node ID** (found in the table or CSV):
   ```powershell
   python find_large_videos.py --trash <NODE_ID>
   ```

2. **Move multiple videos to Trash**:
   ```powershell
   python find_large_videos.py --trash <NODE_ID_1> <NODE_ID_2> <NODE_ID_3>
   ```

3. **Interactive Top-N Deletion**:
   ```powershell
   python find_large_videos.py --trash-top 10
   ```
   *(This shows the estimated space to be freed and requires typing `yes` to confirm.)*

4. **Emptying Trash**:
   Log into [Amazon Photos Trash](https://www.amazon.com/photos/trash) on the web to permanently empty the trash bin and reclaim your account storage!
