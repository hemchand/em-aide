export function Button(props: {
  label: string;
  onClick: () => void;
  kind?: "primary" | "secondary";
  tone?: "blue" | "green" | "amber" | "teal" | "violet";
  disabled?: boolean;
}) {
  const primary = props.kind !== "secondary";
  const tones = {
    blue: {
      solid: "#2563eb",
      softBg: "rgba(37, 99, 235, 0.12)",
      softBorder: "rgba(37, 99, 235, 0.35)",
      softText: "#1e3a8a",
    },
    green: {
      solid: "#16a34a",
      softBg: "rgba(22, 163, 74, 0.12)",
      softBorder: "rgba(22, 163, 74, 0.35)",
      softText: "#14532d",
    },
    amber: {
      solid: "#f59e0b",
      softBg: "rgba(245, 158, 11, 0.14)",
      softBorder: "rgba(245, 158, 11, 0.38)",
      softText: "#7c4a03",
    },
    teal: {
      solid: "#14b8a6",
      softBg: "rgba(20, 184, 166, 0.14)",
      softBorder: "rgba(20, 184, 166, 0.38)",
      softText: "#0f766e",
    },
    violet: {
      solid: "#7c3aed",
      softBg: "rgba(124, 58, 237, 0.14)",
      softBorder: "rgba(124, 58, 237, 0.38)",
      softText: "#4c1d95",
    },
  } as const;
  const tone = props.tone ? tones[props.tone] : null;
  const background = tone
    ? (primary ? tone.solid : tone.softBg)
    : (primary ? "rgba(18,24,38,0.92)" : "rgba(18,24,38,0.06)");
  const border = tone
    ? `1px solid ${primary ? tone.solid : tone.softBorder}`
    : `1px solid ${primary ? "rgba(18,24,38,0.12)" : "rgba(18,24,38,0.16)"}`;
  const color = tone
    ? (primary ? "#ffffff" : tone.softText)
    : (primary ? "#f8fafc" : "rgba(18,24,38,0.9)");
  return (
    <button
      disabled={props.disabled}
      onClick={props.onClick}
      style={{
        padding: "10px 12px",
        borderRadius: 12,
        border,
        background,
        color,
        cursor: props.disabled ? "not-allowed" : "pointer",
        fontWeight: 800,
        opacity: props.disabled ? 0.6 : 1,
      }}
    >
      {props.label}
    </button>
  );
}
