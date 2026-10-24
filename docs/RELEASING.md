# Support Bot — Reliz tartibi

[README](../README.md) · [Changelog](../CHANGELOG.md)

## Joriy relizlar

Hozircha GitHub Releases ro‘yxatida e’lon qilingan reliz topilmadi. Paket manifestidagi versiya avtomatik ravishda GitHub relizi degani emas.

Bu hujjat yangi tag, release yoki model checkpointini avtomatik e’lon qilmaydi.

## Yangi reliz tayyorlash

1. Relizga kiradigan commitni va uning ko‘lamini tanlang.
2. [Baholash protokoli](EVALUATION.md) bo‘yicha zarur tekshiruvlarni bajaring.
3. `CHANGELOG.md` dagi Unreleased yozuvlarini haqiqiy versiya va sana bilan ajrating.
4. Moslikka ta’sir qilsa breaking change va migratsiya yo‘lini yozing.
5. GitHub Release yaratishda tag va tekshirilgan commitni bir-biriga bog‘lang.
6. Faqat tekshirilgan artefaktlarni ilova qiling; model/binar uchun SHA-256 va muhitni ko‘rsating.

## Versiya tanlash

Ishlaydigan dastur uchun `MAJOR.MINOR.PATCH` tartibi qo‘llanishi mumkin: moslik buzilishi, yangi imkoniyat va tuzatish. Eksperimental bosqichni pre-release sifatida belgilang. Arxiv yoki o‘quv materialiga dasturiy versiya ma’nosini majburan yuklamang.

## Reliz tavsifi

- Muammo va foydalanuvchiga ko‘rinadigan natija.
- Qo‘shilgan, tuzatilgan va o‘zgargan qismlar.
- O‘rnatish / yangilash yo‘li.
- Bajarilgan tekshiruvlar va muhim cheklovlar.
- Litsenziya va tegishli upstream bildirishnomalari.
