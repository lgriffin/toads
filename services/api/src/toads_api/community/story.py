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
    "Toads has raided together for six years. We are a tight-knit community with a UK and Scandinavian core: we have "
    "met up in real life, made lasting friendships and kept turning up for each other, raid after raid.",
    "We cut our teeth on Classic Fresh on Spineshatter, clearing Molten Core through to Naxxramas with a focus on "
    "speed runs, then grew to four strong teams in The Burning Crusade, from Karazhan to Black Temple and Mount Hyjal. "
    "Three ran as full guild raids under a loot council and one on soft reserves.",
    "Semi-hardcore means organised and competitive without losing the fun. We want players who put the guild first: "
    "friendly, prepared and team-focused, with a good sense of humour and the ability to take feedback. Experienced "
    "raid leaders run the night, and everyone pulls their weight.",
    "World of Warcraft: Forever will follow the same pattern: three 40-man teams on Wednesday, Thursday and Sunday, "
    "clearing in one night wherever we can, with Discord as the pond in between.",
)
