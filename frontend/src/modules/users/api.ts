import { apiRequest, apiRequestFormData } from '../../api/client'
import type { UserOut, UserWithRoleOut } from '../auth/types'
import type { CreateUserInput, UpdateUserInput } from './types'

export function listUsers(): Promise<UserWithRoleOut[]> {
  return apiRequest<UserWithRoleOut[]>('/users')
}

export function createUser(input: CreateUserInput): Promise<UserWithRoleOut> {
  return apiRequest<UserWithRoleOut>('/users', { method: 'POST', body: input })
}

export function updateUser(userId: string, input: UpdateUserInput): Promise<UserWithRoleOut> {
  return apiRequest<UserWithRoleOut>(`/users/${userId}`, { method: 'PATCH', body: input })
}

export function deleteUser(userId: string): Promise<void> {
  return apiRequest<void>(`/users/${userId}`, { method: 'DELETE' })
}

export function uploadUserPhoto(userId: string, file: File): Promise<UserOut> {
  const form = new FormData()
  form.append('file', file)
  return apiRequestFormData<UserOut>(`/users/${userId}/photo`, form)
}
