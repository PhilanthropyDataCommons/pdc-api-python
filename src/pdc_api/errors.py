from typing import Any


class PDCException(Exception):
    def __init__(self, *, detail: Any, code: int | None = None) -> None:
        super().__init__(str(detail))
        self.detail = detail
        self.code = code


class PDCBadRequestError(PDCException):
    pass


class PDCUnauthorizedError(PDCException):
    pass


class PDCForbiddenError(PDCException):
    pass


class PDCServiceError(PDCException):
    pass


# PDC returns 404 rather than 403 for a resource the caller may not view.
class PDCNotFoundError(PDCException):
    pass


class PDCConflictError(PDCException):
    pass


class PDCUnprocessableEntityError(PDCException):
    pass


class KeycloakSyncError(PDCException):
    pass


class TokenRequestError(PDCException):
    pass


class ProposalNotFoundError(PDCNotFoundError):
    pass


class ChangemakerNotFoundError(PDCNotFoundError):
    pass


class ChangemakerFieldValueBatchNotFoundError(PDCNotFoundError):
    pass


class FunderNotFoundError(PDCNotFoundError):
    pass


class ApplicationFormNotFoundError(PDCNotFoundError):
    pass
