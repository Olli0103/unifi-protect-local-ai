"""Read-only comparison of private Protect event metadata across a slot change."""
import re

from .aiport_deployment import AiPortPlanError


def _samples(events):
    if not isinstance(events, list) or not 1 <= len(events) <= 4096:
        raise AiPortPlanError("Expected a nonempty, bounded list of recording events")
    result = {}
    for row in events:
        if not isinstance(row, dict):
            raise AiPortPlanError("Invalid recording event metadata")
        event, camera, start, end = (row.get(k) for k in ("id", "camera", "start", "end"))
        if (not isinstance(event, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", event)
                or not isinstance(camera, str) or not re.fullmatch(r"[0-9a-fA-F]{24}", camera)
                or type(start) is not int or type(end) is not int or not 0 <= start <= end <= 2**53 - 1
                or event in result):
            raise AiPortPlanError("Invalid or duplicate recording event metadata")
        result[event] = (camera, start, end)
    return result


def verify_recording_links(previous_plan, plan, before, after):
    """Check event IDs, native camera IDs, recording intervals and original slots."""
    previous, current = _samples(before), _samples(after)

    def owners(deployment, field):
        return {camera: slot["slot"] for slot in deployment["instances"] for camera in slot.get(field, [])}

    old_active, active = owners(previous_plan, "camera_ids"), owners(plan, "camera_ids")
    old_slots = old_active | owners(previous_plan, "retired_camera_ids")
    slots = active | owners(plan, "retired_camera_ids")
    sampled = {camera for camera, _, _ in previous.values()}
    if not (old_active.keys() - active.keys()) <= sampled:
        raise AiPortPlanError("Missing a recording sample for a removed camera")
    for event, sample in previous.items():
        camera = sample[0]
        if current.get(event) != sample or camera not in old_slots or old_slots[camera] != slots.get(camera):
            raise AiPortPlanError("A recording event, camera, interval or original slot no longer matches")
