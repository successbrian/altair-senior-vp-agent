import { execFile } from 'node:child_process'

import { Box, Text } from '@hermes/ink'
import { useStore } from '@nanostores/react'
import { memo, useEffect, useState } from 'react'

import { $uiState } from '../app/uiStore.js'

// Persistent tasks panel (Phase 6). Reads the successbrian_os.tasks table via
// tasks.py and renders the open work across the whole ecosystem — not just this
// session's LLM todo list. Collapsible; collapsed by default so it only costs
// one line until Brian expands it.

type OpenTask = { id: number; agent: string; title: string; priority: string; status: string; progress: number }
type DoneTask = { id: number; agent: string; title: string; summary: string; completed_at: string }
type Tasks = { open: OpenTask[]; completed: DoneTask[] }

const TASKS_PY = '/usr/bin/python3'
const TASKS_SCRIPT = '/home/agents/workspace/scripts/tasks.py'
const POLL_MS = 30000
const MAX_ROWS = 8

const STATUS_GLYPH: Record<string, string> = {
  active: '▶',
  in_progress: '◐',
  blocked: '⊘',
  at_risk: '⚠',
  backlog: '○',
  pending: '○'
}

function loadTasks(): Promise<Tasks | null> {
  return new Promise(resolve => {
    execFile(
      TASKS_PY,
      [TASKS_SCRIPT, 'list', '--limit', String(MAX_ROWS), '--json'],
      { timeout: 10000 },
      (err, stdout) => {
        if (err) {
          resolve(null)

          return
        }

        try {
          resolve(JSON.parse(stdout) as Tasks)
        } catch {
          resolve(null)
        }
      }
    )
  })
}

export const DbTasksPanel = memo(function DbTasksPanel() {
  const ui = useStore($uiState)
  const [tasks, setTasks] = useState<Tasks | null>(null)
  const [collapsed, setCollapsed] = useState(true)

  useEffect(() => {
    let alive = true

    const tick = () => {
      loadTasks().then(t => {
        if (alive) {
          setTasks(t)
        }
      })
    }

    tick()
    const id = setInterval(tick, POLL_MS)

    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  if (!tasks) {
    return (
      <Box flexShrink={0} paddingLeft={1}>
        <Text color={ui.theme.color.muted}>📋 tasks: loading…</Text>
      </Box>
    )
  }

  if (tasks.open.length === 0) {
    return null
  }

  const c = ui.theme.color
  const open = tasks.open
  const doneCount = tasks.completed.length

  return (
    <Box flexDirection="column" flexShrink={0} paddingLeft={1} paddingRight={1}>
      <Box onClick={() => setCollapsed(v => !v)}>
        <Text wrap="truncate-end">
          <Text color={c.accent}>{collapsed ? '▸' : '▾'} </Text>
          <Text bold color={c.text}>
            Tasks
          </Text>
          <Text color={c.muted}> · </Text>
          <Text color={c.statusFg}>{open.length} open</Text>
          {doneCount > 0 ? (
            <>
              <Text color={c.muted}> · </Text>
              <Text color={c.statusFg}>{doneCount} done</Text>
            </>
          ) : null}
        </Text>
      </Box>

      {!collapsed && (
        <Box flexDirection="column" marginLeft={2}>
          {open.slice(0, MAX_ROWS).map(t => {
            const glyph = STATUS_GLYPH[t.status] ?? '·'
            const prio = t.priority === 'critical' || t.priority === 'high' ? c.warn : c.muted

            return (
              <Text color={c.text} key={t.id} wrap="truncate-end">
                <Text color={prio}>{glyph} </Text>
                {t.title}
                <Text color={c.muted} dim>
                  {' '}
                  · {t.agent}
                </Text>
              </Text>
            )
          })}
        </Box>
      )}
    </Box>
  )
})
