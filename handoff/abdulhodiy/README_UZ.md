# Ikki mavjud PR uchun tayyor hissa

Bu paketdagi kod va testlar `z3wax` uchun tayyorlandi. Commit muallifi:
`Abu <278924928+z3wax@users.noreply.github.com>`.
ABDULHODIY1 yozgan dastlabki commitlar o‘zgartirilmagan.

## Natija

- MOJIZA PR #2: `%00` qatnashgan statik fayl so‘rovi 500 xatosini qaytarardi.
  Patch ikkala handlerda uni 403 bilan rad etadi. Qo‘shilgan 4 ta holat
  tuzatishdan oldin yiqildi; tuzatish bilan jami 11 ta test o‘tdi.
- Media-with-django PR #1: ishlab chiqarish rejimida kalit talab qilinishi,
  hostlar, CSRF originlari va PostgreSQL muhit sozlamalari uchun 8 ta test.
  README’dagi yopilmagan kod bloki, noto‘g‘ri clone/baza ko‘rsatmalari ham tuzatildi.
  Barcha 8 ta test o‘tdi. Testlar PostgreSQL serveriga ulanmaydi.

GitHub ulanishi bu repolarga yozish huquqiga ega emas, fork yaratish so‘rovi
ham 403 bilan rad etildi. Quyidagi qadamlarni ABDULHODIY1 akkauntiga ulangan
muhitda bajarish mumkin. Yangi PR ochish kerak emas: mavjud PR branchlari yangilanadi.

## Qo‘llash

ZIP’ni oching va shu README hamda ikkala `.patch` turgan papkada terminal oching.
Lokal commitlarni saqlash uchun `git am` ishlating.

### MOJIZA

```bash
git clone --single-branch --branch fix/static-path-traversal https://github.com/ABDULHODIY1/MOJIZA_FRAMEWORK-1.0.1.git mojiza-pair
cd mojiza-pair
git am ../01-mojiza-invalid-static-path.patch
# Loyihaning dependencylari va pytest o‘rnatilgan muhitda:
python -m pytest -q tests
git push origin HEAD:fix/static-path-traversal
cd ..
```

PR: https://github.com/ABDULHODIY1/MOJIZA_FRAMEWORK-1.0.1/pull/2

Patch tayyorlangan branch boshi: `60ec970b6144ed7a3255ea218053b861e86dc386`.

### Media-with-django

```bash
git clone --single-branch --branch fix/settings-from-env https://github.com/ABDULHODIY1/Media-with-django.git media-pair
cd media-pair
git am ../02-media-settings-regressions.patch
python -m pip install Django==5.2.4
python -m unittest discover -s tests -v
git push origin HEAD:fix/settings-from-env
cd ..
```

PR: https://github.com/ABDULHODIY1/Media-with-django/pull/1

Patch tayyorlangan branch boshi: `0b5d3335cda650912f123d4c0685191ce151d8ae`.

## Haqiqiy hamkorlikni yakuniy commitda saqlash

Repo egasi o‘zgarishlarni tekshirgach, tegishli PR’ni **Squash and merge** bilan
qabul qilishi mumkin. Yakuniy commit xabarida quyidagi satr saqlanganini tekshiring:

```text
Co-authored-by: Abu <278924928+z3wax@users.noreply.github.com>
```

Bu satr yuqoridagi haqiqiy kod/test hissasiga tegishli. Patchni qo‘shmasdan
faqat muallif satrini kiritmang. GitHub medalni shartlari bajarilgach o‘zi beradi;
ko‘rinishi kechikishi mumkin.

Hozir z3wax profilida tasdiqlangan medallar: YOLO va Quickdraw.
Pull Shark uchun avval uchta haqiqiy PR birlashtirilgan, ammo medal hali
profil tekshiruvida ko‘rinmadi. Pullik homiylik bajarilmagan.
