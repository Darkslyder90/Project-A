from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.api_usage_log import ApiUsageLog
from app.db.models.model_pricing import ModelPricing


def list_pricing(db: Session) -> list[ModelPricing]:
    return db.query(ModelPricing).order_by(ModelPricing.modell_name, ModelPricing.gueltig_ab.desc()).all()


def create_pricing(
    db: Session,
    *,
    modell_name: str,
    gueltig_ab: date,
    input_preis_pro_million_usd: float,
    output_preis_pro_million_usd: float,
    cache_write_preis_pro_million_usd: float | None,
    cache_read_preis_pro_million_usd: float | None,
) -> ModelPricing:
    pricing = ModelPricing(
        modell_name=modell_name,
        gueltig_ab=gueltig_ab,
        input_preis_pro_million_usd=input_preis_pro_million_usd,
        output_preis_pro_million_usd=output_preis_pro_million_usd,
        cache_write_preis_pro_million_usd=cache_write_preis_pro_million_usd,
        cache_read_preis_pro_million_usd=cache_read_preis_pro_million_usd,
    )
    db.add(pricing)
    db.commit()
    db.refresh(pricing)
    return pricing


def delete_pricing(db: Session, pricing_id: int) -> None:
    pricing = db.get(ModelPricing, pricing_id)
    if pricing is None:
        raise NotFoundError(f"Preis {pricing_id} wurde nicht gefunden.")
    db.delete(pricing)
    db.commit()


def _find_applicable_price(pricing_rows: list[ModelPricing], at: date) -> ModelPricing | None:
    """Neuester Preis, der am Stichtag `at` bereits gueltig war (gueltig_ab <= at) -
    fuer korrekte historische Auswertungen wird IMMER der zum jeweiligen
    Log-Zeitpunkt gueltige Preis verwendet, nie pauschal der aktuellste.
    """
    candidates = [p for p in pricing_rows if p.gueltig_ab <= at]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.gueltig_ab)


def calculate_cost_eur(
    db: Session, logs: list[ApiUsageLog], wechselkurs: float
) -> tuple[float, bool]:
    """Berechnet geschaetzte Kosten in EUR zur Laufzeit aus Tokens + zum
    jeweiligen Zeitpunkt gueltigem Preis (siehe ModelPricing) - es wird
    niemals ein Euro-Betrag dauerhaft gespeichert, nur live berechnet.

    Gibt (kosten_eur, vollstaendig) zurueck: vollstaendig=False, wenn fuer
    mindestens einen Log-Eintrag kein passender Preis gefunden wurde (dessen
    Tokens fliessen dann nicht in die Summe ein) - die Anzeige zeigt dann
    einen "ca."-Hinweis auf eine unvollstaendige Schaetzung.
    """
    if not logs:
        return 0.0, True

    all_pricing = db.query(ModelPricing).all()
    by_model: dict[str, list[ModelPricing]] = {}
    for pricing in all_pricing:
        by_model.setdefault(pricing.modell_name, []).append(pricing)

    total_usd = 0.0
    vollstaendig = True
    for log in logs:
        applicable = _find_applicable_price(by_model.get(log.modell, []), log.erstellt_am.date())
        if applicable is None:
            vollstaendig = False
            continue
        total_usd += (log.input_tokens / 1_000_000) * applicable.input_preis_pro_million_usd
        total_usd += (log.output_tokens / 1_000_000) * applicable.output_preis_pro_million_usd

    return total_usd * wechselkurs, vollstaendig
