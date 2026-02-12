#!/usr/bin/env python3
"""
Check if model files are Git LFS pointers or actual binaries.
This script runs at startup to diagnose LFS issues on Railway.
"""
import os
import sys
from pathlib import Path

def is_lfs_pointer(file_path):
    """Check if a file is a Git LFS pointer (text file < 1KB)."""
    try:
        size = os.path.getsize(file_path)
        if size < 1024:  # Less than 1KB
            # Check if it contains LFS pointer markers
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read(200)
                return 'version https://git-lfs.github.com' in content
        return False
    except Exception:
        return False

def check_model_files():
    """Check if model files are LFS pointers and warn if so."""
    model_files = [
        'models/football_models.joblib',
        'models/basketball/basketball_advanced_models.joblib',
        'models/basketball/basketball_backtested_models.joblib',
        'models/tennis/tennis_advanced_models.joblib',
        'models/tennis/tennis_backtested_models.joblib',
    ]

    lfs_pointers_found = []

    print("[LFS CHECK] Verifying model files are actual binaries, not LFS pointers...\n")

    for model_file in model_files:
        if os.path.exists(model_file):
            if is_lfs_pointer(model_file):
                size = os.path.getsize(model_file)
                print(f"❌ [LFS POINTER] {model_file} ({size} bytes)")
                lfs_pointers_found.append(model_file)

                # Show pointer content
                with open(model_file, 'r') as f:
                    content = f.read(300)
                    print(f"   Content preview:\n   {content[:200]}...\n")
            else:
                size_mb = os.path.getsize(model_file) / 1024 / 1024
                print(f"✅ [ACTUAL FILE] {model_file} ({size_mb:.2f} MB)")
        else:
            print(f"⚠️  [MISSING] {model_file} does not exist!")

    if lfs_pointers_found:
        print("\n" + "="*80)
        print("❌ ERROR: Git LFS files were not pulled by Railway!")
        print("   Railway downloaded LFS pointer files instead of actual model binaries.")
        print("="*80)
        print("\n📋 LFS POINTERS FOUND:")
        for f in lfs_pointers_found:
            print(f"   - {f}")
        print("\n💡 SOLUTIONS:")
        print("   1. Check Railway project settings → Enable Git LFS")
        print("   2. Verify GitHub repo has Railway deploy key with LFS access")
        print("   3. Try using Railway CLI: railway up (uploads files directly)")
        print("   4. Alternative: Upload models to Railway volumes manually")
        print("="*80)
        return False

    print("\n✅ [SUCCESS] All model files are actual binaries (not LFS pointers)")
    return True

if __name__ == '__main__':
    # Run from project root
    if os.path.exists('app'):
        os.chdir('..')

    success = check_model_files()
    sys.exit(0 if success else 1)
