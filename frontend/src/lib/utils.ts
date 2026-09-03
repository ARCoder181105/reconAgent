import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format a paise integer as an INR string (e.g. 2918800 -> "₹29,188.00"). */
export function formatINR(paise: number | null | undefined): string {
  if (paise == null) return "—"
  const rupees = Math.abs(paise) / 100
  const sign = paise < 0 ? "-" : ""
  return `${sign}₹${rupees.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

/** Format a plain decimal amount (bank statement uses rupees float). */
export function formatINRDecimal(rupees: number | null | undefined): string {
  if (rupees == null || Number.isNaN(rupees)) return "—"
  const sign = rupees < 0 ? "-" : ""
  return `${sign}₹${Math.abs(rupees).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

/** Short date string YYYY-MM-DD as-is (already ISO from the API). */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—"
  return iso
}