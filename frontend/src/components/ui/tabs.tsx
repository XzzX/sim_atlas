import { Tabs } from "@base-ui/react/tabs"

import { cn } from "@/lib/utils"

function TabsRoot({ className, ...props }: Tabs.Root.Props) {
  return <Tabs.Root className={cn("w-full", className)} {...props} />
}

function TabsList({ className, ...props }: Tabs.List.Props) {
  return (
    <Tabs.List
      className={cn(
        "inline-flex h-9 items-center gap-1 rounded-lg bg-muted p-1 text-muted-foreground",
        className
      )}
      {...props}
    />
  )
}

function TabsTrigger({ className, ...props }: Tabs.Tab.Props) {
  return (
    <Tabs.Tab
      className={cn(
        "inline-flex items-center justify-center rounded-md px-3 py-1 text-sm font-medium transition-colors data-[selected]:bg-background data-[selected]:text-foreground data-[selected]:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
        className
      )}
      {...props}
    />
  )
}

function TabsContent({ className, ...props }: Tabs.Panel.Props) {
  return <Tabs.Panel className={cn("mt-4", className)} {...props} />
}

export { TabsContent, TabsList, TabsRoot, TabsTrigger }
