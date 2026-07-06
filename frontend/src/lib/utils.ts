import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function splitName(name: string): { label: string; modulePath: string } {
  const parts = name.split(".");
  if (parts.length <= 1) return { label: name, modulePath: "" };
  return { label: parts[parts.length - 1], modulePath: parts.slice(0, -1).join(".") };
}
