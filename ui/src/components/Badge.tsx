export function Badge(props: { kind: "low" | "medium" | "high"; text: string }) {
  const colors: Record<string, { bg: string; bd: string; fg: string }> = {
    high: { bg: "rgba(239,68,68,0.22)", bd: "rgba(239,68,68,0.55)", fg: "#641515" },
    medium: { bg: "rgba(245,158,11,0.20)", bd: "rgba(245,158,11,0.55)", fg: "#604016" },
    low: { bg: "rgba(34,197,94,0.18)", bd: "rgba(34,197,94,0.55)", fg: "#1a572f" }
  };
  const c = colors[props.kind] ?? colors.low;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 10px",
        borderRadius: 999,
        border: `1px solid ${c.bd}`,
        background: c.bg,
        color: c.fg,
        fontSize: 12,
        fontWeight: 900,
        letterSpacing: "0.02em"
      }}
    >
      {props.text}
    </span>
  );
}
