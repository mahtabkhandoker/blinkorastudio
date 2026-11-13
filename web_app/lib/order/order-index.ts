import type { ConversationSummary } from "@/lib/chat/types";
import type { OrderStatus, OrderView } from "@/lib/api/orders";

/**
 * A list of pointers to this browser's recent orders, for the sidebar and
 * the dashboard. It stores only the id, number, title and last known
 * status. The order itself lives on the backend and is always loaded from
 * there; nothing here is treated as the order's state.
 */

const KEY = "blinkora.orders.index";
const MAX_ENTRIES = 30;

export type OrderPointer = {
  id: string;
  number: string;
  title: string;
  status: OrderStatus;
  updatedAt: number;
};

function read(): OrderPointer[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as OrderPointer[]) : [];
  } catch {
    return [];
  }
}

export function listOrderPointers(): OrderPointer[] {
  return read().sort((a, b) => b.updatedAt - a.updatedAt);
}

export function rememberOrder(order: OrderView): void {
  if (typeof window === "undefined") return;
  try {
    const rest = read().filter((p) => p.id !== order.id);
    rest.push({ id: order.id, number: order.number, title: order.title, status: order.status, updatedAt: Date.now() });
    const trimmed = rest.sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_ENTRIES);
    window.localStorage.setItem(KEY, JSON.stringify(trimmed));
  } catch {
    // The index is a convenience; losing it never affects an order.
  }
}

export function forgetOrder(orderId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(read().filter((p) => p.id !== orderId)));
  } catch {
    // ignore
  }
}

export function summaryStatus(status: OrderStatus): ConversationSummary["status"] {
  if (status === "FAILED") return "failed";
  if (status === "GENERATING") return "generating";
  if (status === "GENERATED" || status === "CONFIRMED") return "completed";
  return "active";
}

export function toSummaries(pointers: OrderPointer[]): ConversationSummary[] {
  return pointers.map((p) => ({
    id: p.id,
    title: p.title === p.number ? p.number : `${p.title} · ${p.number}`,
    status: summaryStatus(p.status),
    updatedAt: p.updatedAt,
  }));
}
