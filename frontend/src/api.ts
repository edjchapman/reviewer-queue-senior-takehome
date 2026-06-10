export type ReviewStatus =
  | "unassigned"
  | "in_review"
  | "approved"
  | "rejected"
  | "escalated";

export type ReviewAction = "claim" | "approve" | "reject" | "escalate";

export interface ReviewItem {
  id: string;
  title: string;
  submitted_at: string;
  risk_level: "low" | "medium" | "high";
  customer_tier: "standard" | "priority";
  status: ReviewStatus;
  assigned_reviewer: string | null;
  notes_count: number;
  summary: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchReviewItems(): Promise<ReviewItem[]> {
  const response = await fetch(`${API_BASE_URL}/review-items`);
  if (!response.ok) {
    throw new Error(await extractErrorDetail(response, "Could not load review items"));
  }
  const payload = await response.json();
  return payload.items;
}

export async function applyReviewAction(
  itemId: string,
  action: ReviewAction,
  reviewer: string
): Promise<ReviewItem> {
  const response = await fetch(`${API_BASE_URL}/review-items/${itemId}/actions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ action, reviewer })
  });

  if (!response.ok) {
    throw new Error(await extractErrorDetail(response, "Action failed"));
  }

  const payload = await response.json();
  return payload.item;
}

async function extractErrorDetail(response: Response, fallback: string): Promise<string> {
  const body = await response.json().catch(() => null);
  return body?.detail ?? fallback;
}
