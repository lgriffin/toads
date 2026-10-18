<script lang="ts">
  // The hero's backdrop: a twilight pond under distant spires, in the violet and amber of the WoW Forever key art.
  // Purely decorative, so it is hidden from assistive tech. Motion is a slow drift and respects reduced motion.
  const uid = $props.id();
  const pads = [
    { x: 150, y: 420, rx: 64, d: 0 },
    { x: 330, y: 470, rx: 46, d: 1.2 },
    { x: 905, y: 440, rx: 70, d: 0.6 },
    { x: 1070, y: 485, rx: 44, d: 1.8 },
    { x: 600, y: 505, rx: 36, d: 2.4 }
  ];
  const flies = [
    [180, 300], [260, 360], [420, 330], [790, 310], [980, 350], [1090, 290], [700, 390], [60, 360]
  ];
</script>

<svg viewBox="0 0 1200 560" preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="{uid}-sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#14123a" />
      <stop offset="0.45" stop-color="#3a2f86" />
      <stop offset="0.72" stop-color="#8a5aa8" />
      <stop offset="0.86" stop-color="#e49a72" />
      <stop offset="1" stop-color="#f6c98c" />
    </linearGradient>
    <linearGradient id="{uid}-water" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2e5e9a" />
      <stop offset="0.35" stop-color="#14748f" />
      <stop offset="1" stop-color="#0b2748" />
    </linearGradient>
    <linearGradient id="{uid}-far" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#a98ac4" /><stop offset="1" stop-color="#7457a8" />
    </linearGradient>
    <radialGradient id="{uid}-sun" cx="0.5" cy="1" r="0.6">
      <stop offset="0" stop-color="#ffe3a8" stop-opacity="0.9" />
      <stop offset="1" stop-color="#ffe3a8" stop-opacity="0" />
    </radialGradient>
  </defs>

  <rect width="1200" height="560" fill="url(#{uid}-sky)" />
  <ellipse cx="600" cy="316" rx="520" ry="190" fill="url(#{uid}-sun)" />

  <!-- far ridge with a snow-light edge -->
  <path d="M0 330 L80 262 L150 300 L240 212 L330 300 L420 252 L520 318 L610 280 L720 330 L810 240 L900 306 L1000 226 L1100 300 L1200 262 L1200 346 L0 346Z" fill="url(#{uid}-far)" opacity="0.85" />
  <path d="M240 212 L270 246 L248 240 L232 258Z M810 240 L836 268 L816 262 L798 278Z M1000 226 L1024 258 L1006 252 L990 268Z" fill="#f2e6ff" opacity="0.7" />

  <!-- spires on the far shore -->
  <g fill="#4b3a8c" opacity="0.9">
    <path d="M470 346 V260 L478 226 L486 260 V346Z M492 346 V282 L498 252 L504 282 V346Z M452 346 V292 L458 268 L464 292 V346Z" />
    <path d="M700 346 V242 L710 196 L720 242 V346Z M722 346 V270 L729 236 L736 270 V346Z M686 346 V284 L692 262 L698 284 V346Z" />
    <rect x="440" y="320" width="320" height="26" />
  </g>
  <g fill="#ffd9a0" opacity="0.8">
    <rect x="476" y="262" width="3" height="5" /><rect x="707" y="228" width="3" height="5" /><rect x="707" y="248" width="3" height="5" /><rect x="497" y="284" width="3" height="5" />
  </g>

  <!-- the pond -->
  <rect y="346" width="1200" height="214" fill="url(#{uid}-water)" />
  <g stroke="#ffe3b8" stroke-opacity="0.42" stroke-width="1.6" fill="none" class="glints">
    <path d="M520 360 H680" /><path d="M540 372 H660" /><path d="M560 384 H640" /><path d="M360 366 H430" /><path d="M780 364 H850" />
  </g>
  <g fill="none" stroke="#bff6ee" stroke-opacity="0.28" stroke-width="1.4" class="rings">
    <ellipse cx="600" cy="440" rx="120" ry="14" /><ellipse cx="600" cy="440" rx="220" ry="26" /><ellipse cx="600" cy="440" rx="330" ry="38" />
  </g>

  <!-- lily pads -->
  {#each pads as p (p.x)}
    <g class="pad" style="animation-delay:{p.d}s">
      <ellipse cx={p.x} cy={p.y} rx={p.rx} ry={p.rx * 0.2} fill="#2f8a5c" stroke="#0e3b2a" stroke-width="2" />
      <ellipse cx={p.x} cy={p.y - 2} rx={p.rx * 0.8} ry={p.rx * 0.13} fill="#4fb77a" opacity="0.7" />
    </g>
  {/each}

  <!-- reeds, near and dark -->
  <g stroke="#0c1c2e" stroke-width="5" stroke-linecap="round" fill="none">
    <path d="M24 560 Q30 470 12 396" /><path d="M48 560 Q58 480 52 420" /><path d="M72 560 Q70 500 90 448" />
    <path d="M1176 560 Q1170 480 1190 400" /><path d="M1150 560 Q1142 490 1152 430" /><path d="M1126 560 Q1130 510 1110 460" />
  </g>
  <g fill="#0c1c2e">
    <ellipse cx="12" cy="392" rx="6" ry="16" /><ellipse cx="52" cy="414" rx="6" ry="16" /><ellipse cx="1190" cy="396" rx="6" ry="16" /><ellipse cx="1152" cy="424" rx="6" ry="16" />
  </g>

  <g class="flies" fill="#fff0b8">
    {#each flies as f, i (i)}
      <circle cx={f[0]} cy={f[1]} r="2.4" style="animation-delay:{i * 0.7}s" />
    {/each}
  </g>
</svg>

<style>
  svg { display: block; width: 100%; height: 100%; }
  .pad { transform-box: fill-box; transform-origin: center; animation: bob 7s ease-in-out infinite; }
  .rings ellipse { transform-box: fill-box; transform-origin: center; animation: ring 9s ease-out infinite; }
  .rings ellipse:nth-child(2) { animation-delay: 3s; }
  .rings ellipse:nth-child(3) { animation-delay: 6s; }
  .flies circle { animation: blink 4.2s ease-in-out infinite; }
  @keyframes bob { 50% { transform: translateY(4px); } }
  @keyframes ring { 0% { transform: scale(0.5); opacity: 0.9; } 100% { transform: scale(1); opacity: 0; } }
  @keyframes blink { 0%, 100% { opacity: 0.1; } 50% { opacity: 0.95; } }
  @media (prefers-reduced-motion: reduce) {
    .pad, .rings ellipse, .flies circle { animation: none; }
    .flies circle { opacity: 0.6; }
  }
</style>
