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
        border: "1px solid rgba(255,255,255,0.12)",
        background: primary ? "rgba(255,255,255,0.92)" : "rgba(255,255,255,0.06)",
        color: primary ? "#0b1020" : "rgba(255,255,255,0.92)",
        cursor: props.disabled ? "not-allowed" : "pointer",
        fontWeight: 800
      }}
    >
      {props.label}
    </button>
  );
}
