from typing import Any, Dict, List, Optional


def filter_event_driven_frames(
    frames: List[Dict[str, Any]], event_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Filter frames containing significant events like kills, objectives, or multi-kills.

    Args:
        frames: List of timeline frames to filter
        event_types: List of event types to filter for. Defaults to ['CHAMPION_KILL', 'BUILDING_KILL', 'CHAMPION_SPECIAL_KILL', 'ELITE_MONSTER_KILL']

    Returns:
        List[Dict[str, Any]]: Frames containing the specified events
    """
    if event_types is None:
        event_types = [
            "CHAMPION_KILL",
            "BUILDING_KILL",
            "CHAMPION_SPECIAL_KILL",
            "ELITE_MONSTER_KILL",
        ]

    filtered_frames = []
    for frame in frames:
        if _extract_events_from_frame(frame, event_types):
            filtered_frames.append(frame)

    return filtered_frames


def filter_power_spike_frames(
    frames: List[Dict[str, Any]], gold_threshold: int = 3000
) -> List[Dict[str, Any]]:
    """Identify frames where players completed major item purchases (power spikes).

    Args:
        frames: List of timeline frames to analyze
        gold_threshold: Minimum gold expenditure to consider a power spike

    Returns:
        List[Dict[str, Any]]: Frames where significant gold expenditure occurred
    """
    if len(frames) < 2:
        return frames

    power_spike_frames = []

    for i, curr_frame in enumerate(frames):
        if i == 0:
            continue

        prev_frame = frames[i - 1]

        for participant_id in range(1, 11):
            gold_spent = _calculate_gold_expenditure(
                prev_frame, curr_frame, participant_id
            )
            if gold_spent >= gold_threshold:
                if curr_frame not in power_spike_frames:
                    power_spike_frames.append(curr_frame)
                break

    return power_spike_frames


def get_strategic_frame_subset(
    frames: List[Dict[str, Any]], target_count: int = 10
) -> List[Dict[str, Any]]:
    """Get optimized frame selection combining multiple filtering strategies.

    Args:
        frames: List of timeline frames to filter
        target_count: Target number of frames to return (default: 10)

    Returns:
        List[Dict[str, Any]]: Strategically selected frames combining event-driven and power spike filtering
    """
    if len(frames) <= target_count:
        return frames

    strategic_frames = set()

    strategic_frames.add(id(frames[0]))
    strategic_frames.add(id(frames[-1]))

    event_frames = filter_event_driven_frames(frames)
    for frame in event_frames:
        strategic_frames.add(id(frame))

    power_spike_frames = filter_power_spike_frames(frames)
    for frame in power_spike_frames:
        strategic_frames.add(id(frame))

    selected_frames = []
    for frame in frames:
        if id(frame) in strategic_frames:
            selected_frames.append(frame)

    if len(selected_frames) > target_count:
        selected_frames.sort(key=lambda x: x.get("timestamp", 0))
        first_frame = selected_frames[0]
        recent_frames = selected_frames[-target_count + 1 :]
        selected_frames = [first_frame] + recent_frames

        seen = set()
        final_frames = []
        for frame in selected_frames:
            frame_id = id(frame)
            if frame_id not in seen:
                seen.add(frame_id)
                final_frames.append(frame)

        return final_frames[:target_count]

    return selected_frames


def _extract_events_from_frame(frame: Dict[str, Any], event_types: List[str]) -> bool:
    """Check if frame contains any of the specified event types."""
    if "events" not in frame:
        return False

    for event in frame["events"]:
        if event.get("type") in event_types:
            return True
    return False


def _calculate_gold_expenditure(
    prev_frame: Dict[str, Any], current_frame: Dict[str, Any], participant_id: int
) -> int:
    """Calculate gold spent between two frames for a participant."""
    if (
        "participantFrames" not in prev_frame
        or "participantFrames" not in current_frame
    ):
        return 0

    prev_participant = prev_frame["participantFrames"].get(str(participant_id))
    current_participant = current_frame["participantFrames"].get(str(participant_id))

    if not prev_participant or not current_participant:
        return 0

    prev_gold_earned = prev_participant.get("totalGold", 0)
    prev_gold_current = prev_participant.get("currentGold", 0)
    current_gold_earned = current_participant.get("totalGold", 0)
    current_gold_current = current_participant.get("currentGold", 0)

    gold_gained = current_gold_earned - prev_gold_earned
    gold_spent = (prev_gold_current + gold_gained) - current_gold_current

    return max(0, gold_spent)
