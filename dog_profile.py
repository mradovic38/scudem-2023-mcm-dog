import random
from dataclasses import dataclass


@dataclass(frozen=True)
class DogProfile:
    """All tunable parameters describing a single dog's fetching ability.

    Defaults model the idealized *Optimal* dog (~92% catch rate). Create another
    dog by overriding only the fields you want to change, e.g.::

        FITZ = DogProfile(name="Fitz", max_speed=8.0, acceleration=7.0, ...)
    """

    name: str = "Optimal"

    # Reaction
    reaction_time_ms_min: float = 150
    reaction_time_ms_max: float = 300

    # Movement
    max_speed: float = 12.0           # m/s
    acceleration: float = 15.0        # m/s^2 (burst acceleration)

    # Jaw geometry
    jaw_rotation_speed: float = 7.0   # radians per second
    arrow_length: float = 0.12        # meters, jaw length / catch radius
    arrow_height: float = 0.07        # meters, height of direction triangle
    jaw_open_angle: float = 0.4       # radians, max jaw opening (each side)
    jaw_angle_offset: float = 0.2     # radians, jaw aim offset vs ball approach
    jaw_open_speed_multiplier: float = 10.0
    jaw_close_duration: float = 0.05  # seconds, time for the jaw to snap shut

    # Error / mistiming ranges (zero = perfect timing, the Optimal default)
    jump_mistime_min: float = 0.0     # seconds, max early jump
    jump_mistime_max: float = 0.0     # seconds, max late jump
    jaw_error_min: float = 0.0        # radians, max downward jaw error
    jaw_error_max: float = 0.0        # radians, max upward jaw error
    jaw_close_mistime_min: float = 0.0
    jaw_close_mistime_max: float = 0.0

    def sample_reaction_delay_s(self):
        return random.uniform(self.reaction_time_ms_min, self.reaction_time_ms_max) / 1000.0

    def sample_jump_mistime(self):
        return random.uniform(self.jump_mistime_min, self.jump_mistime_max)

    def sample_jaw_error(self):
        return random.uniform(self.jaw_error_min, self.jaw_error_max)

    def sample_jaw_close_mistime(self):
        return random.uniform(self.jaw_close_mistime_min, self.jaw_close_mistime_max)
