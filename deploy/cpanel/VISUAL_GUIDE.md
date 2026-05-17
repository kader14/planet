# دليل النشر المرئي على cPanel — Planet Python

دليل خطوة بخطوة مع رسوم توضيحية لكل شاشة في cPanel.

> **اختصار:** لو تستطيع استخدام SSH، السكربت `setup.sh` يقوم بكل شيء بأمر واحد.
> هذا الدليل لمن يفضّل الواجهة المرئية.

---

## الخطوة 0 — الدخول إلى cPanel

افتح في المتصفح أحد هذه الروابط (شركة الاستضافة تخبرك بالعنوان الصحيح):

```
https://yourdomain.com:2083
https://yourdomain.com/cpanel
https://server.host.com:2083
```

شاشة الدخول:

```
+---------------------------------------------+
|              cPanel                         |
|  +---------------------------------------+  |
|  |  Username: [____________________]     |  |
|  |  Password: [____________________]     |  |
|  |              [   Log in   ]           |  |
|  +---------------------------------------+  |
+---------------------------------------------+
```

---

## الخطوة 1 — رفع المشروع إلى الخادم

### الطريقة (أ) — Git Version Control (الأفضل)

في cPanel ابحث عن **Git Version Control**:

```
[Files]
  File Manager   Images   Directory Privacy   Disk Usage
  Web Disk       FTP Accounts                FTP Connections
  Backup         Backup Wizard               Git Version Control  <-- هنا
```

اضغط عليها، ثم **Create**:

```
+--------------------------------------------------------+
|  Create a Repository                                   |
+--------------------------------------------------------+
|  [x] Clone a repository                                |
|                                                        |
|  Clone URL:    [https://github.com/kader14/planet.git] |
|  Repository Path: [/home/USERNAME/planet            ]  |
|  Repository Name: [planet                           ]  |
|                                                        |
|                            [   Create   ]              |
+--------------------------------------------------------+
```

### الطريقة (ب) — File Manager

1. افتح **File Manager**.
2. تأكد أنك في مجلد `home/USERNAME/`.
3. اضغط **Upload** ← ارفع ملف ZIP للمشروع.
4. عُد إلى File Manager، اضغط يمين على الملف ← **Extract**.
5. أعِد تسمية المجلد إلى `planet`.

النتيجة المتوقعة:

```
/home/USERNAME/
  planet/
    code/
    config/
    deploy/cpanel/
    static/
    requirements.txt
```

---

## الخطوة 2 — إنشاء بيئة Python

ابحث عن **Setup Python App**:

```
[Software]
  Setup Python App      <-- هنا
  Setup Node.js App
  Optimize Website
  MultiPHP Manager
  PHP PEAR Packages
```

ثم اضغط **Create Application**:

```
+--------------------------------------------------------+
|  Setup Python App                                      |
+--------------------------------------------------------+
|  Python version           [ 3.11.x          v ]        |
|                                                        |
|  Application root         [ planet                 ]   |
|  Application URL          [                        ]   |
|                              ^^^ اتركه فارغاً!         |
|                                                        |
|  Application startup file [                        ]   |
|  Application Entry point  [                        ]   |
|                              ^^^ اتركهما فارغين!       |
|                                                        |
|  Passenger log file       [                        ]   |
|                                                        |
|                            [    Create     ]           |
+--------------------------------------------------------+
```

> **مهم جداً:** اترك "Application URL" و "Startup file" **فارغة**.
> نحن لا نريد cPanel أن يدير تطبيق ويب — فقط نريد بيئة Python.

بعد الإنشاء ستظهر معلومات البيئة:

```
+--------------------------------------------------------+
|  Web Application                                       |
+--------------------------------------------------------+
|  Status: STOPPED  ✓  (هذا ما نريده)                    |
|                                                        |
|  Virtual Environment:                                  |
|    /home/USERNAME/virtualenv/planet/3.11/              |
|                                                        |
|  Enter virtualenv command:                             |
|    source /home/USERNAME/virtualenv/planet/3.11/...    |
|                              [Copy]                    |
|                                                        |
|  Configuration files                                   |
|    Configuration file:  [requirements.txt        v ]   |
|              [   Run Pip Install   ]                   |
+--------------------------------------------------------+
```

اضغط **Run Pip Install**. سيتم تثبيت كل المكتبات تلقائياً.

> سجّل عندك مسار الـ virtualenv (السطر تحت "Virtual Environment").

---

## الخطوة 3 — تعديل `config.ini`

ابحث عن **File Manager**:

