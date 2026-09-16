#!/usr/bin/env python3
"""
Amazon Photos Video Storage Analyzer & Manager
Finds videos stored in Amazon Photos sorted by size to identify and free up storage space.
"""

import argparse
import json
import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

from amazon_photos import AmazonPhotos


def format_size(bytes_val: float) -> str:
    """Format bytes into a human-readable string (KB, MB, GB, TB)."""
    if pd.isna(bytes_val) or bytes_val is None:
        return "N/A"
    try:
        b = float(bytes_val)
    except (ValueError, TypeError):
        return "N/A"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024.0 or unit == 'TB':
            return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} TB"


def load_cookies(cookies_path: str | None = None) -> tuple[dict, str]:
    """
    Load Amazon session cookies from:
    1. Specified cookies file (--cookies-file)
    2. .env file
    3. cookies.json file
    4. Environment variables
    """
    if cookies_path:
        p = Path(cookies_path)
        if not p.exists():
            print(f"[ERROR] Cookies file not found: {cookies_path}")
            sys.exit(1)
        if p.suffix == '.json':
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data, data.get('tld', 'com')
        load_dotenv(p)

    load_dotenv()

    json_path = Path('cookies.json')
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and ('session-id' in data or 'ubid-main' in data or 'at-main' in data):
                    return data, data.get('tld', 'com')
        except Exception as e:
            print(f"[WARNING] Could not parse cookies.json: {e}")

    session_id = os.getenv('AMAZON_SESSION_ID') or os.getenv('SESSION_ID')
    ubid_main = os.getenv('AMAZON_UBID_MAIN') or os.getenv('UBID_MAIN') or os.getenv('UBID')
    at_main = os.getenv('AMAZON_AT_MAIN') or os.getenv('AT_MAIN') or os.getenv('AT')
    tld = os.getenv('AMAZON_TLD') or 'com'

    if not session_id or not (ubid_main or at_main):
        print("\n[ERROR] Missing Amazon Photos credentials!")
        print("Please configure your cookies using either:")
        print("  1. A `.env` file (copy from `.env.example`)")
        print("  2. A `cookies.json` file")
        print("  3. Pass via --cookies-file path/to/cookies.json")
        print("\nRequired cookies:")
        print("  - session-id")
        print("  - ubid-main (or ubid-acb<country>)")
        print("  - at-main (or at-acb<country>)")
        print("\nSee QUICKSTART.md for detailed instructions on extracting these cookies.\n")
        sys.exit(1)

    cookies = {
        'session-id': session_id,
        'ubid-main': ubid_main,
        'at-main': at_main,
    }
    return cookies, tld


def get_amazon_photos_client(cookies: dict, tld: str = 'com') -> AmazonPhotos:
    """Connect to Amazon Photos with cookie validation and fast-fail error handling."""
    try:
        print("[*] Connecting to Amazon Photos...")
        ap = AmazonPhotos(cookies=cookies, tld=tld, init_db=False, init_folders=False)
        print(f"[+] Connected! Logged in to Amazon Photos (TLD: {ap.tld})")
        return ap
    except PermissionError as e:
        print(f"\n[!] Authentication Error: {e}")
        print("Your cookies may be expired or copied incorrectly. Please log in again to Amazon Photos and copy fresh cookies.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Connection Error: {e}")
        print("Double-check your network connection and cookie values.\n")
        sys.exit(1)


