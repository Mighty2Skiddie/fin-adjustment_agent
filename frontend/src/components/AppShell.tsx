import type { ReactNode } from 'react'

export function AppShell({ children }: { children?: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <main className="mx-auto max-w-[1280px] p-6">
        <h1 className="text-2xl font-semibold">fin-adjustments-agent</h1>
        {children}
      </main>
    </div>
  )
}
