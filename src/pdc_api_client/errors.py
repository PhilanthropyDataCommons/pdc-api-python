class PDCException(Exception):
    def __init__(self, *, detail, code=None):
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


class TokenRequestError(PDCException):
    pass


class ProposalNotFoundError(Exception):
    pass


class ChangemakerNotFoundError(Exception):
    pass


class ChangemakerFieldValueBatchNotFoundError(Exception):
    pass


class FunderNotFoundError(Exception):
    pass


class ApplicationFormNotFoundError(PDCNotFoundError):
    pass
