export function Button({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{ padding: "10px 14px", borderRadius: 8 }}>
      {label}
    </button>
  );
}
