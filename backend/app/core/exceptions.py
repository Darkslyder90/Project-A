class AppError(Exception):
    """Basisklasse fuer fachliche Fehler, die als saubere HTTP-Antwort (nicht als
    500er Stacktrace) beim Client ankommen sollen. status_code wird von den
    API-Routen/dem globalen Exception-Handler ausgewertet.
    """

    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class ValidationAppError(AppError):
    status_code = 422
