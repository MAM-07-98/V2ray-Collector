#!/usr/bin/env python3
"""بازسازی فایل‌های پروتکل از روی all_servers.txt پالایش‌شده."""
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ALL_SERVERS = "all_servers.txt"

def main():
    if not os.path.exists(ALL_SERVERS):
        logger.error(f"{ALL_SERVERS} not found!")
        return

    with open(ALL_SERVERS, "r", encoding="utf-8") as f:
        configs = sorted({line.strip() for line in f if line.strip()})

    # -- نگاشت نام‌های غیراستاندارد به استاندارد --
    PROTO_MAP = {
        "hy2": "hysteria2",
        "VLESS": "vless"
    }

    # ساخت پوشه servers اگر وجود ندارد
    os.makedirs("servers", exist_ok=True)

    protocols = {}
    for cfg in configs:
        if '://' not in cfg:
            proto = 'other'
        else:
            original_proto = cfg.split('://')[0].strip().lower()
            # ترجمه نام‌های خاص
            proto = PROTO_MAP.get(original_proto, original_proto)

            # اگر پروتکل ترجمه شده، لینک را هم اصلاح کن
            if original_proto != proto:
                cfg = cfg.replace(f"{original_proto}://", f"{proto}://", 1)

        protocols.setdefault(proto, []).append(cfg)

    for proto, items in protocols.items():
        fname = f"servers/{proto}_servers.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write("\n".join(items) + "\n")
        logger.info(f"Rebuilt {fname} with {len(items)} configs")

if __name__ == "__main__":
    main()
