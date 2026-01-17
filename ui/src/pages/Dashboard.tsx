import { Button } from "../components/Button";

export default function Dashboard() {
  return (
    <div className="container">
      <h1>EM-Aide</h1>
      <p>React UI is connected.</p>
      <Button label="Run Weekly Plan" onClick={() => alert("Hook to backend")} />
    </div>
  );
}
