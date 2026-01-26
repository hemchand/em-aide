export function Button(props: {
  label: string;
  onClick: () => void;
  kind?: "primary" | "secondary";
  disabled?: boolean;
}) {
  const primary = props.kind !== "secondary";
  return (
    <button
      disabled={props.disabled}
      onClick={props.onClick}
      style={{
        padding: "10px 12px",
        borderRadius: 12,
        border: primary ? "1px solid rgba(18,24,38,0.12)" : "1px solid rgba(18,24,38,0.16)",
        background: primary ? "rgba(18,24,38,0.92)" : "rgba(18,24,38,0.06)",
        color: primary ? "#f8fafc" : "rgba(18,24,38,0.9)",
        cursor: props.disabled ? "not-allowed" : "pointer",
        fontWeight: 800
      }}
    >
      {props.label}
    </button>
  );
}
