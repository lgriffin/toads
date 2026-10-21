/**
 * The preview's Decisions panels: a few sample applicants kept in the browser only, so the page works on GitHub Pages
 * with no hub behind it. Notes and decisions last until the page reloads.
 */
import { ApiError } from '$lib/api';
import { NIGHT_NAMES } from '$lib/nights';
import type { ApplicationNote, DecisionApplication, DecisionBackend, DecisionCard } from '$lib/decisions';

const ROOM = 'https://discord.com/channels/0/0';
const ago = (hours: number) => new Date(Date.now() - hours * 3_600_000).toISOString();

function applicant(
  id: number,
  day: string,
  fields: Partial<DecisionApplication> & Pick<DecisionApplication, 'character_name' | 'class_name' | 'role'>
): DecisionApplication {
  return {
    id,
    applicant_name: fields.character_name.toLowerCase().replace(' ', '_'),
    secondary_role: null,
    why_toads: '',
    raid_days: [day],
    logs_url: null,
    status: 'interviewing',
    interview_room_error: null,
    interview_room_url: ROOM,
    created_at: ago(30),
    ...fields
  };
}

function note(id: number, appId: number, author: string | null, body: string, hours: number): ApplicationNote {
  return { id, application_id: appId, author_name: author, body, at: ago(hours) };
}

export function previewDecisions(): DecisionBackend {
  const cards: DecisionCard[] = [
    {
      application: applicant(1, 'wed', {
        character_name: 'Mossbeard',
        class_name: 'Shaman',
        role: 'Healer',
        secondary_role: 'Ranged',
        why_toads: 'A friend raids with you and says the pond is a good place to be. Cleared SSC on another server.',
        logs_url: 'https://fresh.warcraftlogs.com/character/eu/spineshatter/mossbeard'
      }),
      notes: [
        note(1, 1, 'Gallagher', 'Talked in the room for 20 minutes. Knows the Vashj fight well.', 20),
        note(2, 1, 'Hadur', 'Logs look solid; free every Wednesday.', 6)
      ],
      decided_at: null
    },
    {
      application: applicant(2, 'wed', {
        character_name: 'Big Toad',
        class_name: 'Warrior',
        role: 'Tank',
        secondary_role: 'Melee',
        why_toads: 'Looking for a relaxed Wednesday team.',
        status: 'applied',
        interview_room_url: null,
        interview_room_error: 'The Toad Bot needs Manage Roles in the Interviews category',
        created_at: ago(3)
      }),
      notes: [],
      decided_at: null
    },
    {
      application: applicant(3, 'sun', {
        character_name: 'Lilyfin',
        class_name: 'Mage',
        role: 'Ranged',
        why_toads: 'Sunday is the only night I can raid.'
      }),
      notes: [],
      decided_at: null
    },
    {
      application: applicant(4, 'wed', {
        character_name: 'Hopscotch',
        class_name: 'Rogue',
        role: 'Melee',
        status: 'accepted'
      }),
      notes: [note(3, 4, null, 'Gave Hopscotch the Wednesday raider role in Discord.', 47)],
      decided_at: ago(48)
    }
  ];
  let ids = 100;
  const find = (day: string, id: number) => {
    const card = cards.find((c) => c.application.id === id && c.application.raid_days.includes(day));
    if (!card) throw new ApiError(404, 'No such application');
    return card;
  };
  const open = (card: DecisionCard) => ['applied', 'interviewing', 'trial_offered'].includes(card.application.status);
  return {
    board: async (day) => ({
      raid_day: day,
      waiting: cards.filter((c) => c.application.raid_days.includes(day) && open(c)),
      decided: cards.filter((c) => c.application.raid_days.includes(day) && !open(c))
    }),
    note: async (day, id, body) => {
      const card = find(day, id);
      if (!open(card)) throw new ApiError(409, 'This application has been decided; notes are closed');
      const added = note(ids++, id, 'You', body, 0);
      card.notes.push(added);
      return added;
    },
    decide: async (day, id, decision) => {
      const card = find(day, id);
      if (!open(card)) throw new ApiError(409, `This application is already ${card.application.status}`);
      const night = NIGHT_NAMES[day] ?? day;
      card.application.status = decision === 'accept' ? 'accepted' : 'declined';
      card.decided_at = new Date().toISOString();
      if (decision === 'accept') {
        card.notes.push(note(ids++, id, null, `Gave ${card.application.character_name} the ${night} raider role in Discord.`, 0));
      }
      return card.application;
    }
  };
}
