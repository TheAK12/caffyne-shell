from snippets import Icon
from gi.repository import Playerctl

class MediaIcon(Icon):
    def __init__(self, player, **kwargs):
        super().__init__(
            icon_name="play-duotone",
            **kwargs,
        )

        player.connect(
            "playback-status",
            lambda obj, status: setattr(
                self,
                "icon_name",
                "pause-duotone" if status == Playerctl.PlaybackStatus.PLAYING else "play-duotone",
            ),
        )