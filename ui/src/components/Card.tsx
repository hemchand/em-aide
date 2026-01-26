import React from "react";

export function Card(props: { title: string; right?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <div className={`card ${props.className ?? ""}`.trim()}>
      <div className="card-head">
        <div className="card-title">{props.title}</div>
        {props.right}
      </div>
      <div style={{ marginTop: 12 }}>{props.children}</div>
    </div>
  );
}
