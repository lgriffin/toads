<script lang="ts">
  import type { Post } from '$lib/community';
  import { shortDate } from '$lib/format';

  interface Props {
    post: Post;
    /** Show origin, pinned and raid-day badges (the member hub). */
    badges?: boolean;
    headingLevel?: 2 | 3 | 4;
  }
  let { post, badges = false, headingLevel = 3 }: Props = $props();
</script>

<article class="post" class:pinned={post.pinned}>
  <svelte:element this={`h${headingLevel}`} class="title">{post.title}</svelte:element>
  {#if badges}
    <p class="badges">
      {#if post.pinned}<span class="pill pin">Pinned</span>{/if}
      <span class="pill">{post.origin === 'discord' ? 'from Discord' : 'Hub'}</span>
      {#if post.visibility === 'raid_day' && post.raidDay}<span class="pill day">{post.raidDay} raid</span>{/if}
      {#if post.visibility === 'public'}<span class="pill">Public</span>{/if}
    </p>
  {/if}
  <!-- Plain text only: newlines are preserved by CSS, never rendered as HTML. -->
  <p class="body">{post.body}</p>
  <p class="muted small">{post.authorName} · {shortDate(post.publishedAt ?? post.createdAt)}</p>
</article>

<style>
  .post { padding: 0.75rem 0; border-top: 1px solid var(--line); min-width: 0; }
  .post:first-of-type { border-top: 0; padding-top: 0; }
  .title { font-size: 1rem; margin: 0 0 0.35rem; }
  .badges { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0 0 0.4rem; }
  .pin { background: var(--accent); color: #0f1411; }
  .day { background: #3b3320; color: var(--warn); }
  .body { white-space: pre-line; overflow-wrap: anywhere; margin: 0 0 0.35rem; }
  .small { font-size: 0.8rem; margin: 0; }
</style>
