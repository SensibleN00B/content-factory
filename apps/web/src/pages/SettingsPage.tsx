import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getProfile, saveProfile, type ProfilePayload } from "../lib/api";

type LoadState = "loading" | "ready" | "error";
type SaveState = "idle" | "saving" | "saved" | "error";

type FormState = {
  niche: string;
  icp: string;
  regions: string;
  language: string;
  seeds: string;
  negatives: string;
  contentTypes: string;
};

const DEFAULT_PROFILE: ProfilePayload = {
  niche: ["AI", "automation"],
  icp: ["business owners", "CEO", "CTO"],
  regions: ["US", "CA", "EU"],
  language: "en",
  seeds: ["ai agent", "voice ai", "ai receptionist", "startup automation", "ai workflow"],
  negatives: ["crypto", "politics", "gaming", "anime"],
  settings: {
    content_types: ["linkedin", "x", "short_video", "carousel"],
  },
};

function toTextarea(values: string[]): string {
  return values.join("\n");
}

function fromTextarea(value: string): string[] {
  return value
    .split(/[\n,]/g)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildFormState(payload: ProfilePayload): FormState {
  const rawContentTypes = payload.settings["content_types"];
  const contentTypes = Array.isArray(rawContentTypes)
    ? rawContentTypes.filter((item): item is string => typeof item === "string")
    : [];

  return {
    niche: toTextarea(payload.niche),
    icp: toTextarea(payload.icp),
    regions: toTextarea(payload.regions),
    language: payload.language,
    seeds: toTextarea(payload.seeds),
    negatives: toTextarea(payload.negatives),
    contentTypes: toTextarea(contentTypes),
  };
}

function formStateToPayload(formState: FormState): ProfilePayload {
  return {
    niche: fromTextarea(formState.niche),
    icp: fromTextarea(formState.icp),
    regions: fromTextarea(formState.regions),
    language: formState.language.trim() || "en",
    seeds: fromTextarea(formState.seeds),
    negatives: fromTextarea(formState.negatives),
    settings: {
      content_types: fromTextarea(formState.contentTypes),
    },
  };
}

export function SettingsPage() {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [formState, setFormState] = useState<FormState>(buildFormState(DEFAULT_PROFILE));

  useEffect(() => {
    let active = true;

    getProfile()
      .then((profile) => {
        if (!active) {
          return;
        }
        const payload: ProfilePayload = profile ?? DEFAULT_PROFILE;
        setFormState(buildFormState(payload));
        setLoadState("ready");
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        const message =
          error instanceof Error ? error.message : "Unexpected error while loading profile";
        setErrorMessage(message);
        setLoadState("error");
      });

    return () => {
      active = false;
    };
  }, []);

  const canSubmit = useMemo(() => loadState === "ready" && saveState !== "saving", [loadState, saveState]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaveState("saving");
    setErrorMessage("");

    try {
      const payload = formStateToPayload(formState);
      const saved = await saveProfile(payload);
      setFormState(buildFormState(saved));
      setSaveState("saved");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to save profile";
      setErrorMessage(message);
      setSaveState("error");
    }
  }

  function onChange(field: keyof FormState, value: string) {
    setFormState((current) => ({ ...current, [field]: value }));
    if (saveState === "saved" || saveState === "error") {
      setSaveState("idle");
    }
  }

  if (loadState === "loading") {
    return (
      <main className="page">
        <section className="panel">
          <p className="muted">Loading profile settings...</p>
        </section>
      </main>
    );
  }

  if (loadState === "error") {
    return (
      <main className="page">
        <section className="panel">
          <h1>Settings</h1>
          <p className="error">Cannot load profile: {errorMessage}</p>
          <Link to="/" className="ghost-link">
            Back to dashboard
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      <section className="panel settings-panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Profile Settings</p>
            <h1>Discovery Inputs</h1>
          </div>
          <div className="panel-links">
            <Link to="/" className="ghost-link">
              Dashboard
            </Link>
            <Link to="/runs" className="ghost-link">
              Run console
            </Link>
            <Link to="/shortlist" className="ghost-link">
              Shortlist
            </Link>
          </div>
        </div>

        <form className="settings-form" onSubmit={onSubmit}>
          <label>
            Niche
            <textarea
              value={formState.niche}
              onChange={(event) => onChange("niche", event.target.value)}
              rows={3}
            />
          </label>

          <label>
            ICP
            <textarea
              value={formState.icp}
              onChange={(event) => onChange("icp", event.target.value)}
              rows={3}
            />
          </label>

          <label>
            Regions
            <textarea
              value={formState.regions}
              onChange={(event) => onChange("regions", event.target.value)}
              rows={2}
            />
          </label>

          <label>
            Language
            <input
              value={formState.language}
              onChange={(event) => onChange("language", event.target.value)}
              placeholder="en"
            />
          </label>

          <label>
            Seed Keywords
            <textarea
              value={formState.seeds}
              onChange={(event) => onChange("seeds", event.target.value)}
              rows={5}
            />
          </label>

          <label>
            Negative Keywords
            <textarea
              value={formState.negatives}
              onChange={(event) => onChange("negatives", event.target.value)}
              rows={4}
            />
          </label>

          <label>
            Preferred Content Types
            <textarea
              value={formState.contentTypes}
              onChange={(event) => onChange("contentTypes", event.target.value)}
              rows={3}
            />
          </label>

          <div className="settings-actions">
            <button type="submit" disabled={!canSubmit}>
              {saveState === "saving" ? "Saving..." : "Save settings"}
            </button>
            {saveState === "saved" && <p className="ok">Saved.</p>}
            {saveState === "error" && <p className="error">Save failed: {errorMessage}</p>}
          </div>
        </form>
      </section>
    </main>
  );
}
