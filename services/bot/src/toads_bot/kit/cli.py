"""`toads-botkit`: run one of the bots in toads_bot.kit.specs, chosen by TOADS_BOT_SPEC."""

from __future__ import annotations

from toads_bot.kit.spec import KitSettings, build_bot
from toads_bot.kit.specs import SPECS


def main() -> None:
    settings = KitSettings()  # fails fast on a missing variable
    spec = SPECS.get(settings.bot_spec)
    if spec is None:
        raise SystemExit(f"unknown bot {settings.bot_spec!r}; known: {', '.join(sorted(SPECS))}")
    build_bot(spec, settings).run(settings.discord_bot_token.get_secret_value(), log_handler=None)


if __name__ == "__main__":
    main()
