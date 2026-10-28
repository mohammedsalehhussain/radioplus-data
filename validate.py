#!/usr/bin/env python3
"""
يتحقق من ملف قائمة القنوات قبل وصوله لمستخدمي «بث بلس العربي».
يعمل تلقائيًا على GitHub مع كل تعديل، ويمكن تشغيله محليًا:

    python3 validate.py                          # يفحص الملف وحده
    python3 validate.py --previous old.json      # ويقارنه بالنسخة السابقة

القواعد نفسها التي يطبقها التطبيق (CatalogUpdatePolicy) وأكثر، حتى يُكتشف الخطأ هنا لا على جوالات المستخدمين.
"""
import argparse, json, sys
from pathlib import Path

FILE = Path(__file__).resolve().parent / "official_tv_channels.json"
MIN_CHANNELS = 20
BLOCKED = {"almasirah", "almasirahmubasher", "alsahat", "المسيرة", "الساحات"}


def fail(errors):
    print("✗ الملف غير صالح:\n" + "\n".join(f"  - {e}" for e in errors))
    sys.exit(1)


def check(d, previous=None):
    errors, warnings = [], []
    if not isinstance(d.get("version"), int):
        errors.append("الحقل version يجب أن يكون رقمًا صحيحًا")
    url = d.get("updateUrl")
    if url and not str(url).startswith("https://"):
        errors.append("updateUrl يجب أن يبدأ بـ https://")
    channels = d.get("channels")
    if not isinstance(channels, list):
        fail(errors + ["الحقل channels يجب أن يكون قائمة"])
    if len(channels) < MIN_CHANNELS:
        errors.append(f"عدد القنوات {len(channels)} أقل من {MIN_CHANNELS}؛ سيرفض التطبيق الملف")
    seen = set()
    for i, c in enumerate(channels, 1):
        cid, name = c.get("id"), c.get("name")
        where = f"القناة رقم {i} ({cid or name or '?'})"
        if not cid or not name:
            errors.append(f"{where}: id و name مطلوبان")
        if cid in seen:
            errors.append(f"{where}: المعرّف {cid} مكرر")
        seen.add(cid)
        streams = c.get("streams") or []
        if not streams and not c.get("youtubeChannelId") and not c.get("watchUrl"):
            errors.append(f"{where}: لا روابط بث ولا youtubeChannelId")
        for u in streams:
            u = str(u)
            if u.startswith("http://"):
                # مسموح في التطبيق (بعض القنوات لا توفر HTTPS)، ويستطيع المستخدم منعه من الإعدادات
                warnings.append(f"{where}: رابط غير مشفر (HTTP): {u}")
            elif not u.startswith("https://"):
                errors.append(f"{where}: رابط غير صالح: {u}")
        key = (str(cid or "").split(".")[0] + " " + str(name or "")).lower().replace(" ", "")
        if any(b in key for b in BLOCKED):
            errors.append(f"{where}: قناة محظورة في التطبيق")
    if previous is not None:
        pv, pc = previous.get("version", 0), len(previous.get("channels", []))
        if json.dumps(previous.get("channels"), sort_keys=True) != json.dumps(channels, sort_keys=True):
            if d.get("version", 0) <= pv:
                errors.append(f"غيّرت القنوات لكن version ما زال {d.get('version')}؛ ارفعه إلى {pv + 1} وإلا لن يصل التحديث للمستخدمين")
        if len(channels) * 2 < pc:
            errors.append(f"حُذف أكثر من نصف القنوات ({pc} ← {len(channels)})؛ سيرفض التطبيق الملف")
    for w in warnings:
        print(f"! تنبيه: {w}")
    if errors:
        fail(errors)
    print(f"✓ الملف صالح: الإصدار {d['version']}، {len(channels)} قناة")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--previous", help="النسخة السابقة للمقارنة")
    a = p.parse_args()
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail([f"صيغة JSON خاطئة في السطر {e.lineno}، العمود {e.colno}: {e.msg} (غالبًا فاصلة ناقصة أو زائدة)"])
    prev = None
    if a.previous and Path(a.previous).exists() and Path(a.previous).stat().st_size > 0:
        try:
            prev = json.loads(Path(a.previous).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = None
    check(d, prev)


if __name__ == "__main__":
    main()
