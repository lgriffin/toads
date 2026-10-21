"""Rules for the officers' task board. No RBAC, web framework or storage imports: the routes decide who may call
(the raid day's officers) and the repository decides where cards live."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

from toads_api.officer_board.repository import BoardRepository, Card, CardFields, NightLink

# The board's lanes, left to right. A card's lane is one of these ids.
LANES: dict[str, str] = {"todo": "To do", "doing": "In progress", "done": "Done"}
TITLE_LIMIT = 200
NOTES_LIMIT = 2000
# A board is a working list, not an archive: past this, officers clear Done before adding more.
CARD_LIMIT = 200
# Links pinned to a night: its strategy doc, role sheet and Drive folder, not a bookmark list.
LINK_LIMIT = 12
LINK_LABEL_LIMIT = 80
LINK_URL_LIMIT = 500


class BoardError(Exception):
    """A request the rules refuse. `status` is the HTTP code the adapter should answer with."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


@dataclass(frozen=True)
class CardView:
    card: Card
    # The assignee's shown name; None when the card is unassigned.
    assignee_name: str | None
    # Due before today and not yet done.
    overdue: bool


@dataclass(frozen=True)
class Lane:
    id: str
    name: str
    cards: list[CardView]


class OfficerBoardService:
    def __init__(
        self,
        repo: BoardRepository,
        shown_names: Callable[[Iterable[int]], dict[int, str]],
        today: Callable[[], date],
    ) -> None:
        self.repo = repo
        self._shown_names = shown_names
        self._today = today

    def board(self, raid_day: str) -> list[Lane]:
        """The day's board: every lane in order, each card in its place. A card in a retired lane shows under To do."""
        cards = self.repo.cards(raid_day)
        names = self._shown_names({a for c in cards if (a := c.fields.assignee_member_id) is not None})
        today = self._today()
        by_lane: dict[str, list[CardView]] = {lane: [] for lane in LANES}
        for c in cards:
            assignee = c.fields.assignee_member_id
            overdue = c.lane != "done" and c.fields.due_on is not None and c.fields.due_on < today
            view = CardView(c, names.get(assignee) if assignee is not None else None, overdue)
            by_lane.get(c.lane, by_lane["todo"]).append(view)
        return [Lane(lane, name, by_lane[lane]) for lane, name in LANES.items()]

    def _fields(self, title: str, notes: str, assignee: int | None, due_on: date | None) -> CardFields:
        title = " ".join(title.split())
        if not title:
            raise BoardError("A card needs a title", status=422)
        if len(title) > TITLE_LIMIT:
            raise BoardError(f"Keep the title to {TITLE_LIMIT} characters", status=422)
        notes = notes.strip()
        if len(notes) > NOTES_LIMIT:
            raise BoardError(f"Keep the notes to {NOTES_LIMIT} characters", status=422)
        if assignee is not None and assignee not in self._shown_names([assignee]):
            raise BoardError("That member has not signed in to the hub", status=422)
        return CardFields(title, notes, assignee, due_on)

    def _view(self, card: Card) -> CardView:
        lanes = self.board(card.raid_day)
        return next(v for lane in lanes for v in lane.cards if v.card.id == card.id)

    def add(
        self,
        raid_day: str,
        *,
        title: str,
        by: int,
        notes: str = "",
        assignee: int | None = None,
        due_on: date | None = None,
        lane: str = "todo",
    ) -> CardView:
        if lane not in LANES:
            raise BoardError("Unknown lane", status=422)
        fields = self._fields(title, notes, assignee, due_on)
        if len(self.repo.cards(raid_day)) >= CARD_LIMIT:
            raise BoardError(f"The board holds {CARD_LIMIT} cards; clear some from Done first", status=409)
        return self._view(self.repo.add(raid_day, lane, fields, by))

    def edit(
        self,
        raid_day: str,
        card_id: int,
        *,
        title: str,
        by: int,
        notes: str = "",
        assignee: int | None = None,
        due_on: date | None = None,
    ) -> CardView:
        card = self.repo.edit(raid_day, card_id, self._fields(title, notes, assignee, due_on), by)
        if card is None:
            raise BoardError("No such card on this board", status=404)
        return self._view(card)

    def move(self, raid_day: str, card_id: int, *, lane: str, position: int, by: int) -> list[Lane]:
        """Move a card to `position` in `lane` (clamped to the lane's length); returns the board as it now stands."""
        if lane not in LANES:
            raise BoardError("Unknown lane", status=422)
        # Stored lanes, not board()'s view: a card in a retired lane keeps its lane when its neighbours move.
        lanes: dict[str, list[int]] = {lane_id: [] for lane_id in LANES}
        source = None
        for c in self.repo.cards(raid_day):
            lanes.setdefault(c.lane, []).append(c.id)
            if c.id == card_id:
                source = c.lane
        if source is None:
            raise BoardError("No such card on this board", status=404)
        lanes[source].remove(card_id)
        target = lanes[lane]
        target.insert(max(0, min(position, len(target))), card_id)
        touched = {source: lanes[source], lane: target}
        if not self.repo.arrange(raid_day, card_id, touched, by):
            raise BoardError("No such card on this board", status=404)
        return self.board(raid_day)

    def remove(self, raid_day: str, card_id: int, by: int) -> None:
        if not self.repo.remove(raid_day, card_id, by):
            raise BoardError("No such card on this board", status=404)

    # ------------------------------------------------------------------------------------------- pinned links

    def links(self, raid_day: str) -> list[NightLink]:
        return self.repo.links(raid_day)

    def add_link(self, raid_day: str, *, label: str, url: str, by: int) -> NightLink:
        """Pin a link to the night. Only https links to a real host, so a pinned link never runs script or opens a
        local file; Google Drive is the usual one, but any https page is allowed."""
        label = " ".join(label.split())
        if not label or len(label) > LINK_LABEL_LIMIT:
            raise BoardError(f"Give the link a name of up to {LINK_LABEL_LIMIT} characters", status=422)
        url = url.strip()
        parts = urlsplit(url)
        if len(url) > LINK_URL_LIMIT or parts.scheme != "https" or not parts.hostname or "." not in parts.hostname:
            raise BoardError("Paste a full https:// link, such as a Google Drive share link", status=422)
        if len(self.repo.links(raid_day)) >= LINK_LIMIT:
            raise BoardError(f"A night holds {LINK_LIMIT} links; take one off first", status=409)
        return self.repo.add_link(raid_day, label, url, by)

    def remove_link(self, raid_day: str, link_id: int, by: int) -> None:
        if not self.repo.remove_link(raid_day, link_id, by):
            raise BoardError("No such link on this night", status=404)