```
[Files]
  File Manager     <-- هنا
  Images
  Directory Privacy
```

انتقل إلى المسار: `home/USERNAME/planet/config/`

```
+--------------------------------------------------------+
|  File Manager   /home/USERNAME/planet/config           |
+--------------------------------------------------------+
|  Name              Size      Type                      |
|  ----              ----      ----                      |
|  config.ini        12 KB     ini  <-- اختر هذا         |
|  index.html.tmpl    8 KB     tmpl                      |
|  rss20.xml.tmpl     2 KB     tmpl                      |
|  ...                                                   |
+--------------------------------------------------------+
```

اضغط **يمين** على `config.ini` ← **Edit** ← **Edit** (تأكيد).

في الأعلى مباشرة بعد سطر `[Planet]` ابحث عن السطرين وعدّلهما:

```ini
[Planet]
name              = Planet Python
link              = https://planetpython.org/

# هذا هو السطر الأهم
output_dir        = /home/USERNAME/public_html
cache_directory   = /home/USERNAME/planet/cache

# باقي الإعدادات كما هي
template_files    = config/index.html.tmpl ...
```

> **بدّل `USERNAME`** باسم حسابك الفعلي.
> تعرفه من زاوية cPanel أعلى يمين الشاشة (تحت "User").

اضغط **Save Changes** أعلى يمين المحرر.

---

## الخطوة 4 — إنشاء مجلدَي `cache` و `logs`

ما زلنا في File Manager، انتقل إلى `home/USERNAME/planet/`:

```
+--------------------------------------------------------+
|  File Manager   /home/USERNAME/planet                  |
+--------------------------------------------------------+
|  [+ File]  [+ Folder]  [Copy]  [Move]  [Upload]        |
|                                                        |
|  Name              Size      Type                      |
|  ----              ----      ----                      |
|  code/                       Folder                    |
|  config/                     Folder                    |
|  deploy/                     Folder                    |
|  static/                     Folder                    |
+--------------------------------------------------------+
```

اضغط **+ Folder** ← اسم: `cache` ← Create.
اضغط **+ Folder** مرة أخرى ← اسم: `logs` ← Create.

---

## الخطوة 5 — اختبار يدوي (اختياري لكن موصى به)

من cPanel ← **Terminal** (لو متاح):

```
+--------------------------------------------------------+
|  Terminal                                              |
+--------------------------------------------------------+
|  USERNAME@server [~]$  cd ~/planet                     |
|  USERNAME@server [~/planet]$                           |
|    chmod +x deploy/cpanel/run-planet.sh                |
|                                                        |
|  USERNAME@server [~/planet]$                           |
|    ./deploy/cpanel/run-planet.sh                       |
|                                                        |
|  USERNAME@server [~/planet]$  ls ~/public_html         |
|    atom.xml   images/   index.html   rss10.xml         |
|    rss20.xml  styles/   opml.xml                       |
+--------------------------------------------------------+
```

✓ ظهور `index.html` يعني أن النشر اشتغل!

---

## الخطوة 6 — جدولة Cron Job

في الصفحة الرئيسية لـ cPanel ابحث عن **Cron Jobs**:

```
[Advanced]
  Indexes        Error Pages        Apache Handlers
  Cron Jobs      <-- هنا
  Track DNS      MIME Types
```

ستظهر صفحة Cron Jobs، انزل إلى قسم **Add New Cron Job**:

```
+--------------------------------------------------------+
|  Add New Cron Job                                      |
+--------------------------------------------------------+
|                                                        |
|  Common Settings:                                      |
|  [ Twice an hour (*/30 * * * *)              v ]       |
|                                                        |
|  Minute:   [*/30                              ]        |
|  Hour:     [*                                 ]        |
|  Day:      [*                                 ]        |
|  Month:    [*                                 ]        |
|  Weekday:  [*                                 ]        |
|                                                        |
|  Command:                                              |
|  [/home/USERNAME/planet/deploy/cpanel/run-planet.sh]   |
|                                                        |
|                       [   Add New Cron Job   ]         |
+--------------------------------------------------------+
```

> **لا تنسَ:** استبدل `USERNAME` باسم حسابك في حقل Command.

اضغط **Add New Cron Job**. سترى الجدولة الجديدة في القائمة:

```
+--------------------------------------------------------+
|  Current Cron Jobs                                     |
+--------------------------------------------------------+
|  Min  Hr  Day  Mon  Wkd  Command           Actions     |
|  --   --  ---  ---  ---  -------           -------     |
|  */30 *   *    *    *    /home/.../run...  Edit Delete |
+--------------------------------------------------------+
```

