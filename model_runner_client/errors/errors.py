class InvalidCoordinatorUsageError(Exception):
    """Raised when the coordinator does not use the library correctly or violates the call contract."""
    def __init__(self, message="The coordinator did not use the library correctly. Please check the call contract."):
        super().__init__(message)