"""Domain errors for the skill pool."""


class SkillPickerError(Exception):
    """Base error for skill-picker."""


class SkillNotFoundError(SkillPickerError):
    """Raised when a skill id does not exist in the pool."""

    def __init__(self, skill_id: str):
        self.skill_id = skill_id
        super().__init__(f"skill not found: {skill_id!r}")


class SkillExistsError(SkillPickerError):
    """Raised when adding a skill whose id already exists."""

    def __init__(self, skill_id: str):
        self.skill_id = skill_id
        super().__init__(f"skill already exists: {skill_id!r}")
