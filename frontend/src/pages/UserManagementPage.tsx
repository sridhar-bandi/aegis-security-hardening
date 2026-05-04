import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listUsers, updateUserRole, deactivateUser } from '../api/endpoints'
import { useAuth } from '../context/AuthContext'
import type { User } from '../types'

const ROLES = ['admin', 'security_officer', 'auditor', 'user'] as const

export default function UserManagementPage() {
  const { user: me } = useAuth()
  const qc = useQueryClient()

  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: listUsers })

  const roleMut = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) => updateUserRole(userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const deactivateMut = useMutation({
    mutationFn: (userId: string) => deactivateUser(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  if (me?.role !== 'admin') {
    return <p className="text-aegis-red">Access restricted to administrators.</p>
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-aegis-dark mb-4">User Management</h2>
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-aegis-dark text-white">
            <tr>
              {['Username', 'Email', 'Role', 'Status', 'Actions'].map((h) => (
                <th key={h} className="px-4 py-3 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{u.username}</td>
                <td className="px-4 py-3 text-gray-500">{u.email}</td>
                <td className="px-4 py-3">
                  <select
                    value={u.role}
                    onChange={(e) => roleMut.mutate({ userId: u.id, role: e.target.value })}
                    disabled={u.id === me.id}
                    className="border rounded px-1 py-0.5 text-xs"
                  >
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-semibold ${u.is_active ? 'text-aegis-green' : 'text-aegis-red'}`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {u.id !== me.id && u.is_active && (
                    <button
                      onClick={() => deactivateMut.mutate(u.id)}
                      className="text-xs text-aegis-red hover:underline"
                    >
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
