from datetime import date

from agent_app import Signal, classify, irda_score, is_excluded, treng_score, within_days


def test_excluded_sector():
    signal = Signal(
        company="A",
        title="Tekstil yatırım",
        description="",
        source_url="https://example.com",
        source_type="yerel",
        country="Türkiye",
        sector="tekstil",
        tags=[],
        event_date=date.today(),
    )
    assert is_excluded(signal)


def test_treng_and_irda_scores_positive():
    signal = Signal(
        company="B",
        title="Boya hattı, filtrasyon ve havaalanı hangar yapısı",
        description="EPC ana yüklenici ile çelik konstrüksiyon planı.",
        source_url="https://example.com",
        source_type="resmi",
        country="Türkiye",
        sector="endüstriyel tesis",
        tags=["boyahane", "filtrasyon", "havaalanı", "epc"],
        event_date=date.today(),
    )
    assert treng_score(signal) >= 55
    assert irda_score(signal) >= 55


def test_classify_respects_120_days_window():
    old_signal = Signal(
        company="C",
        title="Eski tesis haberi",
        description="Filtrasyon güncellemesi.",
        source_url="https://example.com",
        source_type="resmi",
        country="Türkiye",
        sector="endüstriyel tesis",
        tags=["filtrasyon"],
        event_date=date(2024, 1, 1),
    )
    assert not within_days(old_signal, 120)
    treng, irda, watchlist = classify([old_signal])
    assert treng == []
    assert irda == []
    assert watchlist == []
