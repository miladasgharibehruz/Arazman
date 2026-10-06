# Arazman

Windows 11 inventory and multi-channel price monitor.

## Release
Current source version: **2.6**. Create release tag `v2.6` on `main`. GitHub Actions builds the Windows installer and publishes it with a SHA-256 checksum. The version in the application follows the release tag. Next versions: v1.2 through v1.9, then v2.0.

Updates use this repository’s public GitHub Releases. User data and backups live separately in `%LOCALAPPDATA%/ArazmanPriceMonitor`.

## Local development
Run `run.bat` or install `requirements.txt` and run `price_monitor.py`.

## Shared inventory
Mother products own color/size stock. Pack listings share it. Purchases, sales and inventory corrections use a validated transactional ledger. Per-sale cost and fee snapshots preserve historical profits.

Version 2.6 performs the explicitly requested one-time business-data reset after a full backup. Future runs preserve the new inventory. See `UPDATE_NOTES_FA.txt`.

Run engine checks with `python -m unittest discover -s tests`.