✅ تم! الموقع سيتحدّث كل ٣٠ دقيقة تلقائياً.

---

## الخطوة 7 — التحقق بعد ٣٠ دقيقة

بعد نصف ساعة، افتح موقعك:

```
https://yourdomain.com/
```

يجب أن ترى صفحة Planet Python مع آخر التدوينات من المدوّنات المُشتركة.

للتحقق من السجلّ (logs):

في File Manager: `home/USERNAME/planet/logs/planet.log` ← **View**

شكل السجل المتوقع:

```
[2026-05-17T14:30:01Z] Running planet.py (output -> /home/USERNAME/public_html)
[2026-05-17T14:30:23Z] planet.py finished OK
[2026-05-17T14:30:24Z] Static assets synced into /home/USERNAME/public_html
[2026-05-17T14:30:24Z] Done.
[2026-05-17T15:00:01Z] Running planet.py (output -> /home/USERNAME/public_html)
...
```

---

## استكشاف الأخطاء

| المشكلة | الحل |
|---|---|
| ❌ `ensurepip` returned non-zero exit status 1 | راجع القسم أدناه — `ensurepip` معطّل في Python 3.9 |
| ❌ `Cron Jobs` غير موجود في cPanel | اطلب من شركة الاستضافة تفعيلها |
| ❌ `Setup Python App` غير موجود | الاستضافة لا تدعم Python — تحتاج CloudLinux/LiteSpeed |
| ❌ السجل يقول `ModuleNotFoundError` | الـ venv غير مفعّل — تأكد من مسار `PLANET_VENV` |
| ❌ HTML يظهر لكن بدون تنسيق | مجلدات `styles/` و `images/` لم تُنسخ — شغّل run-planet.sh يدوياً |
| ❌ `Permission denied` | استبدلت `USERNAME` خطأ، أو `output_dir` يشير لمجلد ليس ملكك |
| ❌ صفحة بيضاء على الموقع | لم يتم تشغيل cron بعد — انتظر ٣٠ دقيقة أو شغّله يدوياً |
| ❌ خلاصات RSS لا تتحدّث | تحقق من `cache_directory` (يجب أن يكون قابلاً للكتابة) |

### مشكلة `ensurepip` فشل في إنشاء venv

الخطأ الكامل عادة:

```
Error: Command '['/home/USER/virtualenv/planet/3.9/bin/python3.9',
'-Im', 'ensurepip', '--upgrade', '--default-pip']' returned non-zero exit status 1.
```

**السبب:** بعض شركات الاستضافة (خاصة CloudLinux) تُعطّل وحدة `ensurepip`
في Python 3.9 لتقليل المساحة. النسخة المُحدّثة من `setup.sh` تتعامل مع هذا
تلقائياً عبر ٣ استراتيجيات احتياطية:

1. `python -m venv` (الأصلية).
2. `python -m venv --without-pip` ثم تنزيل `get-pip.py` يدوياً.
3. تثبيت حزمة `virtualenv` كحل أخير.

**لو ما زال يفشل**، استخدم Python 3.10 أو أحدث:

```bash
# اعرض إصدارات Python المتاحة على الخادم
ls /opt/alt/ | grep python

# مثال: استخدم 3.11 صراحةً
bash ~/planet/deploy/cpanel/setup.sh --python /opt/alt/python311/bin/python3.11
```

**أو استخدم Setup Python App في cPanel** لإنشاء الـ venv (يتجاوز قيود
`ensurepip`)، ثم أعد تشغيل السكربت بـ `--skip-run` ليعيد استخدام الـ venv:

```bash
bash ~/planet/deploy/cpanel/setup.sh --skip-run
```

---

## أوامر مفيدة (من Terminal)

```bash
# تشغيل يدوي فوري
~/planet/deploy/cpanel/run-planet.sh

# مشاهدة السجل لحظياً
tail -f ~/planet/logs/planet.log

# ماذا يوجد في public_html؟
ls -la ~/public_html/

# تحديث الكود من GitHub
cd ~/planet && git pull

# إعادة التنصيب من الصفر
bash ~/planet/deploy/cpanel/setup.sh

# اختبار بدون تشغيل (فقط تجهيز)
bash ~/planet/deploy/cpanel/setup.sh --skip-run

# تثبيت في مكان مختلف (نطاق فرعي مثلاً)
bash ~/planet/deploy/cpanel/setup.sh \
    --output-dir /home/USERNAME/planet.example.com
```
