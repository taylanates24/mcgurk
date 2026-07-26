"""Response collection and reaction time measurement."""

from dataclasses import dataclass

from psychopy import core, event


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
    escape_key: str = "escape",
) -> ResponseData | None:
    """Wait for a valid key press and compute reaction times.

    Args:
        valid_keys: List of accepted keys (e.g., ["1", "2", "3"]).
        key_to_syllable: Mapping from key to syllable name.
        video_end_time: Clock time when video ended.
        options_shown_time: Clock time when response options appeared.
        clock: The clock used for timing.
        escape_key: Key to abort the experiment.

    Returns:
        ResponseData or None if escape was pressed.
    """
    all_keys = valid_keys + [escape_key]
    event.clearEvents()
    keys = event.waitKeys(keyList=all_keys, timeStamped=clock)

    if not keys:
        return None

    key, press_time = keys[0]

    if key == escape_key:
        return None

    syllable = key_to_syllable.get(key, key)
    rt_video = (press_time - video_end_time) * 1000.0
    rt_options = (press_time - options_shown_time) * 1000.0

    return ResponseData(
        key_pressed=key,
        syllable=syllable,
        rt_from_video_end_ms=rt_video,
        rt_from_options_shown_ms=rt_options,
    )
