/** Application pipeline (design: ApplicationStatus). The API enforces the same table; this only drives the buttons. */

export type ApplicationStatus = 'applied' | 'interviewing' | 'trial_offered' | 'accepted' | 'declined' | 'withdrawn';

export const APPLICATION_STATUSES: readonly ApplicationStatus[] = [
  'applied',
  'interviewing',
  'trial_offered',
  'accepted',
  'declined',
  'withdrawn'
];

export const TRANSITIONS: Readonly<Record<ApplicationStatus, readonly ApplicationStatus[]>> = {
  applied: ['interviewing', 'declined', 'withdrawn'],
  interviewing: ['trial_offered', 'declined', 'withdrawn'],
  trial_offered: ['accepted', 'declined', 'withdrawn'],
  accepted: [],
  declined: [],
  withdrawn: []
};

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  applied: 'Applied',
  interviewing: 'Interviewing',
  trial_offered: 'Trial offered',
  accepted: 'Accepted',
  declined: 'Declined',
  withdrawn: 'Withdrawn'
};

export function canTransition(from: ApplicationStatus, to: ApplicationStatus): boolean {
  return TRANSITIONS[from]?.includes(to) ?? false;
}

export function isFinal(status: ApplicationStatus): boolean {
  return TRANSITIONS[status].length === 0;
}

export interface NextAction {
  to: ApplicationStatus;
  label: string;
  /** Officer-facing tone for the button. */
  tone: 'primary' | 'default' | 'danger';
}

/** Opening the interview room is how an application moves to interviewing. */
const ACTION_LABELS: Record<ApplicationStatus, string> = {
  applied: 'Applied',
  interviewing: 'Open interview room',
  trial_offered: 'Offer trial raid',
  accepted: 'Accept',
  declined: 'Decline',
  withdrawn: 'Withdraw'
};

/** Only the applicant withdraws (the API refuses an officer doing it), so officers never get that button. */
export const APPLICANT_ONLY: readonly ApplicationStatus[] = ['withdrawn'];

/** The buttons an officer sees for an application in this status. */
export function nextActions(status: ApplicationStatus): NextAction[] {
  return (TRANSITIONS[status] ?? []).filter((to) => !APPLICANT_ONLY.includes(to)).map((to) => ({
    to,
    label: ACTION_LABELS[to],
    tone: to === 'declined' ? 'danger' : 'primary'
  }));
}
