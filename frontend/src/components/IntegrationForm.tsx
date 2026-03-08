/**
 * IntegrationForm — dynamic form rendered from an IntegrationType manifest.
 *
 * No hardcoded fields per device — all inputs are driven by config_fields
 * from GET /api/v1/integration-types. Adding a new backend integration
 * automatically gives it a correct form here.
 *
 * Props:
 *   type       — the plugin type (supplies config_fields)
 *   initial    — existing config values when editing
 *   onSubmit   — called with { id, name, config } on save
 *   onCancel   — called when the user dismisses the form
 */

import { useState } from "react";
import type { ConfigField, IntegrationType } from "../types";

interface Props {
  type: IntegrationType;
  initialId?: string;
  initialName?: string;
  initialConfig?: Record<string, unknown>;
  onSubmit: (id: string, name: string, config: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}

export default function IntegrationForm({
  type,
  initialId = "",
  initialName = "",
  initialConfig = {},
  onSubmit,
  onCancel,
}: Props) {
  const [id, setId] = useState(initialId);
  const [name, setName] = useState(initialName || type.name);
  const [config, setConfig] = useState<Record<string, unknown>>(() => {
    // Pre-fill defaults from manifest
    const defaults: Record<string, unknown> = {};
    for (const f of type.config_fields) {
      defaults[f.name] = initialConfig[f.name] ?? f.default ?? "";
    }
    return defaults;
  });
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  function setField(name: string, value: unknown) {
    setConfig((c) => ({ ...c, [name]: value }));
    setTestResult(null);
  }

  async function handleTest() {
    // To test we need to first save (or have an existing ID)
    if (!id) { setError("Set an ID first to test the connection."); return; }
    setError(null);
    const res = await fetch(`/api/v1/integrations/${id}/test`, { method: "POST" });
    const data = (await res.json()) as { success: boolean; message: string };
    setTestResult(data);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!id.trim()) { setError("ID is required."); return; }
    setSaving(true);
    try {
      await onSubmit(id.trim(), name.trim() || type.name, config);
    } catch (err: unknown) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
      {/* Integration meta */}
      <div className="flex gap-3">
        <div className="flex-1 flex flex-col gap-1">
          <label className="text-xs text-slate-400">ID (unique, no spaces)</label>
          <input
            value={id}
            onChange={(e) => setId(e.target.value.replace(/\s/g, "_"))}
            placeholder="my_enphase"
            disabled={!!initialId}
            className="bg-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 disabled:opacity-50"
          />
        </div>
        <div className="flex-1 flex flex-col gap-1">
          <label className="text-xs text-slate-400">Display name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={type.name}
            className="bg-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
          />
        </div>
      </div>

      {/* Dynamic config fields */}
      {type.config_fields.map((field) => (
        <FieldInput
          key={field.name}
          field={field}
          value={config[field.name]}
          onChange={(v) => setField(field.name, v)}
        />
      ))}

      {/* Test result */}
      {testResult && (
        <div className={`text-sm px-3 py-2 rounded-lg ${testResult.success ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
          {testResult.success ? "✓ " : "✗ "}{testResult.message}
        </div>
      )}

      {/* Error */}
      {error && <div className="text-sm text-red-400">{error}</div>}

      {/* Actions */}
      <div className="flex gap-2 justify-end">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => void handleTest()}
          className="px-4 py-2 text-sm rounded-lg bg-slate-600 text-slate-200 hover:bg-slate-500"
        >
          Test connection
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Single field renderer
// ---------------------------------------------------------------------------

interface FieldInputProps {
  field: ConfigField;
  value: unknown;
  onChange: (value: unknown) => void;
}

function FieldInput({ field, value, onChange }: FieldInputProps) {
  const baseInput = "bg-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 w-full";

  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-slate-400">
        {field.label}
        {field.required && <span className="text-red-400 ml-1">*</span>}
      </label>

      {field.type === "boolean" ? (
        <button
          type="button"
          onClick={() => onChange(!value)}
          className={`self-start px-3 py-1 rounded-full text-sm font-medium transition-colors ${
            value ? "bg-green-600 text-white" : "bg-slate-600 text-slate-300"
          }`}
        >
          {value ? "Enabled" : "Disabled"}
        </button>
      ) : field.type === "select" ? (
        <select
          value={String(value ?? field.default ?? "")}
          onChange={(e) => onChange(e.target.value)}
          className={baseInput}
        >
          {(field.options ?? []).map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      ) : (
        <input
          type={field.type === "password" ? "password" : field.type === "number" ? "number" : "text"}
          value={String(value ?? "")}
          onChange={(e) =>
            onChange(field.type === "number" ? Number(e.target.value) : e.target.value)
          }
          placeholder={String(field.default ?? "")}
          required={field.required}
          className={baseInput}
        />
      )}

      {field.help_text && (
        <span className="text-xs text-slate-500">{field.help_text}</span>
      )}
    </div>
  );
}
