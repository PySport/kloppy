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
