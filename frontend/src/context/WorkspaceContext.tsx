import React, { createContext, useContext, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listWorkspaces } from '../api/endpoints'
import type { Workspace } from '../types'

interface WorkspaceContextValue {
  workspaces: Workspace[]
  selectedWorkspace: Workspace | null
  setSelectedWorkspaceId: (id: string) => void
  isLoading: boolean
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)

const STORAGE_KEY = 'aegis_workspace_id'

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { data: workspaces = [], isLoading } = useQuery({
    queryKey: ['workspaces'],
    queryFn: listWorkspaces,
  })

  const [selectedId, setSelectedId] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) ?? '',
  )

  // When workspaces load, validate that the stored ID still exists
  useEffect(() => {
    if (!isLoading && selectedId) {
      const valid = workspaces.some((w: Workspace) => w.id === selectedId)
      if (!valid) {
        setSelectedId('')
        localStorage.removeItem(STORAGE_KEY)
      }
    }
  }, [workspaces, isLoading, selectedId])

  const setSelectedWorkspaceId = (id: string) => {
    setSelectedId(id)
    if (id) {
      localStorage.setItem(STORAGE_KEY, id)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  const selectedWorkspace = workspaces.find((w: Workspace) => w.id === selectedId) ?? null

  return (
    <WorkspaceContext.Provider
      value={{ workspaces, selectedWorkspace, setSelectedWorkspaceId, isLoading }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error('useWorkspace must be used within WorkspaceProvider')
  return ctx
}
