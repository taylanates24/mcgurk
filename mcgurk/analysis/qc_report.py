"""Session quality-control report (steps.md §C Adım 9).

What it reports, all from ``v_trials_flat`` and the session's config snapshot:

* **timing** — dropped frames, the worst frame interval, and how far each
  realised SOA drifted from its nominal one;
* **timeouts** — the fraction of forced-choice trials that got no response
  (a stream's tones and gaps get no press *by design*, so "no response" is not
  a timeout there and is reported as a plain count);
* **the response distribution** per module, so a participant answering the same
  key throughout, or a module that is mostly timeouts, is visible;
* **flagged trials** — marked by a fixed, objective rule (dropped frames over a
  threshold, SOA past a tolerance), never post-hoc: the thresholds come from the
  config's ``qc`` block and are fixed before data collection;
* **the cross-hearing check** — whether the deaf-ear detection was above chance,
  by a one-sided binomial test at ``qc.cross_hearing_alpha``.  Above chance means
  the tone reached the good cochlea through the skull and the spatial-direction
  manipulation is invalid for that participant (§F.3, §6.5); their Modül 1–2
  direction data should be flagged.

No PsychoPy here: the report runs on the analysis machine.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from scipy.stats import binomtest

from ..config.loader import config_from_snapshot
from ..config.schema import QCConfig
from ..db.database import Database
from ..modules.base import row_value

#: The modules that take one forced choice per trial: for these, a trial with no
#: response row is a timeout.  A stream (oddball, GIN) gets no press for most of
#: its events by design; the cross-hearing check is a detection task where not
#: pressing on a catch trial is the *correct* response — so "no response" is not
#: a timeout for any of those, and it is reported as a plain count.
FORCED_CHOICE = ("mcgurk", "avsr", "tbw", "dichotic")

#: Cross-hearing outcome labels (mirror modules.cross_hearing).
_HIT = "HIT"
_MISS = "MISS"
_FALSE_ALARM = "FALSE_ALARM"
_CORRECT_REJECTION = "CORRECT_REJECTION"


class QCError(RuntimeError):
    """Raised when a session cannot be located for a QC report."""


@dataclass(frozen=True)
class FlaggedTrial:
    """One trial marked broken by an objective rule, with the reason(s)."""

    trial_id: int
    module: str
    trial_index: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class TimingSummary:
    n_trials: int
    n_with_timing: int
    total_dropped_frames: int
    worst_dropped_frames: int
    worst_frame_interval_ms: float | None
    worst_abs_soa_deviation_ms: float | None


@dataclass(frozen=True)
class ModuleQC:
    module: str
    n_trials: int
    n_no_response: int
    #: category (or raw key) -> count, over the response rows of this module.
    response_distribution: dict[str, int]

    @property
    def is_forced_choice(self) -> bool:
        return self.module in FORCED_CHOICE

    @property
    def timeout_rate(self) -> float | None:
        """No-response fraction.  Only a *timeout* rate for forced-choice
        modules — None for a stream, where no-response is expected."""
        if not self.is_forced_choice or not self.n_trials:
            return None
        return self.n_no_response / self.n_trials


@dataclass(frozen=True)
class CrossHearingQC:
    ear: str | None
    n_signal: int
    n_catch: int
    hits: int
    misses: int
    false_alarms: int
    correct_rejections: int
    alpha: float
    #: Null p₀ of the binomial test — the guessing rate estimated from catch
    #: trials (0.5 when there are no catch trials to estimate it from).
    null_p: float
    p_value: float | None
    above_chance: bool | None

    @property
    def hit_rate(self) -> float | None:
        return self.hits / self.n_signal if self.n_signal else None

    @property
    def false_alarm_rate(self) -> float | None:
        return self.false_alarms / self.n_catch if self.n_catch else None


@dataclass(frozen=True)
class SessionQC:
    session_id: int
    participant_code: str | None
    group_code: str | None
    timing: TimingSummary
    modules: tuple[ModuleQC, ...]
    flagged: tuple[FlaggedTrial, ...]
    cross_hearing: CrossHearingQC | None

    def summary_text(self) -> str:
        header = (
            f"KK raporu — katılımcı {self.participant_code} ({self.group_code}) "
            f"— oturum {self.session_id}"
        )
        lines = [header, "=" * len(header), "", _timing_text(self.timing), ""]
        lines.append("Modüller:")
        for module in self.modules:
            lines.append(_module_text(module))
        lines.extend(["", _flagged_text(self.flagged)])
        if self.cross_hearing is not None:
            lines.extend(["", _cross_hearing_text(self.cross_hearing, self.group_code)])
        return "\n".join(lines)


# ------------------------------------------------------------------ trials


@dataclass
class _TrialInfo:
    module: str
    trial_index: int
    dropped_frames: int | None = None
    actual_soa_ms: float | None = None
    nominal_soa_ms: float | None = None
    max_frame_interval_ms: float | None = None
    has_response: bool = False
    categories: list[str] = field(default_factory=list)


def _trials(rows: Sequence[object]) -> dict[int, _TrialInfo]:
    """One :class:`_TrialInfo` per trial, from the (trial, response) rows.

    ``v_trials_flat`` LEFT JOINs responses, so a trial appears once with a null
    response (a timeout / no-press) or once per response.  The trial-level
    columns repeat across a trial's rows; the response-level ones differ.
    """
    trials: dict[int, _TrialInfo] = {}
    for row in rows:
        trial_id = row_value(row, "trial_id")
        if trial_id is None:
            continue
        trial_id = int(trial_id)
        info = trials.get(trial_id)
        if info is None:
            info = _TrialInfo(
                module=str(row_value(row, "module")),
                trial_index=int(row_value(row, "trial_index") or 0),
                dropped_frames=_as_int(row_value(row, "dropped_frames")),
                actual_soa_ms=_as_float(row_value(row, "actual_soa_ms")),
                nominal_soa_ms=_as_float(row_value(row, "nominal_soa_ms")),
                max_frame_interval_ms=_as_float(row_value(row, "max_frame_interval_ms")),
            )
            trials[trial_id] = info
        if row_value(row, "response_id") is not None:
            info.has_response = True
            category = row_value(row, "category")
            info.categories.append("(kategori yok)" if category is None else str(category))
    return trials


def _as_int(value: object) -> int | None:
    return None if value is None else int(value)  # type: ignore[call-overload]


def _as_float(value: object) -> float | None:
    return None if value is None else float(value)  # type: ignore[arg-type]


def flag_trials(
    rows: Sequence[object], *, max_dropped_frames: int, soa_tolerance_ms: float
) -> list[FlaggedTrial]:
    """Trials broken by an objective rule, with the reason(s) they were flagged.

    The rules are fixed before data collection (config ``qc`` block): a trial is
    flagged when it dropped more than ``max_dropped_frames`` frames, or when its
    realised SOA drifted more than ``soa_tolerance_ms`` from the nominal one.
    Both are recorded per trial, so this is a re-reading of the data, not a
    judgement made after seeing the result.
    """
    flagged: list[FlaggedTrial] = []
    for trial_id, info in _trials(rows).items():
        reasons: list[str] = []
        if info.dropped_frames is not None and info.dropped_frames > max_dropped_frames:
            reasons.append(f"düşen kare {info.dropped_frames} > {max_dropped_frames}")
        if info.actual_soa_ms is not None and info.nominal_soa_ms is not None:
            deviation = abs(info.actual_soa_ms - info.nominal_soa_ms)
            if deviation > soa_tolerance_ms:
                reasons.append(
                    f"SOA sapması {deviation:.1f} ms > {soa_tolerance_ms:g} ms"
                )
        if reasons:
            flagged.append(
                FlaggedTrial(
                    trial_id=trial_id,
                    module=info.module,
                    trial_index=info.trial_index,
                    reasons=tuple(reasons),
                )
            )
    return sorted(flagged, key=lambda item: item.trial_id)


def timing_summary(rows: Sequence[object]) -> TimingSummary:
    trials = _trials(rows)
    dropped = [t.dropped_frames for t in trials.values() if t.dropped_frames is not None]
    intervals = [
        t.max_frame_interval_ms
        for t in trials.values()
        if t.max_frame_interval_ms is not None
    ]
    deviations = [
        abs(t.actual_soa_ms - t.nominal_soa_ms)
        for t in trials.values()
        if t.actual_soa_ms is not None and t.nominal_soa_ms is not None
    ]
    return TimingSummary(
        n_trials=len(trials),
        n_with_timing=len(dropped),
        total_dropped_frames=sum(dropped),
        worst_dropped_frames=max(dropped, default=0),
        worst_frame_interval_ms=max(intervals, default=None) if intervals else None,
        worst_abs_soa_deviation_ms=max(deviations, default=None) if deviations else None,
    )


def module_qc(rows: Sequence[object]) -> list[ModuleQC]:
    trials = _trials(rows)
    by_module: dict[str, list[_TrialInfo]] = {}
    for info in trials.values():
        by_module.setdefault(info.module, []).append(info)

    result: list[ModuleQC] = []
    for module, infos in by_module.items():
        distribution: dict[str, int] = {}
        n_no_response = 0
        for info in infos:
            if not info.has_response:
                n_no_response += 1
            for category in info.categories:
                distribution[category] = distribution.get(category, 0) + 1
        result.append(
            ModuleQC(
                module=module,
                n_trials=len(infos),
                n_no_response=n_no_response,
                response_distribution=distribution,
            )
        )
    return sorted(result, key=lambda item: item.module)


# ---------------------------------------------------------- cross-hearing


def cross_hearing_qc(rows: Sequence[object], *, alpha: float) -> CrossHearingQC | None:
    """Score the deaf-ear detection check, or None if it did not run.

    Outcomes are derived from ``cross_hearing_signal_present`` and whether a
    press was recorded (the trial columns of ``v_trials_flat``): a signal trial
    with a press is a hit, without one a miss; a catch trial with a press is a
    false alarm, without one a correct rejection.

    Above chance is decided by a one-sided binomial test of the signal-trial
    hits against the guessing rate — the false-alarm rate estimated from the
    catch trials (``null_p``).  With no catch trials to estimate it, the test
    falls back to p₀ = 0.5.  Corner cases (no signal trials) give a null verdict.
    """
    ear: str | None = None
    hits = misses = false_alarms = correct_rejections = 0
    for info in _cross_trials(rows).values():
        if info.ear is not None:
            ear = info.ear
        if info.signal_present:
            hits += info.has_response
            misses += not info.has_response
        else:
            false_alarms += info.has_response
            correct_rejections += not info.has_response

    n_signal = hits + misses
    n_catch = false_alarms + correct_rejections
    if n_signal == 0 and n_catch == 0:
        return None

    null_p = false_alarms / n_catch if n_catch else 0.5
    if n_signal == 0:
        p_value: float | None = None
        above: bool | None = None
    else:
        p_value = float(
            binomtest(k=hits, n=n_signal, p=null_p, alternative="greater").pvalue
        )
        above = p_value < alpha
    return CrossHearingQC(
        ear=ear,
        n_signal=n_signal,
        n_catch=n_catch,
        hits=hits,
        misses=misses,
        false_alarms=false_alarms,
        correct_rejections=correct_rejections,
        alpha=alpha,
        null_p=null_p,
        p_value=p_value,
        above_chance=above,
    )


@dataclass
class _CrossTrialInfo:
    signal_present: bool
    ear: str | None
    has_response: bool = False


def _cross_trials(rows: Sequence[object]) -> dict[int, _CrossTrialInfo]:
    trials: dict[int, _CrossTrialInfo] = {}
    for row in rows:
        if row_value(row, "module") != "cross_hearing":
            continue
        trial_id = row_value(row, "trial_id")
        if trial_id is None:
            continue
        trial_id = int(trial_id)
        info = trials.get(trial_id)
        if info is None:
            ear = row_value(row, "ear")
            info = _CrossTrialInfo(
                signal_present=bool(row_value(row, "cross_hearing_signal_present")),
                ear=None if ear is None else str(ear),
            )
            trials[trial_id] = info
        if row_value(row, "response_id") is not None:
            info.has_response = True
    return trials


# ------------------------------------------------------------------ session


def session_qc(db: Database, session_id: int) -> SessionQC:
    """Assemble the QC report for one session, thresholds from its snapshot."""
    session = db.get_session(session_id)
    if session is None:
        raise QCError(f"Oturum bulunamadı: {session_id}")
    config = config_from_snapshot(str(session["config_snapshot"]))
    qc: QCConfig = config.qc

    rows = db.flat_rows(session_id)
    participant_code = row_value(rows[0], "participant_code") if rows else None
    group_code = row_value(rows[0], "group_code") if rows else None

    return SessionQC(
        session_id=session_id,
        participant_code=None if participant_code is None else str(participant_code),
        group_code=None if group_code is None else str(group_code),
        timing=timing_summary(rows),
        modules=tuple(module_qc(rows)),
        flagged=tuple(
            flag_trials(
                rows,
                max_dropped_frames=qc.max_dropped_frames,
                soa_tolerance_ms=qc.soa_tolerance_ms,
            )
        ),
        cross_hearing=cross_hearing_qc(rows, alpha=qc.cross_hearing_alpha),
    )


# ------------------------------------------------------------------ text


def _timing_text(timing: TimingSummary) -> str:
    interval = (
        "—"
        if timing.worst_frame_interval_ms is None
        else f"{timing.worst_frame_interval_ms:.1f} ms"
    )
    soa = (
        "—"
        if timing.worst_abs_soa_deviation_ms is None
        else f"{timing.worst_abs_soa_deviation_ms:.1f} ms"
    )
    return (
        "Zamanlama:\n"
        f"  Deneme (zamanlama kaydı)  : {timing.n_with_timing}/{timing.n_trials}\n"
        f"  Toplam düşen kare         : {timing.total_dropped_frames}"
        f" (en kötü deneme {timing.worst_dropped_frames})\n"
        f"  En kötü kare aralığı      : {interval}\n"
        f"  En büyük SOA sapması      : {soa}"
    )


def _module_text(module: ModuleQC) -> str:
    if module.timeout_rate is not None:
        rate = f"zaman aşımı %{100 * module.timeout_rate:.1f} ({module.n_no_response})"
    else:
        # Streams (oddball, GIN) and the cross-hearing check get no press for
        # most events by design, so a no-response count is not a timeout there.
        rate = f"yanıtsız {module.n_no_response} (basımsız — beklenebilir)"
    distribution = ", ".join(
        f"{name}:{count}"
        for name, count in sorted(module.response_distribution.items())
    )
    return (
        f"  {module.module:<14} n={module.n_trials:<4} {rate}\n"
        f"      yanıt dağılımı: {distribution or '—'}"
    )


def _flagged_text(flagged: Sequence[FlaggedTrial]) -> str:
    if not flagged:
        return "İşaretlenen deneme: yok."
    lines = [f"İşaretlenen deneme: {len(flagged)}"]
    for item in flagged:
        lines.append(
            f"  trial {item.trial_id} ({item.module} #{item.trial_index}): "
            + "; ".join(item.reasons)
        )
    return "\n".join(lines)


def _cross_hearing_text(cross: CrossHearingQC, group_code: str | None) -> str:
    hit_rate = "—" if cross.hit_rate is None else f"%{100 * cross.hit_rate:.1f}"
    fa_rate = (
        "—" if cross.false_alarm_rate is None else f"%{100 * cross.false_alarm_rate:.1f}"
    )
    lines = [
        f"Çapraz dinleme ({cross.ear or '—'} kulak):",
        f"  İsabet / kaçırma          : {cross.hits} / {cross.misses}"
        f"  (oran {hit_rate})",
        f"  Yanlış alarm / doğru ret  : {cross.false_alarms}"
        f" / {cross.correct_rejections}  (oran {fa_rate})",
    ]
    if cross.above_chance is None:
        lines.append("  Şans üstü mü?             : hesaplanamadı (sinyal denemesi yok)")
        return "\n".join(lines)

    verdict = "EVET — şans üstü" if cross.above_chance else "hayır (şans düzeyinde)"
    lines.append(
        f"  Şans üstü mü? (binomial)  : {verdict}"
        f"  (p={cross.p_value:.3f}, alfa={cross.alpha:g}, p0={cross.null_p:.2f})"
    )
    if cross.above_chance and group_code in ("SSD_R", "SSD_L"):
        # The whole point of the check: if the deaf ear heard the tone, the
        # lateralisation is invalid for this participant.
        lines.append(
            "  UYARI: sağır kulak tonu şans üstü duydu — bu katılımcının Modül 1-2 "
            "uzamsal yön verisi geçersiz sayılmalı (§6.5)."
        )
    return "\n".join(lines)
