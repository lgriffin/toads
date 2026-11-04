"""The public Story page's words: the tagline and the guild's story, the first thing a visitor reads.

They live in the repository, not in config/community.yaml, so a change ships with a merge and the deploy that follows;
nobody edits the server to update them. The static preview shows the same words (apps/web/src/lib/mock/community.ts),
and a test keeps the two in step.
"""

from __future__ import annotations

TAGLINE = (
    "A semi-hardcore, very social raiding guild on Spineshatter: organised, competitive and locked in on speed and "
    "execution."
)

STORY: tuple[str, ...] = (
    "toads was founded in 2019 by a core of English friends who wanted to create a guild that could progress through "
    "Classic, together. This community soon developed into a large group of players from all over the world, "
    "although with a predominately UK and Scandinavian core. The guild smashed through each iteration of Classic, "
    "growing stronger and stronger. Many IRL friendships grew from this community and after seven years together, "
    "we have strong roots and a very experienced team of officers.",
    "We are a semi-hardcore guild that appeals to players with high skill who operate on a limited timeframe. We are "
    "competitive, disciplined, well-organized and have high expectations from our players. We are very protective of "
    "our community and the guild comes first in all matters.",
    "Our guild strength has peaked in WoW Forever and we begin the game with three 40-man raid teams "
    "(Wednesday/Thursday/Sunday).",
    "toads has been a constant in the lives of our guildies for many years now and we have no intent of slowing down.",
)
