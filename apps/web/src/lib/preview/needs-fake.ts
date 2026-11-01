/**
 * The preview's recruitment needs: the sample needs, kept in the browser only, so Officers > Recruitment and the
 * homepage work on GitHub Pages with no hub behind them. An officer's change shows on the homepage until the page
 * reloads.
 */
import { ApiError } from '$lib/api';
import { CLASSES, SPECS } from '$lib/comp';
import type { RecruitmentNeed } from '$lib/community';
import { needs as samples } from '$lib/mock/community';
import type { RaidDay } from '$lib/mock/data';
import { NIGHT_NAMES, raidNight } from '$lib/nights';
import type { NeedsBackend, NightNeed, NightNeeds } from '$lib/recruiting';

const ROLE: Record<string, NightNeed['role']> = { tank: 'Tank', healer: 'Healer', melee: 'Melee', ranged: 'Ranged' };

let store: RecruitmentNeed[] = samples.map((n) => ({ ...n, raidDays: [...n.raidDays] }));

const onNight = (n: RecruitmentNeed, day: string) => n.raidDays.length === 1 && raidNight(n.raidDays[0])?.id === day;

function view(day: string): NightNeeds {
  const needs: NightNeed[] = [];
  for (const n of store.filter((x) => onNight(x, day))) {
    const spec = SPECS.find((s) => s.name === n.spec && CLASSES.find((c) => c.id === s.wowClass)?.name === n.className);
    if (spec) needs.push({ spec_id: spec.id, class_name: n.className, spec: n.spec, role: n.role, priority: n.priority });
  }
  return { raid_day: day, needs };
}

/** Every night's needs, as the homepage reads them. */
export const previewPublicNeeds = (): RecruitmentNeed[] => store.map((n) => ({ ...n, raidDays: [...n.raidDays] }));

export function previewNeeds(): NeedsBackend {
  return {
    needs: async (day) => view(day),
    save: async (day, picks) => {
      if (new Set(picks.map((p) => p.spec_id)).size !== picks.length) throw new ApiError(422, 'A spec is listed twice');
      const night = (NIGHT_NAMES[day] ?? day) as RaidDay;
      const fresh = picks.map((p): RecruitmentNeed => {
        const spec = SPECS.find((s) => s.id === p.spec_id);
        if (!spec) throw new ApiError(422, `No spec has the id ${p.spec_id}`);
        const className = CLASSES.find((c) => c.id === spec.wowClass)?.name ?? spec.wowClass;
        return { className, spec: spec.name, role: ROLE[spec.role], priority: p.priority, raidDays: [night] };
      });
      store = [...store.filter((n) => !onNight(n, day)), ...fresh];
      return view(day);
    }
  };
}
