class KloppyError(Exception):
    pass


class DeserializationError(KloppyError):
    pass


class OrientationError(KloppyError):
    pass


class OrphanedRecordError(KloppyError):
    pass


class InvalidFilterError(KloppyError):
    pass


class AdapterError(KloppyError):
    pass


class InputNotFoundError(KloppyError):
    pass
