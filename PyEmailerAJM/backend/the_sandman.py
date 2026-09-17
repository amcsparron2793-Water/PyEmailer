from datetime import datetime
from typing import Optional

from TheSandmanAJM import TheSandman


class PyEmailerTheSandman(TheSandman):
    """
    Handles email snooze functionality with a configurable expiration limit.

    The PyEmailerTheSandman class extends the functionality of TheSandman to
    include customizable snooze expiration, providing developers with a
    framework for time-based snooze state checks. This class is particularly
    useful in scenarios where email alerts or reminders must be temporarily
    disabled for a predefined duration.

    :ivar snooze_expiration_limit_hours: Default number of hours after which
        a snooze is considered expired. Can be overridden via initialization
        parameters.
    :type snooze_expiration_limit_hours: int
    """
    DEFAULT_SNOOZE_EXPIRATION_LIMIT_HOURS = 24
    SECONDS_IN_HOUR = 3600

    def __init__(self, sleep_time_seconds=None, **kwargs):
        super().__init__(sleep_time_seconds, **kwargs)
        self.snooze_expiration_limit_hours = kwargs.get('snooze_expiration_limit_hours',
                                                        self.__class__.DEFAULT_SNOOZE_EXPIRATION_LIMIT_HOURS)

    @classmethod
    def is_snooze_expired(cls, snoozed_at: datetime, snooze_expiration_limit_hours: Optional[int] = None):
        if not snooze_expiration_limit_hours:
            snooze_expiration_limit_hours = cls.DEFAULT_SNOOZE_EXPIRATION_LIMIT_HOURS
        snooze_expiration_limit_seconds = snooze_expiration_limit_hours * cls.SECONDS_IN_HOUR
        time_since_snooze = (datetime.now() - snoozed_at)
        if time_since_snooze.total_seconds() >= snooze_expiration_limit_seconds:
            #print('msg_snoozed expired! Unsnoozing now!')
            return True
        return False


if __name__ == '__main__':
    ts = PyEmailerTheSandman(sleep_time_seconds=30)
    ts.sleep_in_rounds(rounds=3)
