const OWNER = "fericode24-art";
const REPO = "fericode24-art-super-investor-vnext-codex";
const WORKFLOW = "octa-vnext-refresh.yml";

function env(name) {
  return globalThis.Netlify?.env?.get?.(name) || process.env[name] || "";
}

export function romeTimeParts(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Rome",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(now);
  const get = (type) => parts.find((p) => p.type === type)?.value || "";
  const weekdays = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7 };
  return {
    weekday: weekdays[get("weekday")] || 0,
    hour: Number(get("hour")),
    minute: Number(get("minute")),
  };
}

export async function dispatchWorkflow({ mode = "all", reason = "scheduled" } = {}) {
  const token = env("GITHUB_ACTIONS_TOKEN") || env("GH_WORKFLOW_TOKEN");
  if (!token) {
    return {
      ok: false,
      status: 501,
      body: {
        ok: false,
        error: "missing_github_actions_token",
        reason,
      },
    };
  }

  const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const runApex = mode === "all" || mode === "apex";
  const gh = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "super-investor-vnext-netlify-scheduler",
    },
    body: JSON.stringify({
      ref: "main",
      inputs: {
        force_run: "true",
        run_apex: runApex ? "true" : "false",
      },
    }),
  });

  if (!gh.ok) {
    const detail = await gh.text().catch(() => "");
    return {
      ok: false,
      status: 502,
      body: {
        ok: false,
        error: "github_dispatch_failed",
        github_status: gh.status,
        detail,
        reason,
      },
    };
  }

  return {
    ok: true,
    status: 202,
    body: {
      ok: true,
      mode,
      reason,
      requested_at: new Date().toISOString(),
      workflow: `https://github.com/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}`,
    },
  };
}

export function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}
