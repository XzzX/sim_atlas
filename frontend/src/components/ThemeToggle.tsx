import { useTheme } from "next-themes";
import { SunIcon, MoonIcon } from "lucide-react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <div className="flex shrink-0 gap-0.5 rounded-[9px] bg-muted p-0.5">
      <button
        type="button"
        onClick={() => setTheme("light")}
        className={`flex items-center gap-[5px] rounded-md px-[11px] py-[5px] text-xs font-medium transition-colors duration-[120ms] ${
          !isDark ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
        }`}
      >
        <SunIcon className="size-[13px]" />
        Light
      </button>
      <button
        type="button"
        onClick={() => setTheme("dark")}
        className={`flex items-center gap-[5px] rounded-md px-[11px] py-[5px] text-xs font-medium transition-colors duration-[120ms] ${
          isDark ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"
        }`}
      >
        <MoonIcon className="size-[13px]" />
        Dark
      </button>
    </div>
  );
}
