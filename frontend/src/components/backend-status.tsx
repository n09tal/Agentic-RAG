"use client";

import { useEffect, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type Status = "checking" | "ready" | "not_ready" | "offline";

const MESSAGES: Record<Status, string> = {
  checking: "Checking backend…",
  ready: "Backend is ready. Database connected.",
  not_ready: "Backend is running, but the database is unreachable.",
  offline: `Cannot reach the backend at ${API_BASE_URL}.`,
};

const COLORS: Record<Status, string> = {
  checking: "bg-zinc-400",
  ready: "bg-green-500",
  not_ready: "bg-amber-500",
  offline: "bg-red-500",
};

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    fetch(`${API_BASE_URL}/ready`)
      .then((response) => setStatus(response.ok ? "ready" : "not_ready"))
      .catch(() => setStatus("offline"));
  }, []);

  return (
    <p className="flex items-center gap-2 text-sm">
      <span className={`h-2.5 w-2.5 rounded-full ${COLORS[status]}`} />
      {MESSAGES[status]}
    </p>
  );
}