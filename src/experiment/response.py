"""Response collection and reaction time measurement."""

from dataclasses import dataclass

from psychopy import core, event

from .stimuli import ABORT_KEY, AbortSession


@dataclass
class ResponseData:
    """Raw response data from a single trial."""

    key_pressed: str
    syllable: str
    rt_from_video_end_ms: float
    rt_from_options_shown_ms: float


def collect_response(
    valid_keys: list[str],
    key_to_syllable: dict[str, str],
    video_end_time: float,
    options_shown_time: float,
    clock: core.Clock,
) -> ResponseData:
    """Wait for a valid key press and compute reaction times.

    Args:
        valid_keys: List of accepted keys (e.g., ["1", "2", "3"]).
        key_to_syllable: Mapping from key to syllable name.
        video_end_time: Clock time when the stimulus ended.
        options_shown_time: Clock time when response options appeared.
        clock: The clock used for timing.

    Returns:
        The collected response.

    Raises:
        AbortSession: if the abort key was pressed instead of a response.
    """
    all_keys = valid_keys + [ABORT_KEY]
    event.clearEvents()
    keys = event.waitKeys(keyList=all_keys, timeStamped=clock)

    if not keys:
        # waitKeys returns empty only when interrupted; treat that as an abort
        # rather than silently recording a response that was never given.
        raise AbortSession()

    key, press_time = keys[0]

    if key == ABORT_KEY:
        raise AbortSession()

    syllable = key_to_syllable.get(key, key)
    rt_video = (press_time - video_end_time) * 1000.0
    rt_options = (press_time - options_shown_time) * 1000.0

    return ResponseData(
        key_pressed=key,
        syllable=syllable,
        rt_from_video_end_ms=rt_video,
        rt_from_options_shown_ms=rt_options,
    )
