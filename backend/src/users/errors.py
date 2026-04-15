class DuplicateInfoError(ValueError):
    """Data duplication error on creating or updating a model."""

    pass


class StrokeDataError(ValueError):
    """Invalid combination of stroke type and subtype."""

    pass


class InactiveUserError(ValueError):
    """Operation attempted on a deactivated user."""

    pass
