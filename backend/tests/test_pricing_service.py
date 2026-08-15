from datetime import date, datetime

from app.db.models.api_usage_log import ApiUsageLog
from app.db.models.enums import ApiUsagePurpose
from app.db.models.model_pricing import ModelPricing
from app.services.pricing_service import calculate_cost_eur


def _make_log(modell: str, input_tokens: int, output_tokens: int, erstellt_am: datetime) -> ApiUsageLog:
    log = ApiUsageLog(
        zweck=ApiUsagePurpose.CHAT,
        modell=modell,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        dauer_ms=100,
        erfolg=True,
    )
    log.erstellt_am = erstellt_am  # ueberschreibt server_default fuer den Test
    return log


def test_calculate_cost_eur_with_no_pricing_is_zero_and_incomplete(app):
    with app.state.session_factory() as db:
        logs = [_make_log("claude-opus-5", 1_000_000, 0, datetime(2026, 8, 14))]
        kosten, vollstaendig = calculate_cost_eur(db, logs, wechselkurs=1.0)
    assert kosten == 0.0
    assert vollstaendig is False


def test_calculate_cost_eur_computes_correct_amount(app):
    with app.state.session_factory() as db:
        db.add(
            ModelPricing(
                modell_name="claude-opus-5",
                gueltig_ab=date(2026, 1, 1),
                input_preis_pro_million_usd=5.0,
                output_preis_pro_million_usd=25.0,
            )
        )
        db.commit()

        logs = [_make_log("claude-opus-5", 1_000_000, 1_000_000, datetime(2026, 8, 14))]
        # 1M Input * 5 USD + 1M Output * 25 USD = 30 USD, Wechselkurs 0.5 -> 15 EUR
        kosten, vollstaendig = calculate_cost_eur(db, logs, wechselkurs=0.5)

    assert vollstaendig is True
    assert kosten == 15.0


def test_calculate_cost_eur_uses_price_valid_at_log_timestamp(app):
    """Kernanforderung: historische Auswertungen bleiben korrekt, auch wenn
    sich Preise spaeter aendern - der zum jeweiligen Log-Zeitpunkt gueltige
    Preis wird verwendet, nicht pauschal der aktuellste.
    """
    with app.state.session_factory() as db:
        db.add_all(
            [
                ModelPricing(
                    modell_name="claude-sonnet-5",
                    gueltig_ab=date(2026, 1, 1),
                    input_preis_pro_million_usd=2.0,
                    output_preis_pro_million_usd=10.0,
                ),
                ModelPricing(
                    modell_name="claude-sonnet-5",
                    gueltig_ab=date(2026, 9, 1),
                    input_preis_pro_million_usd=3.0,
                    output_preis_pro_million_usd=15.0,
                ),
            ]
        )
        db.commit()

        # Log VOR der Preisaenderung -> alter Preis (2.0/10.0) muss gelten.
        old_log = [_make_log("claude-sonnet-5", 1_000_000, 0, datetime(2026, 8, 15))]
        kosten_alt, vollstaendig_alt = calculate_cost_eur(db, old_log, wechselkurs=1.0)

        # Log NACH der Preisaenderung -> neuer Preis (3.0/10.0->15.0) muss gelten.
        new_log = [_make_log("claude-sonnet-5", 1_000_000, 0, datetime(2026, 9, 15))]
        kosten_neu, vollstaendig_neu = calculate_cost_eur(db, new_log, wechselkurs=1.0)

    assert vollstaendig_alt is True
    assert kosten_alt == 2.0
    assert vollstaendig_neu is True
    assert kosten_neu == 3.0


def test_calculate_cost_eur_with_mixed_known_and_unknown_models_is_incomplete(app):
    with app.state.session_factory() as db:
        db.add(
            ModelPricing(
                modell_name="claude-opus-5",
                gueltig_ab=date(2026, 1, 1),
                input_preis_pro_million_usd=5.0,
                output_preis_pro_million_usd=25.0,
            )
        )
        db.commit()

        logs = [
            _make_log("claude-opus-5", 1_000_000, 0, datetime(2026, 8, 14)),
            _make_log("ein-unbekanntes-modell", 1_000_000, 0, datetime(2026, 8, 14)),
        ]
        kosten, vollstaendig = calculate_cost_eur(db, logs, wechselkurs=1.0)

    assert vollstaendig is False
    assert kosten == 5.0  # nur der bepreiste Anteil zaehlt


def test_calculate_cost_eur_with_empty_logs_is_zero_and_complete(app):
    with app.state.session_factory() as db:
        kosten, vollstaendig = calculate_cost_eur(db, [], wechselkurs=1.0)
    assert kosten == 0.0
    assert vollstaendig is True