def analyze_videos(ap: AmazonPhotos, min_size_mb: float = 0.0) -> pd.DataFrame:
    """Query all videos from Amazon Photos and format sizes."""
    print("[*] Querying video library from Amazon Photos...")
    df = ap.videos()

    if df is None or df.empty:
        print("[!] No videos found in your Amazon Photos account.")
        return pd.DataFrame()

    print(f"[+] Found {len(df)} total videos.")

    df['size_bytes'] = pd.to_numeric(df['size'], errors='coerce').fillna(0).astype('int64')
    df['size_mb'] = (df['size_bytes'] / (1024 * 1024)).round(2)
    df['size_gb'] = (df['size_bytes'] / (1024 * 1024 * 1024)).round(3)
    df['size_str'] = df['size_bytes'].apply(format_size)

    df = df.sort_values(by='size_bytes', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1

    if min_size_mb > 0:
        initial_len = len(df)
        df = df[df['size_mb'] >= min_size_mb].reset_index(drop=True)
        df['rank'] = df.index + 1
        print(f"[*] Filtered to {len(df)} videos >= {min_size_mb:.1f} MB (omitted {initial_len - len(df)} smaller videos).")

    return df


def display_video_table(df: pd.DataFrame, limit: int = 25):
    """Print a clean summary table of the largest videos."""
    if df.empty:
        return

    total_bytes = df['size_bytes'].sum()
    total_gb = total_bytes / (1024 ** 3)
    avg_mb = (df['size_bytes'].mean() or 0) / (1024 ** 2)

    print("\n" + "=" * 95)
    print(" Amazon Photos Video Storage Summary")
    print("=" * 95)
    print(f" Total Videos:       {len(df):,}")
    print(f" Total Storage Used: {total_gb:.2f} GB ({format_size(total_bytes)})")
    print(f" Average Video Size: {avg_mb:.2f} MB")
    if len(df) > 0:
        print(f" Largest Video:      {df.iloc[0]['size_str']} ('{df.iloc[0].get('name', 'Unknown')}')")
    print("=" * 95)

    display_df = df.head(limit)
    print(f"\nTop {len(display_df)} Largest Videos:")
    print("-" * 95)
    header = f"{'Rank':<5} | {'Size':<10} | {'Date':<12} | {'Resolution':<11} | {'Filename':<32} | {'Node ID'}"
    print(header)
    print("-" * 95)

    for _, row in display_df.iterrows():
        rank = row['rank']
        size_str = row['size_str']
        created = str(row.get('createdDate', ''))[:10]
        vw = row.get('video.width')
        vh = row.get('video.height')
        res = f"{int(vw)}x{int(vh)}" if pd.notna(vw) and pd.notna(vh) else "N/A"
        name = str(row.get('name', 'Unknown'))
        if len(name) > 30:
            name = name[:27] + "..."
        node_id = str(row.get('id', ''))
        print(f"{rank:<5} | {size_str:<10} | {created:<12} | {res:<11} | {name:<32} | {node_id}")

    print("-" * 95)
    if len(df) > limit:
        print(f"... and {len(df) - limit:,} more videos. See exported CSV for full list.")


def export_csv(df: pd.DataFrame, csv_path: str = "amazon_videos_by_size.csv"):
    """Export sorted video list to CSV."""
    if df.empty:
        return

    cols = ['rank', 'name', 'size_str', 'size_mb', 'size_gb', 'size_bytes', 'createdDate', 'id']
    available_cols = [c for c in cols if c in df.columns]
    extra_cols = [c for c in ['contentType', 'extension', 'video.width', 'video.height', 'modifiedDate'] if c in df.columns]
    out_df = df[available_cols + extra_cols]

    out_df.to_csv(csv_path, index=False)
    print(f"\n[+] Full video inventory exported to: {Path(csv_path).resolve()}")


def move_to_trash(ap: AmazonPhotos, node_ids: list[str]):
    """Safely move specified node IDs to Amazon Photos Trash."""
    if not node_ids:
        print("[!] No node IDs provided.")
        return

    print(f"[*] Moving {len(node_ids)} video(s) to Amazon Photos Trash...")
    try:
        ap.trash(node_ids)
        print(f"[+] Successfully moved {len(node_ids)} video(s) to Trash!")
        print("Note: Items in Trash can be restored from the Amazon Photos web app if needed.")
    except Exception as e:
        print(f"[!] Error moving to trash: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="List and sort Amazon Photos videos by size to free up cloud storage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--cookies-file',
        type=str,
        default=None,
        help="Path to cookies JSON or .env file (default: .env or cookies.json)",
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=25,
        help="Number of videos to display in console table (default: 25)",
    )
    parser.add_argument(
        '--min-size-mb',
        type=float,
        default=0.0,
        help="Only include videos larger than this size in MB (e.g. --min-size-mb 100)",
    )
    parser.add_argument(
        '--csv',
        type=str,
        default="amazon_videos_by_size.csv",
        help="Path for output CSV file (default: amazon_videos_by_size.csv)",
    )
    parser.add_argument(
        '--trash',
        nargs='+',
        metavar='NODE_ID',
        help="Move one or more video node IDs to Amazon Photos Trash",
    )
    parser.add_argument(
        '--trash-top',
        type=int,
        metavar='N',
        help="Interactively move top N largest videos to Trash",
    )

    args = parser.parse_args()

    cookies, tld = load_cookies(args.cookies_file)
    ap = get_amazon_photos_client(cookies, tld)

    if args.trash:
        confirm = input(f"Are you sure you want to move {len(args.trash)} item(s) to Trash? [y/N]: ").strip().lower()
        if confirm == 'y':
            move_to_trash(ap, args.trash)
        else:
            print("Cancelled.")
        return

    df = analyze_videos(ap, min_size_mb=args.min_size_mb)
    if df.empty:
        return

    display_video_table(df, limit=args.limit)
    export_csv(df, csv_path=args.csv)

    if args.trash_top and args.trash_top > 0:
        top_n = min(args.trash_top, len(df))
        candidates = df.head(top_n)
        total_freed = candidates['size_bytes'].sum() / (1024 ** 3)
        print(f"\n[!] You requested moving the top {top_n} largest videos to Trash (~{total_freed:.2f} GB to be freed).")
        confirm = input(f"Type 'yes' to confirm moving these {top_n} videos to Trash: ").strip()
        if confirm == 'yes':
            ids = candidates['id'].tolist()
            move_to_trash(ap, ids)
        else:
            print("Cancelled. No files were modified.")


if __name__ == '__main__':
    main()
