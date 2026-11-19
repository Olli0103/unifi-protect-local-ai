"""Edit local pool membership while preserving the identity and unrelated camera settings."""
from .aiport_ingest import normalize_mac


def passive_slot(config):
    return (isinstance(config, dict)
            and {"controller_ip", "controller_pin", "device_ip", "mac", "firmware_version"} <= config.keys()
            and not any(k in config for k in ("paired_streams", "paired_stream", "live_pool_detector",
                                               "diagnostic_stream", "diagnostic_streams", "live_detector")))


def restrict_detector(detector, cameras):
    if "plate_cameras" in detector:
        plates = [c for c in detector["plate_cameras"] if normalize_mac(c) in cameras]
        if plates:
            detector["plate_cameras"] = plates
        else:
            del detector["plate_cameras"]
            detector.pop("ocr_provider_config", None)
    if "camera_thresholds" in detector:
        gates = {k: v for k, v in detector["camera_thresholds"].items() if normalize_mac(k) in cameras}
        if gates:
            detector["camera_thresholds"] = gates
        else:
            del detector["camera_thresholds"]


def replace_streams(config, streams):
    """Keep each camera's permissions with its own MAC, including after a reorder."""
    cameras = {normalize_mac(s["camera_mac"]) for s in streams}
    if streams:
        config["paired_streams"] = streams
        if "live_pool_detector" in config:
            restrict_detector(config["live_pool_detector"], cameras)
    else:
        config.pop("paired_streams", None)
        config.pop("live_pool_detector", None)
    if "live_speech_cameras" in config:
        speech = [c for c in config["live_speech_cameras"] if normalize_mac(c) in cameras]
        if speech:
            config["live_speech_cameras"] = speech
        else:
            del config["live_speech_cameras"]
            config.pop("live_speech_max_events_per_hour", None)
    for name in ("live_face", "live_sound"):
        if name in config:
            keep = [c for c in config[name]["cameras"] if normalize_mac(c) in cameras]
            if keep:
                config[name]["cameras"] = keep
            else:
                del config[name]
