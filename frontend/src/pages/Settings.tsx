/**
 * Settings page — dynamic integration management.
 *
 * - Lists configured integrations with live status dots
 * - "Add integration" flow: pick type → fill dynamic form → test → save
 * - Edit / delete existing integrations
 */

import { useEffect, useState } from "react";
import IntegrationForm from "../components/IntegrationForm";
import type { IntegrationInstance, IntegrationType } from "../types";

// ---------------------------------------------------------------------------
// Data fetching helpers
// ---------------------------------------------------------------------------

async function fetchTypes(): Promise<IntegrationType[]> {
  const res = await fetch("/api/v1/integration-types");
  return res.json() as Promise<IntegrationType[]>;
}

async function fetchInstances(): Promise<IntegrationInstance[]> {
  const res = await fetch("/api/v1/integrations");
  return res.json() as Promise<IntegrationInstance[]>;
}

async function deleteInstance(id: string): Promise<void> {
  await fetch(`/api/v1/integrations/${id}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Settings() {
  const [types, setTypes] = useState<IntegrationType[]>([]);
  const [instances, setInstances] = useState<IntegrationInstance[]>([]);
  const [loading, setLoading] = useState(true);

  // "add" flow
  const [addingTypeId, setAddingTypeId] = useState<string | null>(null);
  // "edit" flow
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([fetchTypes(), fetchInstances()]).then(([t, i]) => {
      setTypes(t);
      setInstances(i);
      setLoading(false);
    });
  }, []);

  async function refresh() {
    setInstances(await fetchInstances());
  }

  async function handleSaveNew(id: string, name: string, config: Record<string, unknown>) {
    await fetch("/api/v1/integrations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, type_id: addingTypeId, name, config }),
    });
    setAddingTypeId(null);
    await refresh();
  }

  async function handleSaveEdit(id: string, name: string, config: Record<string, unknown>) {
    await fetch(`/api/v1/integrations/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, config }),
    });
    setEditingId(null);
    await refresh();
  }

  async function handleDelete(id: string) {
    if (!confirm(`Remove integration "${id}"?`)) return;
    await deleteInstance(id);
    await refresh();
  }

  const addingType = types.find((t) => t.id === addingTypeId) ?? null;
  const editingInstance = instances.find((i) => i.id === editingId) ?? null;
  const editingType = editingInstance
    ? (types.find((t) => t.id === editingInstance.type_id) ?? null)
    : null;

  if (loading) {
    return <div className="text-slate-400">Loading…</div>;
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl mx-auto">
      <h1 className="text-xl font-bold text-white">Settings</h1>

      {/* Add integration modal */}
      {addingType && (
        <Modal title={`Add ${addingType.name}`} onClose={() => setAddingTypeId(null)}>
          <IntegrationForm
            type={addingType}
            onSubmit={handleSaveNew}
            onCancel={() => setAddingTypeId(null)}
          />
        </Modal>
      )}

      {/* Edit integration modal */}
      {editingType && editingInstance && (
        <Modal title={`Edit ${editingInstance.name}`} onClose={() => setEditingId(null)}>
          <IntegrationForm
            type={editingType}
            initialId={editingInstance.id}
            initialName={editingInstance.name}
            onSubmit={handleSaveEdit}
            onCancel={() => setEditingId(null)}
          />
        </Modal>
      )}

      {/* Configured integrations */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
            Integrations
          </h2>
          <TypePicker types={types} onPick={setAddingTypeId} />
        </div>

        {instances.length === 0 ? (
          <div className="text-slate-500 text-sm py-6 text-center">
            No integrations configured yet.
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {instances.map((inst) => {
              const type = types.find((t) => t.id === inst.type_id);
              return (
                <div
                  key={inst.id}
                  className="bg-slate-800 rounded-xl px-4 py-3 flex items-center gap-3"
                >
                  <span className="text-xl">{type?.icon ?? "📟"}</span>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-100 truncate">{inst.name}</div>
                    <div className="text-xs text-slate-500">{inst.type_id}</div>
                  </div>

                  {/* Status dot */}
                  <span
                    className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                      inst.last_error
                        ? "bg-red-500"
                        : inst.last_seen
                        ? "bg-green-500"
                        : "bg-slate-500"
                    }`}
                    title={inst.last_error ?? (inst.last_seen ? "OK" : "Never polled")}
                  />

                  <button
                    onClick={() => setEditingId(inst.id)}
                    className="text-slate-400 hover:text-white text-sm px-2"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => void handleDelete(inst.id)}
                    className="text-red-400 hover:text-red-300 text-sm px-2"
                  >
                    Remove
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TypePicker({
  types,
  onPick,
}: {
  types: IntegrationType[];
  onPick: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-sm px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg"
      >
        + Add integration
      </button>
    );
  }

  return (
    <div className="relative">
      <div className="absolute right-0 top-8 z-10 bg-slate-700 rounded-xl shadow-xl w-64 py-1">
        {types.map((t) => (
          <button
            key={t.id}
            onClick={() => { onPick(t.id); setOpen(false); }}
            className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-600 text-left"
          >
            <span>{t.icon}</span>
            <div>
              <div className="text-sm text-slate-100">{t.name}</div>
              <div className="text-xs text-slate-400">{t.category}</div>
            </div>
          </button>
        ))}
        <button
          onClick={() => setOpen(false)}
          className="w-full text-xs text-slate-500 py-2 hover:text-slate-400"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="bg-slate-800 rounded-2xl w-full max-w-lg p-6 flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-white">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
