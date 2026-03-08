/**
 * EnergyFlow — SVG energy flow diagram.
 *
 * Nodes: Solar, House, Grid, Car, Heat Pump, Smart Plugs.
 * Animated dashed arrows show power direction and magnitude.
 * Green = solar energy, orange = grid import.
 */

import type { DeviceReading } from "../types";

interface Props {
  devices: DeviceReading[];
  chargingPowerW: number;
}

interface FlowArrow {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  watts: number;
  color: string;
  label: string;
}

// Node positions in the SVG (viewBox 0 0 500 340)
const NODES = {
  solar:    { x: 250, y: 40,  label: "☀️ Solar" },
  house:    { x: 250, y: 170, label: "🏠 Home" },
  grid:     { x: 60,  y: 170, label: "⚡ Grid" },
  car:      { x: 440, y: 170, label: "🚗 EV" },
  heatpump: { x: 250, y: 300, label: "🌡️ Heat pump" },
  plugs:    { x: 440, y: 300, label: "🔌 Plugs" },
};

function fmt(w: number): string {
  if (Math.abs(w) >= 1000) return `${(w / 1000).toFixed(1)} kW`;
  return `${Math.round(w)} W`;
}

function strokeWidth(w: number): number {
  const clamped = Math.min(Math.abs(w), 6000);
  return 2 + (clamped / 6000) * 6;
}

export default function EnergyFlow({ devices, chargingPowerW }: Props) {
  // Extract power values from device readings
  const solar = devices.find((d) => d.category === "solar");
  const grid = devices.find((d) => d.category === "grid");
  const heatpump = devices.find((d) => d.category === "heat_pump");
  const plugs = devices.filter((d) => d.category === "smart_plug");

  const solarW = solar?.readings?.power_w ?? 0;
  const gridW = grid?.readings?.power_w ?? 0;   // positive = import, negative = export
  const heatpumpW = heatpump?.readings?.input_power_w ?? 0;
  const plugsW = plugs.reduce((sum, p) => sum + (p.readings?.power_w ?? 0), 0);

  // House consumption = solar + grid_import - grid_export - charger - heatpump - plugs
  // Simplified: total load minus known sub-loads
  const houseW = Math.max(
    0,
    solarW + Math.max(0, gridW) - chargingPowerW - heatpumpW - plugsW
  );

  const arrows: FlowArrow[] = [];

  // Solar → House
  if (solarW > 10) {
    arrows.push({
      id: "solar-house",
      x1: NODES.solar.x, y1: NODES.solar.y + 18,
      x2: NODES.house.x, y2: NODES.house.y - 18,
      watts: solarW,
      color: "#22c55e",
      label: fmt(solarW),
    });
  }

  // Grid → House (import) or House → Grid (export)
  if (Math.abs(gridW) > 10) {
    const importing = gridW > 0;
    arrows.push({
      id: "grid-house",
      x1: importing ? NODES.grid.x + 20 : NODES.house.x - 20,
      y1: NODES.grid.y,
      x2: importing ? NODES.house.x - 20 : NODES.grid.x + 20,
      y2: NODES.house.y,
      watts: Math.abs(gridW),
      color: importing ? "#f97316" : "#22c55e",
      label: fmt(Math.abs(gridW)),
    });
  }

  // House → Car
  if (chargingPowerW > 10) {
    arrows.push({
      id: "house-car",
      x1: NODES.house.x + 20, y1: NODES.house.y,
      x2: NODES.car.x - 20,   y2: NODES.car.y,
      watts: chargingPowerW,
      color: "#22c55e",
      label: fmt(chargingPowerW),
    });
  }

  // House → Heat pump
  if (heatpumpW > 10) {
    arrows.push({
      id: "house-heatpump",
      x1: NODES.house.x, y1: NODES.house.y + 18,
      x2: NODES.heatpump.x, y2: NODES.heatpump.y - 14,
      watts: heatpumpW,
      color: "#22c55e",
      label: fmt(heatpumpW),
    });
  }

  // House → Plugs
  if (plugsW > 10) {
    arrows.push({
      id: "house-plugs",
      x1: NODES.house.x + 20, y1: NODES.house.y + 10,
      x2: NODES.plugs.x - 20, y2: NODES.plugs.y - 10,
      watts: plugsW,
      color: "#22c55e",
      label: fmt(plugsW),
    });
  }

  return (
    <svg
      viewBox="0 0 500 370"
      className="w-full max-w-lg mx-auto"
      aria-label="Energy flow diagram"
    >
      <defs>
        <marker id="arrow-green" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#22c55e" />
        </marker>
        <marker id="arrow-orange" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L0,6 L8,3 z" fill="#f97316" />
        </marker>
        <style>{`
          .flow-dash { stroke-dasharray: 8 4; animation: dash 1s linear infinite; }
          @keyframes dash { to { stroke-dashoffset: -24; } }
        `}</style>
      </defs>

      {/* Arrows */}
      {arrows.map((a) => (
        <g key={a.id}>
          <line
            x1={a.x1} y1={a.y1} x2={a.x2} y2={a.y2}
            stroke={a.color}
            strokeWidth={strokeWidth(a.watts)}
            strokeLinecap="round"
            className="flow-dash"
            markerEnd={`url(#arrow-${a.color === "#22c55e" ? "green" : "orange"})`}
          />
          <text
            x={(a.x1 + a.x2) / 2}
            y={(a.y1 + a.y2) / 2 - 6}
            textAnchor="middle"
            fontSize="11"
            fill={a.color}
            fontWeight="600"
          >
            {a.label}
          </text>
        </g>
      ))}

      {/* Nodes */}
      {Object.entries(NODES).map(([key, node]) => {
        const isActive = (() => {
          if (key === "solar") return solarW > 10;
          if (key === "grid") return Math.abs(gridW) > 10;
          if (key === "car") return chargingPowerW > 10;
          if (key === "heatpump") return heatpumpW > 10;
          if (key === "plugs") return plugsW > 10;
          return true; // house always shown
        })();

        return (
          <g key={key}>
            <circle
              cx={node.x} cy={node.y} r={28}
              fill={isActive ? "#1e293b" : "#0f172a"}
              stroke={isActive ? "#334155" : "#1e293b"}
              strokeWidth="2"
            />
            <text x={node.x} y={node.y + 4} textAnchor="middle" fontSize="18">
              {node.label.split(" ")[0]}
            </text>
            <text
              x={node.x} y={node.y + 44}
              textAnchor="middle" fontSize="10"
              fill={isActive ? "#94a3b8" : "#475569"}
            >
              {node.label.split(" ").slice(1).join(" ")}
            </text>
            {key === "house" && houseW > 0 && (
              <text x={node.x} y={node.y + 56} textAnchor="middle" fontSize="10" fill="#64748b">
                {fmt(houseW)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
