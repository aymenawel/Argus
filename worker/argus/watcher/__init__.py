"""The watcher decides when a frame is worth segmenting (KB 03): change, check-ins, or a steady tick."""

from argus.watcher.watcher import Trigger, Watcher, WatcherSettings

__all__ = ["Trigger", "Watcher", "WatcherSettings"]
