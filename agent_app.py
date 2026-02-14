from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


EXCLUDED_SECTORS = {"tekstil", "konut", "toki", "ges", "güneş enerji santrali"}
TRENG_KEYWORDS = {
    "toz",
    "talaş",
    "filtrasyon",
    "kartuş",
    "torba",
    "jet-pulse",
    "baca",
    "kaynak dumanı",
    "boyahane",
    "havalandırma",
    "emisyon",
    "konveyör",
    "zincirli",
    "bantlı",
    "pnömatik",
    "fan",
    "kanallama",
    "hvac",
    "proses",
    "kurutma",
    "kaplama",
    "modernizasyon",
}
IRDA_KEYWORDS = {
    "endüstriyel tesis",
    "çelik konstrüksiyon",
    "prefabrik",
    "kenet çatı",
    "havaalanı",
    "savunma",
    "altyapı",
    "epc",
    "ana yüklenici",
    "çatı",
    "hangar",
}
RELIABILITY_WEIGHTS = {
    "kap": 20,
    "resmi": 18,
    "şirket": 16,
    "sektörel": 12,
    "ulusal": 10,
    "yerel": 8,
    "etkinlik": 6,
    "çed": 14,
}


@dataclass
class Signal:
    company: str
    title: str
    description: str
    source_url: str
    source_type: str
    country: str
    sector: str
    tags: list[str]
    event_date: date

    @property
    def text(self) -> str:
        return f"{self.title} {self.description} {' '.join(self.tags)}".lower()


def parse_signals(raw_signals: Iterable[dict]) -> list[Signal]:
    parsed: list[Signal] = []
    for item in raw_signals:
        parsed.append(
            Signal(
                company=item["company"],
                title=item["title"],
                description=item["description"],
                source_url=item["source_url"],
                source_type=item["source_type"].lower(),
                country=item.get("country", "Türkiye"),
                sector=item.get("sector", "endüstriyel").lower(),
                tags=[t.lower() for t in item.get("tags", [])],
                event_date=datetime.strptime(item["event_date"], "%Y-%m-%d").date(),
            )
        )
    return parsed


def is_excluded(signal: Signal) -> bool:
    blob = f"{signal.sector} {signal.text}"
    return any(word in blob for word in EXCLUDED_SECTORS)


def within_days(signal: Signal, days: int = 120, today: date | None = None) -> bool:
    pivot = today or date.today()
    return signal.event_date >= pivot - timedelta(days=days)


def keyword_score(blob: str, keywords: set[str], weight: int = 8) -> int:
    hits = sum(1 for kw in keywords if kw in blob)
    return min(45, hits * weight)


def reliability_score(source_type: str) -> int:
    return RELIABILITY_WEIGHTS.get(source_type, 6)


def treng_score(signal: Signal) -> int:
    blob = signal.text
    score = keyword_score(blob, TRENG_KEYWORDS)
    score += 15 if "endüstriyel" in signal.sector or "fabrika" in blob else 0
    score += 15 if signal.country.lower() == "türkiye" else 0
    score += 12 if within_days(signal, 60) else 6
    score += reliability_score(signal.source_type)
    return min(100, score)


def irda_score(signal: Signal) -> int:
    blob = signal.text
    score = keyword_score(blob, IRDA_KEYWORDS)
    score += 18 if "havaalanı" in blob or "altyapı" in blob else 0
    score += 14 if "epc" in blob or "ana yüklenici" in blob else 0
    score += 15 if signal.country.lower() == "türkiye" else 0
    score += 12 if within_days(signal, 60) else 6
    score += reliability_score(signal.source_type)
    return min(100, score)


