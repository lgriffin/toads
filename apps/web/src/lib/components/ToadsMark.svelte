<script lang="ts">
  // The Toads medallion: a bronze ring and a teal disc with a toad on its lily pad, drawn to sit beside the World of
  // Warcraft: Forever badge without copying it. Toads, never frogs: wide mouth, warty brow, glands behind the eyes.
  let { size = 120, title = '' }: { size?: number; title?: string } = $props();
  const uid = $props.id();
  const ticks = Array.from({ length: 24 }, (_, i) => i * 15);
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 200 200"
  role={title ? 'img' : undefined}
  aria-label={title || undefined}
  aria-hidden={title ? undefined : 'true'}
  focusable="false"
>
  <defs>
    <linearGradient id="{uid}-bronze" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f4d894" />
      <stop offset="0.45" stop-color="#c58f45" />
      <stop offset="1" stop-color="#7a4f23" />
    </linearGradient>
    <radialGradient id="{uid}-teal" cx="0.5" cy="0.42" r="0.62">
      <stop offset="0" stop-color="#5fe6d6" />
      <stop offset="0.55" stop-color="#139aa4" />
      <stop offset="1" stop-color="#0a3d63" />
    </radialGradient>
    <linearGradient id="{uid}-skin" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e4d29a" />
      <stop offset="1" stop-color="#a99a5c" />
    </linearGradient>
    <clipPath id="{uid}-disc"><circle cx="100" cy="100" r="74" /></clipPath>
  </defs>

  <circle cx="100" cy="100" r="97" fill="url(#{uid}-bronze)" />
  <circle cx="100" cy="100" r="97" fill="none" stroke="#4a2f14" stroke-width="1.5" />
  {#each ticks as a (a)}
    <rect x="98" y="5" width="4" height="9" rx="1.5" fill="#4a2f14" opacity="0.55" transform="rotate({a} 100 100)" />
  {/each}
  <circle cx="100" cy="100" r="82" fill="#3a2410" />
  <circle cx="100" cy="100" r="79" fill="url(#{uid}-bronze)" />
  <circle cx="100" cy="100" r="74" fill="url(#{uid}-teal)" />

  <g clip-path="url(#{uid}-disc)">
    <!-- the pond: ripples and a lily pad under the toad -->
    <ellipse cx="100" cy="158" rx="70" ry="13" fill="none" stroke="#bff6ee" stroke-opacity="0.35" stroke-width="1.2" />
    <ellipse cx="100" cy="158" rx="50" ry="9" fill="none" stroke="#bff6ee" stroke-opacity="0.5" stroke-width="1.2" />
    <path d="M52 150 Q100 134 148 150 Q142 172 100 174 Q58 172 52 150Z" fill="#3f9a63" stroke="#14452f" stroke-width="2" />
    <path d="M100 152 L100 174" stroke="#14452f" stroke-width="1.6" opacity="0.6" />

    <!-- the toad, seen from the front -->
    <path
      d="M54 128 Q50 100 78 98 L122 98 Q150 100 146 128 Q142 152 100 154 Q58 152 54 128Z"
      fill="url(#{uid}-skin)"
      stroke="#12303f"
      stroke-width="3"
      stroke-linejoin="round"
    />
    <ellipse cx="62" cy="104" rx="14" ry="7.5" transform="rotate(-24 62 104)" fill="#8b7a45" stroke="#12303f" stroke-width="2.4" />
    <ellipse cx="138" cy="104" rx="14" ry="7.5" transform="rotate(24 138 104)" fill="#8b7a45" stroke="#12303f" stroke-width="2.4" />
    <circle cx="76" cy="90" r="16" fill="url(#{uid}-skin)" stroke="#12303f" stroke-width="3" />
    <circle cx="124" cy="90" r="16" fill="url(#{uid}-skin)" stroke="#12303f" stroke-width="3" />
    <circle cx="76" cy="90" r="9" fill="#e7a73c" stroke="#12303f" stroke-width="2" />
    <circle cx="124" cy="90" r="9" fill="#e7a73c" stroke="#12303f" stroke-width="2" />
    <ellipse cx="76" cy="90" rx="7" ry="3" fill="#12303f" />
    <ellipse cx="124" cy="90" rx="7" ry="3" fill="#12303f" />
    <circle cx="94" cy="108" r="1.8" fill="#12303f" />
    <circle cx="106" cy="108" r="1.8" fill="#12303f" />
    <path d="M62 124 Q100 148 138 124" fill="none" stroke="#12303f" stroke-width="3.2" stroke-linecap="round" />
    <path d="M66 126 Q64 132 68 135 M134 126 Q136 132 132 135" fill="none" stroke="#12303f" stroke-width="2.4" stroke-linecap="round" />
    <g fill="#7d6e3c" stroke="#12303f" stroke-width="1" opacity="0.95">
      <circle cx="82" cy="115" r="3.4" /><circle cx="100" cy="120" r="3" /><circle cx="118" cy="115" r="3.4" />
      <circle cx="70" cy="131" r="3.2" /><circle cx="130" cy="131" r="3.2" /><circle cx="100" cy="141" r="3.6" />
      <circle cx="86" cy="132" r="2.6" /><circle cx="114" cy="132" r="2.6" /><circle cx="58" cy="118" r="2.6" /><circle cx="142" cy="118" r="2.6" />
    </g>
  </g>
</svg>
