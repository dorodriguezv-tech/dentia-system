import { apiRequest } from '../../api/client'
import type { UserWithRoleOut } from '../auth/types'
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
