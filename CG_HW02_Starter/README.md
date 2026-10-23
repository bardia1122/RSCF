# تمرین ۲ گرافیک کامپیوتری: Rasterization, Symmetry, Clipping, and Filling

فقط فایل `rasterize.py` را کامل کنید. بقیه‌ی فایل‌ها را تغییر ندهید.

```
pip install numpy pillow pygame

python screensaver.py                 # پنجره‌ی زنده (W: لبه‌ی سیمی، Space: توقف، ← →: گام به گام)
python selfcheck.py                   # آزمون خودکار؛ تصویر تفاوت‌ها در selfcheck_out/
python selfcheck.py clip fill -v      # فقط بخش‌های نام‌برده، با جزئیات
python selfcheck.py aa                # آزمون بخش امتیازی
python screensaver.py --export        # frame_noaa.png (و frame_aa.png اگر بخش امتیازی را نوشته‌اید)
python screensaver.py --export --t 8.2 --crop 560 120 64 48    # crop_compare.png برای گزارش
python screensaver.py --bench         # بخش امتیازی: جدول زمان و خطا برای k از ۱ تا ۱۶
```

| فایل | نقش |
|---|---|
| `rasterize.py` | **فایل شما**؛ پنج تابع `make_star_vertices`، `draw_line_bresenham`، `clip_line_cohen_sutherland`، `fill_polygon_scanline` و (امتیازی) `fill_polygon_aa` با قرارداد کامل در docstring |
| `support.py` | `put_pixel`، `fill_span`، `polygon_bbox`، `get_region`، `block_mean` و بارگذاری و ذخیره‌ی تصویر؛ قرارداد مختصات در ابتدای این فایل است |
| `scene.py` | صحنه (قاب، پنجره و ستاره)؛ تابع `render_frame(t, ...)`. برش هر لبه‌ی ستاره، گرد کردن و رسم آن با Bresenham اینجا انجام می‌شود |
| `screensaver.py` | پنجره‌ی زنده، خروجی گرفتن و بنچمارک |
| `selfcheck.py` و `golden/` | آزمون خودکار و داده‌ی آن |

هر تابعی که هنوز ننوشته‌اید با پیام `not implemented yet` اعلام می‌شود و بقیه‌ی صحنه کار می‌کند.
