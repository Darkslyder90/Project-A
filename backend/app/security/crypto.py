from cryptography.fernet import Fernet, InvalidToken


class EncryptionUnavailableError(Exception):
    """SETTINGS_ENCRYPTION_KEY fehlt (siehe Briefing: bleibt bewusst ausserhalb
    der DB, App startet trotzdem - nur Ver-/Entschluesselung eines Keys
    schlaegt dann verstaendlich fehl statt eines unklaren Absturzes).
    """


def encrypt(plaintext: str, secret: str | None) -> str:
    if not secret:
        raise EncryptionUnavailableError(
            "SETTINGS_ENCRYPTION_KEY ist nicht konfiguriert - ein Claude-API-Key "
            "kann ohne dieses Secret nicht sicher gespeichert werden."
        )
    return Fernet(secret.encode("utf-8")).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str, secret: str | None) -> str | None:
    """Gibt None zurueck, wenn nicht entschluesselt werden kann (fehlendes/
    falsches Secret) - Aufrufer behandeln das als "gespeicherter Key kann
    nicht entschluesselt werden", nicht als Absturz (siehe Briefing).
    """
    if not secret:
        return None
    try:
        return Fernet(secret.encode("utf-8")).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None
