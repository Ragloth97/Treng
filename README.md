# Kurumsal Araştırma Ajanı (TRENG / İRDA)

Bu uygulama, verilen sinyalleri 120 günlük pencereye göre tarar, kapsam dışı alanları filtreler ve TRENG ile İRDA için ayrı skor hesaplayıp istenen rapor formatında çıktı üretir.

## Özellikler
- Son 120 gün filtresi
- Kapsam dışı sektör filtresi (tekstil, konut/TOKİ, GES)
- TRENG ve İRDA için 0–100 skor
- Yönetici özeti + önemli bulgular + takip listesi + fuar radarı

## Kullanım
```bash
python3 agent_app.py sample_signals.json --output rapor.md
```

veya doğrudan terminalde:

```bash
python3 agent_app.py sample_signals.json
```

## Girdi Formatı
JSON dosyasında `signals` anahtarı altında dizi beklenir:

```json
{
  "signals": [
    {
      "company": "Şirket adı",
      "title": "Olay başlığı",
      "description": "Açıklama",
      "source_url": "https://...",
      "source_type": "resmi|kap|şirket|sektörel|ulusal|yerel|etkinlik|çed",
      "country": "Türkiye",
      "sector": "endüstriyel tesis",
      "tags": ["filtrasyon", "boyahane"],
      "event_date": "YYYY-MM-DD"
    }
  ]
}
```

## Test
```bash
python3 -m pytest -q
```
