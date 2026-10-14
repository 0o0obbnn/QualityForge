/**
 * 原型 SVG 图标集（与 deliverables/2026-08-12/prototype 各页内联 SVG 一致）。
 * 全部 stroke="currentColor"，继承文字颜色，尺寸由调用方指定。
 */

interface IconProps {
  size?: number;
}

function svgProps(size: number) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 16 16",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    "aria-hidden": true,
  } as const;
}

export function IconBoard({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <rect x="2" y="2.5" width="12" height="11" rx="2" />
      <path d="M2 6h12M5.5 9h2M5.5 11.5h4" />
    </svg>
  );
}

export function IconKnowledge({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <circle cx="8" cy="8" r="5.5" />
      <path d="M8 5v3l2 1.5" />
    </svg>
  );
}

export function IconPlanning({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="M3 4h10M3 8h10M3 12h6" />
      <circle cx="13" cy="12" r="1.6" />
    </svg>
  );
}

export function IconAutomation({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="M4 12.5V3.5h8v9H4Z" />
      <path d="M6 6h4M6 8.5h4" />
    </svg>
  );
}

export function IconExecution({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="M2.5 13.5h11M4 13.5V8l4-3 4 3v5.5" />
    </svg>
  );
}

export function IconQuality({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="M8 2.5 13.5 13.5h-11L8 2.5Z" />
      <path d="M8 7v3M8 12.2v.3" />
    </svg>
  );
}

export function IconAgent({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <circle cx="8" cy="8" r="2.4" />
      <path d="M8 2.8v2M8 11.2v2M2.8 8h2M11.2 8h2" />
    </svg>
  );
}

export function IconPlatform({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <circle cx="8" cy="8" r="2" />
      <path d="M8 1.8v2M8 12.2v2M1.8 8h2M12.2 8h2" />
    </svg>
  );
}

export function IconHome({ size = 14 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="M2 5.5 8 2l6 3.5v8h-4.5V10h-3v3.5H2v-8Z" />
    </svg>
  );
}

export function IconBell({ size = 16 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="M8 2.5a4 4 0 0 1 4 4v3l1.5 2h-11L4 9.5v-3a4 4 0 0 1 4-4Z" />
      <path d="M6.5 13a1.6 1.6 0 0 0 3 0" />
    </svg>
  );
}

export function IconAvatar({ size = 16, strokeWidth = 1.5 }: IconProps & { strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={strokeWidth} width={size} height={size} aria-hidden>
      <circle cx="8" cy="5.6" r="2.6" />
      <path d="M3.5 13.5c.6-2.4 2.4-3.6 4.5-3.6s3.9 1.2 4.5 3.6" />
    </svg>
  );
}

export function IconSearch({ size = 14 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <circle cx="7" cy="7" r="4.5" />
      <path d="m10.5 10.5 3 3" />
    </svg>
  );
}

export function IconChevronDown({ size = 10 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="m4 6 4 4 4-4" />
    </svg>
  );
}

export function IconClose({ size = 14, strokeWidth = 1.8 }: IconProps & { strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={strokeWidth} width={size} height={size} aria-hidden>
      <path d="m4 4 8 8M12 4l-8 8" />
    </svg>
  );
}

export function IconCheck({ size = 14, strokeWidth = 2 }: IconProps & { strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={strokeWidth} width={size} height={size} aria-hidden>
      <path d="m3 8.5 3 3 7-7" />
    </svg>
  );
}

export function IconCheckSmall({ size = 11, strokeWidth = 2.4 }: IconProps & { strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={strokeWidth} width={size} height={size} aria-hidden>
      <path d="m3 8.5 3 3 7-7" />
    </svg>
  );
}

export function IconWarn({ size = 14, strokeWidth = 1.6 }: IconProps & { strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={strokeWidth} width={size} height={size} aria-hidden>
      <path d="M8 2.5 13.5 13.5h-11L8 2.5Z" />
      <path d="M8 7v3M8 12.2v.3" />
    </svg>
  );
}

export function IconPlus({ size = 14, strokeWidth = 1.8 }: IconProps & { strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={strokeWidth} width={size} height={size} aria-hidden>
      <path d="M8 3v10M3 8h10" />
    </svg>
  );
}

export function IconHamburger({ size = 18 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="M2 4h12M2 8h12M2 12h12" />
    </svg>
  );
}

export function IconTrace({ size = 13 }: IconProps) {
  return (
    <svg {...svgProps(size)}>
      <path d="M8 2.8v2M8 11.2v2M2.8 8h2M11.2 8h2" />
    </svg>
  );
}

export function IconMark() {
  return (
    <svg viewBox="0 0 16 16" width="15" height="15" fill="none" aria-hidden>
      <path d="M3 12.5 8 3l5 9.5H3Z" stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}
