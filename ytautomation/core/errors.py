class PipelineError(Exception):
    """Base error for pipeline failures."""


class ConfigError(PipelineError):
    pass


class ArtifactMissingError(PipelineError):
    pass


class ValidationError(PipelineError):
    pass
