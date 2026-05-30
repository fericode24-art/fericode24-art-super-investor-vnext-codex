import { dispatchWorkflow, jsonResponse, romeTimeParts } from "./_shared/dispatch-workflow.mjs";

const ALLOWED = new Set(["8:35", "8:45", "8:55", "9:10", "9:30"]);

export default async () => {
  const rome = romeTimeParts();
  const key = `${rome.hour}:${String(rome.minute).padStart(2, "0")}`;
  const shouldRun = rome.weekday >= 1 && rome.weekday <= 5 && ALLOWED.has(key);

  if (!shouldRun) {
    return jsonResponse({ ok: true, skipped: true, reason: "outside_octa_window", rome });
  }

  const result = await dispatchWorkflow({ mode: "octa", reason: "netlify_schedule_octa" });
  return jsonResponse(result.body, result.status);
};

export const config = {
  schedule: "10,30,35,45,55 6,7,8 * * 1-5",
};