def classify(signals: list[Signal]) -> tuple[list[tuple[Signal, int]], list[tuple[Signal, int]], list[Signal]]:
    treng_candidates: list[tuple[Signal, int]] = []
    irda_candidates: list[tuple[Signal, int]] = []
    watchlist: list[Signal] = []

    for signal in signals:
        if is_excluded(signal) or not within_days(signal, 120):
            continue

        ts = treng_score(signal)
        iscore = irda_score(signal)

        if ts >= 55:
            treng_candidates.append((signal, ts))
        if iscore >= 55:
            irda_candidates.append((signal, iscore))
        if 35 <= max(ts, iscore) < 55:
            watchlist.append(signal)

    treng_candidates.sort(key=lambda x: x[1], reverse=True)
    irda_candidates.sort(key=lambda x: x[1], reverse=True)
    return treng_candidates[:5], irda_candidates[:5], watchlist[:5]


def format_report(treng: list[tuple[Signal, int]], irda: list[tuple[Signal, int]], watchlist: list[Signal]) -> str:
    if not treng and not irda:
        return "Seçilen firmalar için son 120 gün içinde doğrulanmış operasyonel sinyal bulunamadı."

    critical = sorted(treng + irda, key=lambda x: x[1], reverse=True)[:3]

    lines = [
        "🧠 YÖNETİCİ ÖZETİ",
        f"- Bu dönemde Treng için {len(treng)} anlamlı sinyal bulundu.",
        f"- Bu dönemde İrda için {len(irda)} anlamlı sinyal bulundu.",
        "- En kritik 3 gelişme:",
    ]

    for signal, score in critical:
        lines.append(f"  - {signal.company}: {signal.title} (Skor: {score})")

    lines.append("\n🔧 TRENG – ÖNEMLİ BULGULAR")
    for signal, score in treng:
        lines.extend(
            [
                f"- Şirket: {signal.company}",
                f"  - Olay: {signal.title}",
                f"  - TRENG için neden kritik: Teknik uyum skoru {score}/100; {signal.description}",
                f"  - 🔗 {signal.source_url}",
            ]
        )

    lines.append("\n🏗️ İRDA – ÖNEMLİ BULGULAR")
    for signal, score in irda:
        lines.extend(
            [
                f"- Şirket: {signal.company}",
                f"  - Olay: {signal.title}",
                f"  - İRDA için neden kritik: Teknik uyum skoru {score}/100; {signal.description}",
                f"  - 🔗 {signal.source_url}",
            ]
        )

    lines.append("\n👀 TAKİPTE OLANLAR")
    if watchlist:
        for signal in watchlist:
            lines.append(f"- {signal.company}: {signal.title} — 🔗 {signal.source_url}")
    else:
        lines.append("- Takipte anlamlı ancak zayıf kanıtlı sinyal bulunamadı.")

    lines.extend(
        [
            "\n📅 FUAR RADARI (önümüzdeki 90–180 gün)",
            "- WIN EURASIA (İstanbul): Neden Treng? Endüstriyel otomasyon, hava ve filtrasyon çözümü alıcıları yoğun.",
            "- PaintExpo Eurasia: Neden Treng? Boyahane, kurutma ve emisyon kontrolü yatırımcılarına doğrudan erişim.",
            "- SAHA EXPO: Neden İrda? Savunma sanayi altyapı ve hangar yatırımlarında EPC/çelik yapı ilişkileri güçlenir.",
            "- Airport Show Türkiye panelleri: Neden İrda? Havaalanı bakım ve genişleme projeleri için erken sinyal üretir.",
        ]
    )

    return "\n".join(lines)


def run(input_file: Path) -> str:
    payload = json.loads(input_file.read_text(encoding="utf-8"))
    signals = parse_signals(payload["signals"])
    treng, irda, watchlist = classify(signals)
    return format_report(treng, irda, watchlist)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kurumsal Araştırma Ajanı")
    parser.add_argument("input", type=Path, help="JSON input dosyası")
    parser.add_argument("--output", type=Path, help="Raporu markdown dosyasına yaz")
    args = parser.parse_args()

    report = run(args.input)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
