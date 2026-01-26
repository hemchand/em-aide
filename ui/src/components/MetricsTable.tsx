import type { Metric } from "../types";
import { metricLabel } from "../metrics";

export function MetricsTable(props: { metrics: Metric[] }) {
  if (!props.metrics.length) {
    return <div className="muted">No metrics yet. Click <code>Snapshot metrics</code>.</div>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Value</th>
          <th>As of</th>
        </tr>
      </thead>
      <tbody>
        {props.metrics.map((m, i) => (
          <tr key={i}>
            <td>{metricLabel(m.name)}</td>
            <td>{Number.isFinite(m.value) ? m.value.toFixed(3) : String(m.value)}</td>
            <td>{m.as_of_date}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
