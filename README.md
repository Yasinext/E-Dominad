# DomainBot

Telegram gruplarında kullanıcı tarafından verilen `.com` domainleri RDAP üzerinden kontrol eden,
sonuçları PostgreSQL'e kaydeden ve talep üzerine raporlayan bot.

## Ilkeler

- Bot yalnızca yetkili Telegram gruplarında çalışır.
- Yalnızca `.com` kabul edilir.
- Kullanıcı girdisi dışında domain, kök veya aralık üretilmez.
- RDAP sonucu "satın alınabilir" anlamına gelmez; ilk sürümde kullanıcıya
  "Registry kaydı bulunamadı" denir.
- Telegram handler uzun RDAP işi yapmaz; işi veritabanına yazar.
- Worker geçici hatalarda doğrulanmış domain durumunu değiştirmez.
- BTK kontrolü ayrı worker tarafından DB havuzundaki domainler için arka planda tamamlanır.

## Geliştirme

Hedef Python sürümü 3.12'dir.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

Çalışan süreçler:

```bash
python -m domainbot.main_bot
python -m domainbot.main_worker
python -m domainbot.main_scheduler
python -m domainbot.main_btk_worker
```

## Lokal PostgreSQL

macOS üzerinde Homebrew PostgreSQL 16 ile lokal test:

```bash
brew install postgresql@16
/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D /opt/homebrew/var/postgresql@16 -l /tmp/domainbot-postgres.log start
/opt/homebrew/opt/postgresql@16/bin/createuser domainbot
/opt/homebrew/opt/postgresql@16/bin/createdb -O domainbot domainbot
alembic -c alembic.ini upgrade head
python scripts/local_smoke.py
```

Lokal `.env` için bağlantı:

```dotenv
DATABASE_URL=postgresql+asyncpg://domainbot@127.0.0.1:5432/domainbot
```

## Komutlar

```text
/sorgu <domain.com>
/sorgu <kok> <baslangic>-<bitis>
/rapor <kok> <baslangic>-<bitis> [kayitli|kayitsiz|belirsiz] [excel]
/rapor_genel [excel]
/takip <domain.com> <gunluk|haftalik>
/takip <kok> <baslangic>-<bitis> <gunluk|haftalik>
/takipler
/takip_durdur <domain.com>
/takip_durdur <kok> <baslangic>-<bitis>
/havuz_domain_guncelle
/havuz_btk_guncelle
```
