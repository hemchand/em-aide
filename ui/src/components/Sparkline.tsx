export function Sparkline(props: { values: number[]; color: string }) {
  const values = props.values.filter((v) => Number.isFinite(v));
  if (!values.length) return <div className="spark-empty">No data</div>;

  const width = 160;
  const height = 42;
  const padding = 6;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;

  const points = values.map((v, i) => {
    const x = padding + (i * (width - padding * 2)) / Math.max(values.length - 1, 1);
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");

  const lastX = padding + ((values.length - 1) * (width - padding * 2)) / Math.max(values.length - 1, 1);
  const lastY = height - padding - ((values[values.length - 1] - min) / range) * (height - padding * 2);

  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`}>
      <polyline
        fill="none"
        stroke={props.color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
      <circle cx={lastX} cy={lastY} r="3.5" fill={props.color} />
    </svg>
  );
}
