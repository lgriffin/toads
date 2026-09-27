/**
 * Preview-only mutable copies of the community sample data. Officer and consent actions in the static preview change
 * these in memory (shared across client-side navigation, reset on reload); nothing is sent anywhere.
 */
import type { Application, Highlight, Post, Spotlight } from '$lib/community';
import { defaultLayout, type HomeLayout } from '$lib/home';
import { applications, highlights, posts, spotlights } from '$lib/mock/community';

export const community = $state<{
  applications: Application[];
  posts: Post[];
  highlights: Highlight[];
  spotlights: Spotlight[];
}>({
  applications: structuredClone(applications),
  posts: structuredClone(posts),
  highlights: structuredClone(highlights),
  spotlights: structuredClone(spotlights)
});

/** The preview visitor's hub home layout. Hopscotch is an officer, so the desk is placeable. */
export const home = $state<{ layout: HomeLayout }>({ layout: defaultLayout(true) });
