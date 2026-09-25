import { execFile } from 'node:child_process'

import { Box, Text } from '@hermes/ink'
import { useStore } from '@nanostores/react'
import { memo, useEffect, useState } from 'react'

import { $uiState } from '../app/uiStore.js'

// Health strip (top of the 4-panel TUI). Polls the successbrian-os health
// worker (health.py report --json) and renders a compact one-line readout:
// agents up/down, task counts, stuck count, model service states, revenue,
// and alert count. Data comes straight from PostgreSQL via the worker, so it
// reflects the whole ecosystem, not just this session.

type HealthAgent = { agent: string; status: string }
type Health = {
  tasks_by_status?: Record<string, number>
  stuck?: number
  agents?: HealthAgent[]
  revenue?: { net_profit: number | null; working_capital: number | null }
  models?: Record<string, string>
  alerts?: { severity: string; message: string }[]
}

const HEALTH_PY = '/usr/bin/python3'
const HEALTH_SCRIPT = '/home/agents/workspace/scripts/health.py'
const POLL_MS = 30000

function loadHealth(): Promise<Health | null> {
  return new Promise(resolve => {
    execFile(HEALTH_PY, [HEALTH_SCRIPT, 'report', '--json'], { timeout: 10000 }, (err, stdout) => {
      if (err) {
        resolve(null)

        return
      }

      try {
        resolve(JSON.parse(stdout) as Health)
      } catch {
        resolve(null)
      }
    })
  })
}

export const HealthStrip = memo(function HealthStrip() {
  const ui = useStore($uiState)
  const [health, setHealth] = useState<Health | null>(null)

  useEffect(() => {
    let alive = true

    const tick = () => {
      loadHealth().then(h => {
        if (alive) {setHealth(h)}
      })
    }

    tick()
    const id = setInterval(tick, POLL_MS)

    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  if (!health) {
    return (
      <Box flexShrink={0} paddingLeft={1}>
        <Text color={ui.theme.color.muted}>⚡ health: loading…</Text>
      </Box>
    )
  }

  const c = ui.theme.color
  const agents = health.agents ?? []
  const active = agents.filter(a => a.status === 'active').length
  const down = agents.length - active
  const tasks = health.tasks_by_status ?? {}

  const open =
    (tasks.backlog ?? 0) +
    (tasks.in_progress ?? 0) +
    (tasks.active ?? 0) +
    (tasks.blocked ?? 0) +
    (tasks.at_risk ?? 0)

  const done = tasks.completed ?? 0
  const models = health.models ?? {}
  const modelsUp = Object.values(models).filter(s => s === 'active').length
  const modelsTotal = Object.values(models).length
  const alerts = health.alerts ?? []
  const net = health.revenue?.net_profit ?? null

  return (
    <Box flexShrink={0} paddingLeft={1} paddingRight={1}>
      <Text wrap="truncate-end">
        <Text bold color={c.accent}>⚡ </Text>
        <Text color={down > 0 ? c.error : c.statusFg}>
          {active}/{agents.length} agents
        </Text>
        <Text color={c.muted}> · </Text>
        <Text color={c.statusFg}>{open} open</Text>
        <Text color={c.muted}> · </Text>
        <Text color={c.statusFg}>{done} done</Text>
        {health.stuck ? (
          <>
            <Text color={c.muted}> · </Text>
            <Text color={c.warn}>{health.stuck} stuck</Text>
          </>
        ) : null}
        <Text color={c.muted}> · </Text>
        <Text color={modelsUp === modelsTotal ? c.statusFg : c.warn}>
          models {modelsUp}/{modelsTotal}
        </Text>
        {net != null ? (
          <>
            <Text color={c.muted}> · </Text>
            <Text color={c.statusFg}>${net} net</Text>
          </>
        ) : null}
        {alerts.length > 0 ? (
          <>
            <Text color={c.muted}> · </Text>
            <Text color={c.error}>{alerts.length} alerts</Text>
          </>
        ) : null}
      </Text>
    </Box>
  )
})
